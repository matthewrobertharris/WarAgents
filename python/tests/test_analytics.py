"""Analytics: what the engine counts during a game, and the filtered views over a player's games."""

import pytest
from conftest import sign_up
from helpers import make

from waragents.analytics import backfill
from waragents.battles import run_to_end

DEFEND = ["t (OUTPUT DEFEND)"]

# ---- what the engine counts ---------------------------------------------------------------------


def test_a_kill_and_the_damage_are_counted():
    world = make(width=2, height=1, players=[("red", 0, 0, ["t (OUTPUT ATTACK_RIGHT)"], {"power": 200}),
                                             ("blue", 1, 0, DEFEND)])
    world.step()
    red, blue = (p.stats for p in world.players)
    assert (red.kills, red.damage_dealt, blue.deaths, blue.damage_taken) == (1, 100, 1, 100)
    assert red.succeeded["ATTACK_RIGHT"] == 1
    assert (red.agents, blue.agents) == ([1, 1], [1, 0])  # turn 0, then after turn 1


def test_a_blocked_attack_is_counted():
    world = make(width=2, height=1, players=[("red", 0, 0, ["t (OUTPUT ATTACK_RIGHT)"]),
                                             ("blue", 1, 0, DEFEND)], )
    world.players[1].agents[0].action = None
    world.step()
    world.step()
    assert world.players[1].stats.blocks >= 1


def test_food_failed_actions_and_node_visits_are_counted():
    tree = "t (BOOLEAN HAS_FOOD CURRENT (OUTPUT EAT) (OUTPUT MOVE_LEFT))"
    world = make(width=3, height=1, food=[[0, 0, 30]], players=[("red", 2, 0, [tree], {"health": 100})])
    agent = world.agents[0]
    agent.health = 80
    world.step()  # eats 20 of the 30
    world.step()  # full health now, so EAT fails
    stats = world.players[0].stats
    assert stats.food_eaten == 20
    assert (stats.succeeded["EAT"], stats.failed["EAT"]) == (1, 1)
    assert stats.visits["t"] == {0: 2, 1: 2}  # the root, then the true branch, twice
    assert stats.health == [80, 100, 100]


def test_confusion_is_counted_at_the_node_that_caused_it():
    tree = "t (BOOLEAN OCCUPIED XY_VALUE 9 9 (OUTPUT DEFEND) (OUTPUT DEFEND))"
    world = make(players=[("red", 0, 0, [tree])])
    world.step()
    stats = world.players[0].stats
    assert stats.confused == 1 and stats.confused_at["t"] == {0: 1}


def test_counting_doesnt_change_the_game_and_replays_count_the_same(catalogue):
    record = catalogue.new_game("skirmish", [{"slot": 1, "tree": "raid"}, {"slot": 2, "tree": "graze"}], seed=11)[1]
    first, second = run_to_end(record), run_to_end(record)
    assert first.result == second.result
    assert [p.stats for p in first.players] == [p.stats for p in second.players]
    assert len(first.players[0].stats.agents) == first.time + 1


# ---- the views ----------------------------------------------------------------------------------


@pytest.fixture
def played(app, catalogue):
    """Alice has played five skirmishes with her tree "mine": three with one version of it and two
    after editing it. Bob has played one of his own."""
    sign_up(app, "Admin")
    alice, bob = sign_up(app, "Alice"), sign_up(app, "Bob")
    for player in ("alice", "bob"):
        catalogue.add_xp(player, 40000)  # a budget big enough for any default tree
    raid = catalogue.find_tree(None, "raid")
    graze = catalogue.find_tree(None, "graze")
    tree_id = alice.post("/api/catalogue/trees", json={"name": "mine", "root": raid["root"]}).json["id"]
    bots = [{"bot": "guard"}, {"bot": "graze"}, {"bot": "guard"}, {"bot": "raid"}, {"bot": "guard"}]
    for n, bot in enumerate(bots):
        if n == 3:
            alice.put(f"/api/catalogue/trees/{tree_id}", json={"name": "mine", "root": graze["root"]})
        response = alice.post("/api/skirmish", json={"map": "skirmish", "tree": "mine", "opponents": [bot], "seed": n})
        assert response.status_code == 201, response.json
    bob.post("/api/skirmish", json={"map": "skirmish", "tree": "raid", "opponents": [{"bot": "guard"}], "seed": 9})
    return {"alice": alice, "bob": bob, "tree": tree_id}


