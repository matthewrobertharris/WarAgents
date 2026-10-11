"""Skirmish battles, their results and rewards, and History."""

import pytest
from conftest import sign_up

from waragents.catalogue import DEFAULT_STATS, CatalogueError
from waragents.progression import MODE_XP_FACTOR

@pytest.fixture
def people(app):
    """Admin, Alice (the attacker) and Bob (who has a default tree, so he can be picked)."""
    admin = sign_up(app, "Admin")
    alice, bob, carol = sign_up(app, "Alice"), sign_up(app, "Bob"), sign_up(app, "Carol")
    wander = admin.get("/api/catalogue/trees/wander").json
    alice.post("/api/catalogue/trees", json={"name": "mine", "root": wander["root"]})
    assert bob.put("/api/me", json={"startTree": "wander"}).status_code == 200
    return {"admin": admin, "alice": alice, "bob": bob, "carol": carol}


def skirmish(client, **changes):
    body = {"map": "skirmish", "tree": "mine", "opponents": [{"player": "bob"}], "seed": 5, **changes}
    return client.post("/api/skirmish", json=body)


def catalogue(app):
    return app.extensions["waragents"]["catalogue"]


def test_a_skirmish_is_played_through_and_rewards_everyone(app, people):
    response = skirmish(people["alice"])
    assert response.status_code == 201, response.json
    game_id, result = response.json["gameId"], response.json["result"]

    record = catalogue(app).get("games", game_id)
    assert (record["mode"], record["createdBy"], record["participants"]) == ("skirmish", "alice", ["alice", "bob"])
    assert all({k: t[k] for k in DEFAULT_STATS} == DEFAULT_STATS for t in record["teams"])
    assert [t["startTree"] for t in record["teams"]] == ["mine", "wander"]

    assert result["mode"] == "skirmish" and result["turns"] >= 1
    assert {p["player"] for p in result["placements"]} == {"alice", "bob"}
    for player_id in ("alice", "bob"):
        reward = result["rewards"][player_id]
        team = next(p for p in result["placements"] if p["player"] == player_id)
        assert reward["agentXp"] == team["exp"]
        assert reward["fromAgents"] == round(team["exp"] * MODE_XP_FACTOR["skirmish"])
        assert reward["total"] == reward["fromAgents"] and reward["bonus"] == 0
        assert catalogue(app).get("players", player_id).get("xp", 0) == reward["total"]
    assert people["alice"].get("/api/me").json["xp"] == result["rewards"]["alice"]["total"]


def test_the_replay_ends_the_way_the_result_says(people):
    alice = people["alice"]
    battle = skirmish(alice).json
    game_id, result = battle["gameId"], battle["result"]
    replay = alice.post(f"/api/games/{game_id}/seek", json={"turn": result["turns"]}).json
    assert replay["state"]["finished"]
    assert replay["state"]["result"]["placements"] == [
        {k: v for k, v in p.items() if k not in ("player", "colour")} for p in result["placements"]]
    again = skirmish(alice).json["result"]
    assert again["placements"] == result["placements"]  # same seed, same battle


def test_opponents_trees_are_hidden_in_the_replay(people):
    game_id = skirmish(people["alice"]).json["gameId"]
    for viewer, own, other in ((people["alice"], "Alice", "Bob"), (people["bob"], "Bob", "Alice")):
        state = viewer.post(f"/api/games/{game_id}/step", json={"turns": 3}).json["state"]
        players = {p["name"]: p for p in state["players"]}
        assert players[own]["trees"] and not players[own]["hidden"]
        assert "trees" not in players[other] and players[other]["hidden"]
        for agent in state["agents"]:
            if agent["player"] == other:
                assert agent["path"] == [] and agent["tree"] is None
    admin_view = people["admin"].get(f"/api/games/{game_id}").json["state"]
    assert all("trees" in p for p in admin_view["players"])


def test_history_and_results(people):
    alice, bob, carol = people["alice"], people["bob"], people["carol"]
    game_id = skirmish(alice).json["gameId"]

    entry = alice.get("/api/history").json[0]
    assert (entry["id"], entry["mode"], entry["finished"], entry["seen"]) == (game_id, "skirmish", True, False)
    assert entry["place"] in (1, 2) and entry["teamCount"] == 2
    assert bob.get("/api/history").json[0]["id"] == game_id  # the defender sees it too
    assert carol.get("/api/history").json == []

    result = alice.get(f"/api/results/{game_id}").json
    assert [t["name"] for t in result["teams"]] == ["Alice", "Bob"]
    assert alice.post(f"/api/results/{game_id}/seen").status_code == 200
    assert alice.get("/api/history").json[0]["seen"] is True
    assert bob.get("/api/history").json[0]["seen"] is False

    assert carol.get(f"/api/results/{game_id}").status_code == 403
    assert carol.get(f"/api/games/{game_id}").status_code == 403
    assert alice.get("/api/catalogue/results").status_code == 403


def test_practice_bots_and_who_can_be_picked(people):
    alice = people["alice"]
    opponents = {p["id"]: p for p in alice.get("/api/opponents").json}
    assert "alice" not in opponents
    assert opponents["bob"] == {"id": "bob", "name": "Bob", "colour": None, "level": 1, "ready": True, "treeCost": 10}
    assert opponents["carol"]["ready"] is False
    assert {"defend", "wander", "raid"} <= {b["name"] for b in alice.get("/api/bots").json}

    response = skirmish(alice, opponents=[{"bot": "raid"}])
    assert response.status_code == 201
    result = response.json["result"]
    assert set(result["rewards"]) == {"alice"}
    assert [p["name"] for p in sorted(result["placements"], key=lambda p: p["slot"])] == ["Alice", "Bot (raid)"]


@pytest.mark.parametrize("changes, message", [
    ({"tree": "raid"}, "Your tree 'raid' isn't ready: It costs 97 points and the budget is 20"),
    ({"opponents": [{"player": "carol"}]}, "Carol can't be picked yet: their default tree isn't ready"),
    ({"opponents": [{"player": "alice"}]}, "You can't pick yourself"),
    ({"opponents": [{"player": "bob"}, {"bot": "wander"}]}, "at most 1 opponents"),
    ({"opponents": [{"bot": "nope"}]}, "There's no practice opponent called 'nope'"),
    ({"opponents": []}, "Choose at least one opponent"),
    ({"slot": 7}, "This map has no slot 7"),
])
def test_skirmish_mistakes(people, changes, message):
    response = skirmish(people["alice"], **changes)
    assert response.status_code == 400
    assert any(message in p for p in response.json["problems"]), response.json


def test_skirmish_needs_a_map_you_can_use(people):
    bob = people["bob"]
    made = bob.post("/api/catalogue/maps", json={
        "name": "Private", "mode": "FIXED", "maxAgents": 5, "dirt": [[0, 0]], "food": [[0, 0]], "plants": [],
        "starts": [{"slot": 1, "x": 0, "y": 0}, {"slot": 2, "x": 1, "y": 0}], "criteria": []}).json
    assert skirmish(people["alice"], map=made["id"]).status_code == 403
    assert skirmish(people["alice"], map="nowhere").status_code == 404


def test_a_game_has_one_result_and_deleting_it_deletes_the_result(app, people):
    game_id = skirmish(people["alice"]).json["gameId"]
    cat = catalogue(app)
    with pytest.raises(CatalogueError):
        cat.save_result(game_id, cat.result(game_id))
    cat.delete("games", game_id)
    assert cat.result(game_id) is None
