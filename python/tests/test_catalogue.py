"""Tests for the catalogue: storage, checks, tree ownership and new games."""

import json

import pytest
from helpers import map_text

from waragents.catalogue import CatalogueError, NotFound
from waragents.content import dumps
from waragents.scenario import build_world


def output(action, *args):
    return {"kind": "OUTPUT", "action": action, **({"args": list(args)} if args else {})}


MAP = {
    "name": "Two Rooms", "mode": "CLICK", "maxAgents": 5,
    "dirt": [[0, 0, 0, 0]], "food": [[0, 0, 0, 0]], "plants": [],
    "starts": [{"slot": 1, "x": 0, "y": 0}, {"slot": 2, "x": 3, "y": 0}],
    "criteria": [{"type": "ANNIHILATE", "slot": 1}, {"type": "ANNIHILATE", "slot": 2},
                 {"type": "SURVIVE_TURNS", "turns": 20}],
}


@pytest.fixture
def cat(empty_catalogue):
    return empty_catalogue


def test_create_get_update_delete(cat):
    map_id = cat.create("maps", MAP)
    assert map_id == "two-rooms"
    assert cat.create("maps", MAP) == "two-rooms-2"
    assert cat.get("maps", map_id) == {**MAP, "owner": None, "published": False}
    cat.update("maps", map_id, {**MAP, "name": "Renamed"})
    assert cat.get("maps", map_id)["name"] == "Renamed"  # the id stays the same
    assert [m["id"] for m in cat.list("maps")] == ["two-rooms", "two-rooms-2"]
    cat.delete("maps", map_id)
    with pytest.raises(NotFound):
        cat.get("maps", map_id)


def test_ids_cannot_escape_the_catalogue(cat):
    for bad in ("../secrets", "a/b", "UPPER", ""):
        with pytest.raises(NotFound):
            cat.get("maps", bad)
    with pytest.raises(NotFound):
        cat.list("passwords")


def test_saves_are_checked(cat):
    with pytest.raises(CatalogueError, match="isn't on a tile"):
        cat.create("maps", {**MAP, "starts": [{"slot": 1, "x": 9, "y": 0}]})
    with pytest.raises(CatalogueError, match="colour must look like"):
        cat.create("players", {"name": "Sam", "colour": "red"})
    with pytest.raises(CatalogueError, match="isn't a player"):
        cat.create("trees", {"name": "t", "owner": "nobody", "root": None})


def test_a_new_one_tile_map_can_be_saved_but_not_played(cat):
    draft = {"name": "Draft", "mode": "FIXED", "maxAgents": 10, "dirt": [[0]], "food": [[0]],
             "plants": [], "starts": [], "criteria": []}
    cat.create("maps", draft)
    cat.create("trees", {"name": "wait", "owner": None, "root": output("DEFEND")})
    with pytest.raises(CatalogueError, match="the map needs at least one start"):
        cat.new_game("draft", [{"slot": 1, "tree": "wait"}], seed=1)


def test_trees_are_unique_per_owner(cat):
    sam = cat.create("players", {"name": "Sam"})
    cat.create("trees", {"name": "t", "owner": None, "root": None})
    cat.create("trees", {"name": "t", "owner": sam, "root": None})  # same name, different owner
    with pytest.raises(CatalogueError, match="already a tree of sam's called 't'"):
        cat.create("trees", {"name": "t", "owner": sam, "root": output("EAT")})
    with pytest.raises(CatalogueError, match="still owns 1 tree"):
        cat.delete("players", sam)


def test_players_who_own_maps_cannot_be_deleted(cat):
    sam = cat.create("players", {"name": "Sam"})
    cat.create("maps", {**MAP, "owner": sam})
    with pytest.raises(CatalogueError, match="still owns 1 map"):
        cat.delete("players", sam)


def test_players_see_their_trees_then_the_defaults(cat):
    sam = cat.create("players", {"name": "Sam"})
    kim = cat.create("players", {"name": "Kim"})
    cat.create("trees", {"name": "shared", "owner": None, "root": output("DEFEND")})
    cat.create("trees", {"name": "shared", "owner": sam, "root": output("EAT")})
    cat.create("trees", {"name": "secret", "owner": kim, "root": output("EAT")})
    assert set(cat.trees_for(None)) == {"shared"}
    assert cat.trees_for(sam)["shared"]["root"] == output("EAT")
    assert set(cat.trees_for(kim)) == {"shared", "secret"}