def test_the_summary_covers_your_games_only(played):
    summary = played["alice"].get("/api/analytics").json
    k = summary["kpis"]
    assert (k["games"], k["counted"]) == (5, 5)
    assert k["wins"] == sum(r["wins"] for r in summary["byTree"])
    assert [(r["key"], r["games"]) for r in summary["byTree"]] == [(played["tree"], 5)]
    assert {r["key"] for r in summary["byOpponent"]} == {"bot:Bot (guard)", "bot:Bot (graze)", "bot:Bot (raid)"}
    assert summary["byMode"][0]["key"] == "skirmish" and summary["byMap"][0]["key"] == "skirmish"
    assert sum(a["succeeded"] + a["failed"] for a in summary["you"]["actions"]) == k["decisions"] > 0
    assert summary["timeline"]["turns"][0] == 0 and len(summary["games"]) == 5
    assert summary["timeline"]["you"]["agents"][0] == summary["timeline"]["opponents"]["agents"][0]  # same start
    assert summary["byVersion"] is None  # only with one tree picked

    assert played["bob"].get("/api/analytics").json["kpis"]["games"] == 1


def test_one_tree_shows_its_versions(played):
    summary = played["alice"].get(f"/api/analytics?tree={played['tree']}").json
    assert [(v["label"], v["games"]) for v in summary["byVersion"]] == [("v1", 3), ("v2", 2)]
    v2 = summary["byVersion"][1]["key"]
    only_v2 = played["alice"].get(f"/api/analytics?tree={played['tree']}&version={v2}").json
    assert only_v2["kpis"]["games"] == 2
    assert {g["versionLabel"] for g in only_v2["games"]} == {"v2"}


def test_filters_narrow_everything(played):
    alice = played["alice"]
    wins = alice.get("/api/analytics?outcome=win").json["kpis"]
    losses = alice.get("/api/analytics?outcome=loss").json["kpis"]
    assert wins["games"] + losses["games"] == 5 and wins["wins"] == wins["games"] and losses["wins"] == 0
    guard = alice.get("/api/analytics?opponent=bot:Bot%20(guard)").json
    assert guard["kpis"]["games"] == 3 and all("Bot (guard)" in g["opponents"] for g in guard["games"])
    assert alice.get("/api/analytics?mode=season").json["kpis"]["games"] == 0
    assert alice.get("/api/analytics?since=2000-01-01&until=2000-12-31").json["kpis"]["games"] == 0
    assert alice.get("/api/analytics?mode=skirmish,training&map=skirmish").json["kpis"]["games"] == 5


@pytest.mark.parametrize("query", ["mode=chess", "outcome=draw", "since=yesterday"])
def test_bad_filters_are_refused(played, query):
    response = played["alice"].get(f"/api/analytics?{query}")
    assert response.status_code == 422 and response.json["detail"]


def test_options_list_what_you_can_filter_on(played):
    options = played["alice"].get("/api/analytics/options").json
    assert [t["key"] for t in options["trees"]] == [played["tree"]]
    assert [v["label"] for v in options["trees"][0]["versions"]] == ["v1", "v2"]
    assert [m["key"] for m in options["modes"]] == ["skirmish"]
    assert options["seasons"] == []


def test_a_trees_nodes_are_counted_per_version(played):
    alice = played["alice"]
    assert alice.get("/api/analytics/nodes").status_code == 422  # it needs a tree
    nodes = alice.get(f"/api/analytics/nodes?tree={played['tree']}").json
    assert (nodes["versionLabel"], nodes["games"], nodes["startTree"]) == ("v2", 2, "mine")
    decisions = alice.get(f"/api/analytics?tree={played['tree']}&version={nodes['version']}").json["kpis"]["decisions"]
    assert sum(v["0"]["visits"] for v in nodes["visits"].values()) == decisions  # every decision starts at a root
    assert {t["name"] for t in nodes["trees"]} >= {"mine"}
    assert played["bob"].get(f"/api/analytics/nodes?tree={played['tree']}").status_code == 404


def test_backfill_counts_games_again_the_same_way(played, catalogue):
    before = played["alice"].get("/api/analytics").json
    catalogue.db.execute("delete from team_stats")
    assert played["alice"].get("/api/analytics").json["kpis"]["counted"] == 0
    assert backfill(catalogue) == {"counted": 6, "mismatched": []}
    assert backfill(catalogue) == {"counted": 0, "mismatched": []}
    after = played["alice"].get("/api/analytics").json
    assert after["kpis"] == before["kpis"] and after["you"] == before["you"] and after["opponents"] == before["opponents"]


