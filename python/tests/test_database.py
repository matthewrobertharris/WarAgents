"""The PostgreSQL side of the catalogue: migrations, seeding, importing a JSON catalogue, and
changes that have to stay right when many requests (or servers) make them at once."""

import json
import threading

import pytest

from waragents.battles import run_to_end
from waragents.catalogue import CatalogueError
from waragents.content import CONTENT_DIR, dumps, import_folder, seed
from waragents.db.migrate import migrate, pending
from waragents.training import tree_name


def output(action):
    return {"kind": "OUTPUT", "action": action}


def in_threads(count, work):
    """Run work(n) in count threads at once and return what each one raised (or None)."""
    errors = [None] * count
    start = threading.Barrier(count)

    def run(n):
        start.wait()
        try:
            work(n)
        except Exception as e:  # noqa: BLE001 - reported to the test
            errors[n] = e

    threads = [threading.Thread(target=run, args=(n,)) for n in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def test_migrating_again_changes_nothing(database):
    assert migrate(database) == []
    assert pending(database) == []


def test_seeding_twice_updates_rather_than_duplicates(empty_catalogue):
    first = seed(empty_catalogue)
    assert first["tutorials"] >= 17 and first["maps"] == 3
    assert seed(empty_catalogue) == first
    assert empty_catalogue.count("trees") == first["trees"]
    assert all(t["owner"] is None for t in empty_catalogue.list("trees"))


def test_a_bad_content_file_loads_nothing(empty_catalogue, tmp_path):
    (tmp_path / "trees").mkdir()
    (tmp_path / "trees" / "good.json").write_text(json.dumps({"name": "good", "root": output("EAT")}))
    (tmp_path / "trees" / "worse.json").write_text(json.dumps({"name": "worse", "root": output("FLY")}))
    with pytest.raises(CatalogueError, match="trees/worse.json"):
        seed(empty_catalogue, tmp_path)
    assert empty_catalogue.count("trees") == 0


def test_the_session_key_is_made_once(empty_catalogue):
    key = empty_catalogue.secret("session-key")
    assert len(key) == 64 and empty_catalogue.secret("session-key") == key


def test_xp_from_simultaneous_games_all_counts(empty_catalogue):
    empty_catalogue.create("players", {"name": "Sam"})
    assert in_threads(8, lambda n: [empty_catalogue.add_xp("sam", 5) for _ in range(10)]) == [None] * 8
    assert empty_catalogue.get("players", "sam")["xp"] == 400


def test_only_one_run_completes_a_tutorial_first(empty_catalogue):
    seed(empty_catalogue, only={"tutorials": ["movement-1"]})
    empty_catalogue.create("players", {"name": "Sam"})
    firsts = []
    errors = in_threads(6, lambda n: firsts.append(empty_catalogue.complete_tutorial("sam", "movement-1", 10 + n)))
    assert errors == [None] * 6
    assert sorted(firsts) == [False] * 5 + [True]
    assert empty_catalogue.get("players", "sam")["training"]["movement-1"]["turns"] == 10


def test_one_of_two_trees_saved_at_once_with_the_same_name_is_refused(empty_catalogue):
    empty_catalogue.create("players", {"name": "Sam"})
    errors = in_threads(2, lambda n: empty_catalogue.create(
        "trees", {"name": "twin", "owner": "sam", "root": output("EAT")}))
    assert sorted(type(e).__name__ for e in errors if e) == ["CatalogueError"]
    assert [t["name"] for t in empty_catalogue.list("trees")] == ["twin"]


def test_only_one_season_can_be_open(empty_catalogue):
    season = {"name": "S", "status": "open", "ratings": {}, "standings": None}
    errors = in_threads(3, lambda n: empty_catalogue.create("seasons", {**season, "name": f"S{n}"}))
    assert len([e for e in errors if e]) == 2
    assert all("already running" in str(e) for e in errors if e)


def test_games_remember_the_tree_each_team_started_with(catalogue):
    catalogue.create("players", {"name": "Sam"})
    mine = catalogue.create("trees", {"name": "mine", "owner": "sam", "root": output("DEFEND")})
    game_id, _ = catalogue.new_game("skirmish", [{"slot": 1, "player": "sam", "tree": mine},
                                                {"slot": 2, "tree": "graze"}], seed=1)
    teams = catalogue.db.query("select slot, tree_id from game_teams where game_id = %s order by slot", (game_id,))
    assert [(t["slot"], t["tree_id"]) for t in teams] == [(1, "mine"), (2, "graze")]

    # Deleting the tree doesn't touch the game, which keeps its own copy to replay.
    catalogue.delete("trees", mine)
    assert catalogue.db.value("select tree_id from game_teams where game_id = %s and slot = 1", (game_id,)) is None
    assert run_to_end(catalogue.get("games", game_id)).finished


def test_deleting_a_game_deletes_its_result(catalogue):
    game_id, record = catalogue.new_game("skirmish", [{"slot": 1, "tree": "raid"}, {"slot": 2, "tree": "graze"}],
                                         seed=3)
    catalogue.save_result(game_id, {**run_to_end(record).result, "seenBy": []})
    with pytest.raises(CatalogueError, match="already has a result"):
        catalogue.save_result(game_id, {**run_to_end(record).result})
    catalogue.delete("games", game_id)
    assert catalogue.count("results") == 0


def test_a_json_catalogue_imports_exactly(empty_catalogue, tmp_path):
    seed(empty_catalogue, only={"tutorials": ["movement-1"], "maps": ["skirmish"], "trees": ["defend"]})
    alice = {"name": "Alice", "colour": "#2f9e44", "startTree": "mine", "created": "2026-10-03T09:30:00",
             "xp": 120, "training": {"movement-1": {"completed": "2026-10-04T10:00:00", "turns": 7}},
             "passwordHash": "scrypt:fake", "admin": True}
    tree = {"name": "mine", "owner": "alice", "root": output("ATTACK_RIGHT")}
    game_id, game = empty_catalogue.new_game("skirmish", [{"slot": 1, "tree": "defend", "name": "A"},
                                                         {"slot": 2, "tree": "defend", "name": "B"}], seed=9)
    result = {**run_to_end(game).result, "seenBy": []}
    old = {"players": {"alice": alice}, "trees": {tree_name("x"): tree},
           "games": {"20261001-120000-abcd": {**game, "participants": []}},
           "results": {"20261001-120000-abcd": result}}
    for kind, items in old.items():
        (tmp_path / kind).mkdir()
        for item_id, item in items.items():
            (tmp_path / kind / f"{item_id}.json").write_text(dumps(item), encoding="utf-8")

    report = import_folder(empty_catalogue, tmp_path)
    assert {k: (v["added"], v["failed"]) for k, v in report.items() if v["added"] or v["failed"]} == {
        "players": (1, []), "trees": (1, []), "games": (1, []), "results": (1, [])}
    assert empty_catalogue.get("players", "alice") == alice
    assert empty_catalogue.get("trees", "tut-x") == tree
    assert empty_catalogue.get("games", "20261001-120000-abcd") == {**game, "participants": []}
    stored = empty_catalogue.result("20261001-120000-abcd")
    assert (stored["placements"], stored["winners"], stored["turns"]) == (
        [{**p, "player": None, "colour": None} for p in result["placements"]], result["winners"], result["turns"])
    assert import_folder(empty_catalogue, tmp_path)["players"] == {"added": 0, "skipped": 1, "failed": []}


def test_the_bundled_content_is_all_valid(empty_catalogue):
    counts = seed(empty_catalogue)
    assert counts == {kind: len(list((CONTENT_DIR / kind).glob("*.json"))) for kind in counts}