def test_new_game_copies_the_trees_a_team_can_switch_to(cat):
    sam = cat.create("players", {"name": "Sam", "colour": "#e03131"})
    cat.create("maps", MAP)
    cat.create("trees", {"name": "calm", "owner": None, "root": output("CHANGE_TREE", "angry")})
    cat.create("trees", {"name": "angry", "owner": None, "root": output("CHANGE_TREE", "calm")})
    cat.create("trees", {"name": "angry", "owner": sam, "root": output("ATTACK_RIGHT")})
    cat.create("trees", {"name": "unused", "owner": None, "root": output("EAT")})

    game_id, game = cat.new_game("two-rooms", [
        {"slot": 1, "player": sam, "tree": "calm"},
        {"slot": 2, "player": None, "tree": "calm", "name": "Bots", "speed": 3},
    ], seed=7)
    sam_team, bots = game["teams"]
    assert (sam_team["name"], sam_team["colour"], sam_team["speed"]) == ("Sam", "#e03131", 10)
    assert sorted(t["name"] for t in sam_team["trees"]) == ["angry", "calm"]
    # Sam's own "angry" tree hides the default one.
    assert next(t for t in sam_team["trees"] if t["name"] == "angry")["root"] == output("ATTACK_RIGHT")
    assert next(t for t in bots["trees"] if t["name"] == "angry")["root"] == output("CHANGE_TREE", "calm")
    assert bots["speed"] == 3
    assert cat.get("games", game_id) == game
    assert build_world(game).time == 0


def test_players_have_a_joined_date_and_a_start_tree(cat):
    sam = cat.create("players", {"name": "Sam", "startTree": "angry"})
    assert cat.get("players", sam)["created"].startswith("20")
    with pytest.raises(CatalogueError, match="startTree must be a tree name"):
        cat.update("players", sam, {"name": "Sam", "startTree": 3})

    cat.create("maps", MAP)
    cat.create("trees", {"name": "calm", "owner": None, "root": output("DEFEND")})
    cat.create("trees", {"name": "angry", "owner": sam, "root": output("ATTACK_RIGHT")})
    _, game = cat.new_game("two-rooms", [{"slot": 1, "player": sam}, {"slot": 2, "tree": "calm"}], seed=1)
    assert [t["startTree"] for t in game["teams"]] == ["angry", "calm"]


def test_new_game_with_one_team_drops_annihilate(cat):
    cat.create("maps", MAP)
    cat.create("trees", {"name": "wait", "owner": None, "root": output("DEFEND")})
    _, game = cat.new_game("two-rooms", [{"slot": 2, "tree": "wait"}], seed=1)
    assert game["criteria"] == [{"type": "SURVIVE_TURNS", "turns": 20}]
    assert game["teams"][0]["name"] == "Team 1"


def test_new_game_refuses_trees_the_player_cannot_use(cat):
    kim = cat.create("players", {"name": "Kim"})
    cat.create("maps", MAP)
    cat.create("trees", {"name": "secret", "owner": kim, "root": output("EAT")})
    cat.create("trees", {"name": "draft", "owner": None, "root": None})
    with pytest.raises(CatalogueError, match="isn't one of the default trees"):
        cat.new_game("two-rooms", [{"slot": 1, "tree": "secret"}], seed=1)
    with pytest.raises(CatalogueError, match="this slot is empty"):
        cat.new_game("two-rooms", [{"slot": 1, "tree": "draft"}], seed=1)


def test_import_renames_clashing_trees(cat):
    cat.create("trees", {"name": "main", "owner": None, "root": output("EAT")})
    text = map_text(players=[
        ("red", 0, 0, ["main (OUTPUT CHANGE_TREE other)", "other (OUTPUT CHANGE_TREE main)"]),
        ("blue", 4, 4, ["main (OUTPUT DEFEND)"]),
    ], criteria=["ANNIHILATE blue"])
    result = cat.import_map(text, "Imported")
    assert result == {"map": "imported", "trees": ["main-2", "other", "main-3"]}
    assert cat.get("trees", "main-2")["root"] == output("CHANGE_TREE", "other")
    assert cat.get("trees", "other")["root"] == output("CHANGE_TREE", "main-2")
    assert cat.get("maps", "imported")["criteria"] == [{"type": "ANNIHILATE", "slot": 2}]


def test_dumps_keeps_rows_and_small_objects_on_one_line():
    text = dumps({"dirt": [[0] * 40, [1] * 40], "node": {"kind": "OUTPUT", "action": "EAT"}})
    assert '\n    [0, 0, 0' in text
    assert '"node": {"kind": "OUTPUT", "action": "EAT"}' in text
    assert json.loads(text)["dirt"][1][0] == 1