# ---- opponents ------------------------------------------------------------------------------------


def test_opponents_are_summarised_like_you(played):
    summary = played["alice"].get("/api/analytics").json
    you, them = summary["you"], summary["opponents"]
    assert (you["teams"], them["teams"]) == (5, 5)  # one practice team in each game
    assert them["decisions"] > 0 and them["actions"] and them["averages"]["peakAgents"] >= 1
    # Every kill is someone's death: with one opponent per game, the two sides mirror each other.
    assert you["averages"]["kills"] == them["averages"]["deaths"]
    assert you["averages"]["damageDealt"] == them["averages"]["damageTaken"]
    assert len(summary["timeline"]["opponents"]["agents"]) == len(summary["timeline"]["turns"])

    guard = played["alice"].get("/api/analytics?opponent=bot:Bot%20(guard)").json
    assert guard["opponents"]["teams"] == 3


def test_opponents_trees_stay_private(played):
    # The node view only ever counts your own teams, so another player's tree finds nothing.
    assert played["alice"].get("/api/analytics/nodes?tree=graze").status_code == 404


# ---- export ---------------------------------------------------------------------------------------


def unzip(response):
    import csv
    import io
    import json
    import zipfile

    assert response.status_code == 200 and response.mimetype == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.data))
    files = {name: list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8"))))
             for name in archive.namelist() if name.endswith(".csv")}
    return archive, files, json.loads(archive.read("trees.json"))


def test_export_has_every_turn_of_every_game(played, catalogue):
    response = played["alice"].get("/api/analytics/export")
    assert "attachment" in response.headers["Content-Disposition"]
    archive, files, trees = unzip(response)
    assert "README.txt" in archive.namelist()
    games = files["games.csv"]
    assert len(games) == 5 and all(g["your_slot"] for g in games)
    turns = {g["game_id"]: int(g["turns"]) for g in games}
    assert len(files["turns.csv"]) == sum((n + 1) * 2 for n in turns.values())  # two teams, turn 0 too

    # The per-turn counts agree with what Analytics stored.
    game_id = games[0]["game_id"]
    stored = catalogue.db.query("select slot, agents from team_stats where game_id = %s", (game_id,))
    for team in stored:
        exported = [int(r["agents"]) for r in files["turns.csv"] if r["game_id"] == game_id and r["slot"] == str(team["slot"])]
        assert exported == team["agents"]
    alive_at_1 = sum(1 for r in files["agents.csv"] if r["game_id"] == game_id and r["turn"] == "1" and not r["died"])
    assert alive_at_1 == sum(t["agents"][1] for t in stored)

    # The whole board at turn 0, then only changes.
    first = [r for r in files["tiles.csv"] if r["game_id"] == game_id and r["turn"] == "0"]
    assert len(first) == 16 * 10  # the Skirmish map has no holes
    assert any(r["kind"] == "end" for r in files["events.csv"] if r["game_id"] == game_id)
    assert set(trees) == {g["version"] for g in games}


def test_export_keeps_opponents_thinking_private(played):
    _, files, trees = unzip(played["alice"].get("/api/analytics/export"))
    yours = {(t["game_id"], t["slot"]) for t in files["teams.csv"] if t["yours"] == "True"}
    theirs = [t for t in files["teams.csv"] if t["yours"] == "False"]
    assert theirs and all(t["start_tree"] == "" for t in theirs)
    for row in files["agents.csv"]:
        mine = (row["game_id"], row["slot"]) in yours
        if not mine:
            assert row["tree"] == row["path"] == row["primary_x"] == row["secondary_x"] == ""
        elif row["action"]:
            assert row["tree"] and row["path"]
    assert any(r["action"] for r in files["agents.csv"] if (r["game_id"], r["slot"]) not in yours)  # but not what they did
    assert all(v["startTree"] == "mine" for v in trees.values())


def test_export_follows_the_filters_and_only_has_your_games(played):
    _, files, _ = unzip(played["alice"].get("/api/analytics/export?opponent=bot:Bot%20(guard)"))
    assert len(files["games.csv"]) == 3
    _, files, _ = unzip(played["bob"].get("/api/analytics/export"))
    assert len(files["games.csv"]) == 1
    assert played["alice"].get("/api/analytics/export?mode=chess").status_code == 422
