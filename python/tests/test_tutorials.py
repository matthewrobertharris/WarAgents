"""The bundled tutorials, and Training through the web app.

Every tutorial's model answer has to complete it, and a tree that only defends has to fail it
(unless defending is the lesson), so the tutorials are checked along with the engine.
"""

import json
import shutil

import pytest
from conftest import sign_up

from waragents.battles import run_to_end
from waragents.catalogue import Catalogue
from waragents.progression import MODE_XP_FACTOR, TUTORIAL_BONUS
from waragents.training import TRACKS, check_tutorial
from waragents.web.app import DEFAULT_CATALOGUE

TUTORIALS = sorted((DEFAULT_CATALOGUE / "tutorials").glob("*.json"))
DEFEND = {"name": "defend-only", "owner": None, "root": {"kind": "OUTPUT", "action": "DEFEND"}}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def play(tmp_path, tutorial, trees, seed=1):
    """Play a tutorial with these trees for the player (the first is the start tree)."""
    cat = Catalogue(tmp_path / "cat")
    team = {"slot": 1, "trees": trees, "startTree": trees[0]["name"], **tutorial.get("team", {})}
    bots = [{**bot, "player": None} for bot in tutorial.get("bots", [])]
    _, record = cat.new_game(tutorial["map"], [team, *bots], seed, mode="training",
                             extra={"maxTurns": tutorial["maxTurns"]})
    return run_to_end(record)


def test_there_are_tutorials_in_every_early_track():
    tracks = {load(p)["track"] for p in TUTORIALS}
    assert {"Movement", "Food", "Combat", "Dirt", "Reproduction"} <= tracks <= set(TRACKS)


@pytest.mark.parametrize("path", TUTORIALS, ids=lambda p: p.stem)
def test_each_tutorial_is_valid(path):
    tutorial = load(path)
    assert check_tutorial(tutorial) == []
    for other in tutorial.get("recommendedAfter", []):
        assert (path.parent / f"{other}.json").exists()


@pytest.mark.parametrize("path", TUTORIALS, ids=lambda p: p.stem)
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_the_model_answer_completes_the_tutorial(tmp_path, path, seed):
    tutorial = load(path)
    world = play(tmp_path, tutorial, [tutorial["solution"], *tutorial.get("solutionTrees", [])], seed)
    assert world.result["winners"] == [1] or 1 in world.result["winners"], world.outcome
    assert world.time <= tutorial["maxTurns"]


def test_the_corridor_has_no_loops():
    """A loop in the corridor would let a tree that follows one wall go round it forever. With
    no loops, the open tiles form a tree: one fewer joins between neighbours than tiles."""
    dirt = load(DEFAULT_CATALOGUE / "tutorials" / "movement-5.json")["map"]["dirt"]
    tiles = {(x, y) for y, row in enumerate(dirt) for x, d in enumerate(row) if d is not None}
    joins = sum((x + 1, y) in tiles for x, y in tiles) + sum((x, y + 1) in tiles for x, y in tiles)
    assert joins == len(tiles) - 1


@pytest.mark.parametrize("path", TUTORIALS, ids=lambda p: p.stem)
def test_just_defending_does_not_complete_the_tutorial(tmp_path, path):
    tutorial = load(path)
    if tutorial["solution"]["root"] == DEFEND["root"]:
        pytest.skip("defending is the lesson")
    world = play(tmp_path, tutorial, [DEFEND])
    assert 1 not in world.result["winners"], world.outcome


# ---- through the web app ------------------------------------------------------------------


@pytest.fixture
def trained(app, catalogue_dir):
    shutil.copytree(DEFAULT_CATALOGUE / "tutorials", catalogue_dir / "tutorials")
    sign_up(app, "Admin")
    return sign_up(app, "Alice")


def test_list_and_read_tutorials(trained):
    tutorials = trained.get("/api/training").json
    assert tutorials[0]["id"] == "movement-1" and tutorials[0]["completed"] is False
    assert [t["track"] for t in tutorials] == sorted((t["track"] for t in tutorials), key=TRACKS.index)
    one = trained.get("/api/training/movement-2").json
    assert one["solution"]["root"]["kind"] == "BOOLEAN"
    assert (one["tree"], one["previous"], one["next"]) == (None, "movement-1", "movement-3")
    assert trained.get("/api/catalogue/tutorials").status_code == 403


def test_complete_a_tutorial(app, trained):
    tree_id = trained.post("/api/training/movement-1/tree").json["treeId"]
    assert trained.post("/api/training/movement-1/tree").json["treeId"] == tree_id  # made once

    unfinished = trained.post("/api/training/movement-1/run", json={})
    assert unfinished.status_code == 400  # the new tree is empty

    trained.put(f"/api/catalogue/trees/{tree_id}",
                json={"name": "tut-movement-1", "root": {"kind": "OUTPUT", "action": "MOVE_RIGHT"}})
    first = trained.post("/api/training/movement-1/run", json={"seed": 4}).json
    assert first["passed"] and first["firstTime"]
    reward = first["result"]["rewards"]["alice"]
    assert reward["bonus"] == TUTORIAL_BONUS["Beginner"]
    assert reward["fromAgents"] == round(reward["agentXp"] * MODE_XP_FACTOR["training"])
    me = trained.get("/api/me").json
    assert me["xp"] == reward["total"] and me["training"]["movement-1"]["turns"] == 7

    again = trained.post("/api/training/movement-1/run", json={}).json
    assert again["passed"] and not again["firstTime"] and again["result"]["rewards"]["alice"]["total"] == 0
    assert trained.get("/api/me").json["xp"] == reward["total"]
    assert trained.get("/api/training").json[0]["completed"] is True
    assert trained.get("/api/history").json[0]["mode"] == "training"


def test_a_failed_run_earns_nothing(trained):
    trained.post("/api/training/movement-2/tree")
    trained.put("/api/catalogue/trees/tut-movement-2",
                json={"name": "tut-movement-2", "root": {"kind": "OUTPUT", "action": "MOVE_RIGHT"}})
    run = trained.post("/api/training/movement-2/run", json={}).json
    assert not run["passed"] and run["result"]["rewards"]["alice"]["total"] == 0
    assert "movement-2" not in trained.get("/api/me").json.get("training", {})


def test_tutorial_progress_cannot_be_faked(trained):
    trained.put("/api/catalogue/players/alice", json={"name": "Alice", "training": {"movement-7": {"turns": 1}}})
    trained.put("/api/me", json={"training": {"movement-7": {"turns": 1}}})
    assert trained.get("/api/me").json.get("training") is None
