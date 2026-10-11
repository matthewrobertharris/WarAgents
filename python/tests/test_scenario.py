"""Tests for the JSON formats: trees, maps with holes, game records and .map import."""

import copy

import pytest
from helpers import FIXTURES

from waragents import parse_tree
from waragents.actions import Activity
from waragents.scenario import (ScenarioError, build_world, check_game, check_map, check_tree,
                                import_map_text, rename_trees, tree_from_json, tree_references,
                                tree_to_json)
from waragents.world import XY

MOVE5 = "(OUTPUT MOVE_LEFT) (OUTPUT MOVE_RIGHT) (OUTPUT MOVE_UP) (OUTPUT MOVE_DOWN) (OUTPUT DEFEND)"


def output(action, *args):
    return {"kind": "OUTPUT", "action": action, **({"args": list(args)} if args else {})}


def tree(root, name="t"):
    return {"name": name, "owner": None, "root": root}


def a_map(**changes):
    data = {
        "name": "test", "mode": "CLICK", "maxAgents": 10,
        "dirt": [[0, 0, 0], [0, None, 0], [0, 0, 0]],
        "food": [[0, 0, 0], [0, None, 0], [0, 0, 5]],
        "plants": [], "starts": [{"slot": 1, "x": 0, "y": 0}, {"slot": 2, "x": 2, "y": 2}],
        "criteria": [{"type": "SURVIVE_TURNS", "turns": 5}],
    }
    return {**data, **changes}


def a_game(root=None, map_data=None, teams=None, criteria=None):
    team = {"slot": 1, "name": "red", "speed": 10, "health": 100, "power": 10,
            "startTree": "t", "trees": [tree(root or output("DEFEND"))]}
    return {"name": "g", "seed": 1, "map": map_data or a_map(), "teams": teams or [team],
            "criteria": criteria if criteria is not None else [{"type": "SURVIVE_TURNS", "turns": 5}]}


# ---- trees -------------------------------------------------------------------------


def test_tree_json_round_trips_through_the_map_syntax():
    source = (f"t (BOOLEAN HAS_ENEMY LEFT (OUTPUT ATTACK_LEFT) (NUMERIC RANDOM VALUE 30 "
              f"(OUTPUT SET_PRIMARY XY_VALUE 1 2) (OUTPUT CHANGE_TREE other) "
              f"(POSITION DIRECTION_TO PRIMARY {MOVE5})))")
    parsed = parse_tree(source)
    data = tree_to_json(parsed)
    assert data["root"]["inputs"] == [{"name": "HAS_ENEMY", "args": ["LEFT"]}]
    assert data["root"]["children"][1]["children"][0] == output("SET_PRIMARY", {"x": 1, "y": 2})
    rebuilt = tree_from_json(data)
    assert rebuilt.source() == parsed.source()
    # Node ids are in the same order as the parser's, so paths highlight the same nodes.
    assert [n.id for n in rebuilt.nodes()] == [n.id for n in parsed.nodes()]


def test_check_tree_reports_paths_and_allows_empty_slots_in_drafts():
    root = {"kind": "BOOLEAN", "inputs": [{"name": "HAS_FOOD", "args": [None]}],
            "children": [output("EAT"), {"kind": "NUMERIC", "inputs": [{"name": "RANDOM"}, None],
                                          "children": [None, output("FLY"), output("DEFEND")]}]}
    assert [str(p) for p in check_tree(tree(root))] == ["root › false › =: unknown action 'FLY'"]
    strict = check_tree(tree(root), allow_empty=False)
    assert [p.path for p in strict] == [(), (1,), (1, 0), (1, 1)]
    assert "HAS_FOOD needs its position filled in" in str(strict[0])
    assert "choose a numeric input" in str(strict[1])


@pytest.mark.parametrize("root, message", [
    ({"kind": "BOOLEAN", "inputs": [{"name": "RANDOM"}], "children": [None, None]},
     "BOOLEAN nodes need boolean inputs, but RANDOM is a numeric input"),
    ({"kind": "BOOLEAN", "inputs": [{"name": "LEGAL_MOVE"}], "children": [output("EAT")]},
     "BOOLEAN nodes need 2 branches (true, false)"),
    ({"kind": "BOOLEAN", "inputs": [{"name": "HAS_FOOD", "args": ["SIDEWAYS"]}], "children": [None, None]},
     "unknown position 'SIDEWAYS'"),
    ({"kind": "NUMERIC", "inputs": [{"name": "VALUE", "args": [True]}, {"name": "TIME"}],
      "children": [None, None, None]}, "VALUE needs a whole number"),
    (output("CHANGE_TREE"), "CHANGE_TREE takes 1 argument (name)"),
    ({"kind": "LOOP"}, "unknown node kind 'LOOP'"),
])
def test_tree_mistakes(root, message):
    assert message in " | ".join(str(p) for p in check_tree(tree(root)))


def test_a_draft_can_have_a_leaf_without_an_action():
    # The editor makes a DO node before its action is chosen.
    draft = tree({"kind": "BOOLEAN", "inputs": [{"name": "LEGAL_MOVE"}],
                  "children": [{"kind": "OUTPUT", "action": None}, output("DEFEND")]})
    assert check_tree(draft) == []
    assert [(p.path, p.message) for p in check_tree(draft, allow_empty=False)] == [((0,), "choose an action")]


def test_playable_trees_cannot_have_empty_slots():
    with pytest.raises(ScenarioError, match="this slot is empty"):
        tree_from_json(tree(None))


def test_tree_references_and_renames():
    data = tree({"kind": "BOOLEAN", "inputs": [{"name": "CURRENT_TREE", "args": ["a"]}],
                 "children": [output("CHANGE_TREE", "b"), output("CHANGE_TREE", "a")]}, name="a")
    assert tree_references(data) == {"a", "b"}
    renamed = rename_trees(data, {"a": "a-2"})
    assert renamed["name"] == "a-2"
    assert renamed["root"]["inputs"][0]["args"] == ["a-2"]
    assert tree_references(renamed) == {"a-2", "b"}
    assert data["name"] == "a"  # the original is untouched


# ---- maps and holes ------------------------------------------------------------------


def test_check_map_finds_mistakes():
    assert check_map(a_map()) == []
    problems = check_map(a_map(
        food=[[0, 0, 0], [0, 0, 0], [0, 0, 999]],
        starts=[{"slot": 1, "x": 1, "y": 1}],
        plants=[{"x": 5, "y": 0, "rate": 3}],
        criteria=[{"type": "ANNIHILATE", "slot": 4}, {"type": "WIN"}],
    ))
    assert problems == [
        "x=1 y=1 is a hole in one of dirt and food but not the other",
        "food at x=2 y=2 must be a whole number from 0 to 100",
    ]
    problems = check_map(a_map(starts=[{"slot": 1, "x": 1, "y": 1}], plants=[{"x": 5, "y": 0, "rate": 3}],
                               criteria=[{"type": "ANNIHILATE", "slot": 4}, {"type": "WIN"}]))
    assert problems == [
        "plant 0 at x=5 y=0 isn't on a tile",
        "slot 1's start at x=1 y=1 isn't on a tile",
        "unknown criterion 'WIN'",
        "ANNIHILATE refers to slot 4, which has no start",
    ]


def test_unfinished_maps_can_be_saved_but_not_played():
    data = a_map(starts=[], criteria=[{"type": "ANNIHILATE", "slot": 1}, {"type": "TRAVEL_TO", "slot": 1, "x": 1, "y": 1}])
    assert check_map(data, allow_unfinished=True) == []
    assert check_map(data) == [
        "the map needs at least one start",
        "ANNIHILATE refers to slot 1, which has no start",
        "TRAVEL_TO refers to slot 1, which has no start",
        "TRAVEL_TO at x=1 y=1 isn't on a tile",
    ]
    # Real mistakes still count while editing.
    assert check_map(a_map(mode="FAST"), allow_unfinished=True) == ["mode must be one of CLICK, CONST, FIXED"]


def test_holes_count_as_off_the_map():
    # A 3x1 strip with a hole in the middle. The agent at x=0 can't move right into the hole,
    # and IN_BOUNDS RIGHT is false.
    data = a_map(dirt=[[0, None, 0]], food=[[0, None, 0]], starts=[{"slot": 1, "x": 0, "y": 0}],
                 criteria=[])
    root = {"kind": "BOOLEAN", "inputs": [{"name": "IN_BOUNDS", "args": ["RIGHT"]}],
            "children": [output("DEFEND"), output("MOVE_RIGHT")]}
    world = build_world(a_game(root, map_data=data, criteria=[]))
    assert not world.in_bounds(XY(1, 0))
    world.step()
    agent = world.agents[0]
    assert agent.pos == XY(0, 0)
    assert agent.action.activity is Activity.MOVE_RIGHT
    assert [e.message for e in world.events if e.kind == "fail"] == [
        "Cannot MOVE_RIGHT because of out of bounds"]


def test_plants_do_not_spill_into_holes():
    data = a_map(dirt=[[0, None, 0]], food=[[0, None, 0]], plants=[{"x": 0, "y": 0, "rate": 16}],
                 starts=[{"slot": 1, "x": 2, "y": 0}], criteria=[])
    world = build_world(a_game(map_data=data, criteria=[]))
    world.step()
    assert world.tile(XY(0, 0)).food == 8


# ---- games ---------------------------------------------------------------------------


def test_build_world_from_a_game_record():
    team2 = {"slot": 2, "name": "blue", "colour": "#1c7ed6", "speed": 12, "health": 50, "power": 7,
             "startTree": "t", "trees": [tree(output("MOVE_LEFT"))]}
    game = a_game(criteria=[{"type": "ANNIHILATE", "slot": 2}, {"type": "SURVIVE_TURNS", "turns": 9}])
    game["teams"].append(team2)
    world = build_world(game)
    assert [p.name for p in world.players] == ["red", "blue"]
    blue = world.players[1]
    assert blue.colour == "#1c7ed6"
    assert (blue.agents[0].id, blue.agents[0].pos, blue.agents[0].max_health) == ("Agent1", XY(2, 2), 50)
    assert [c.source() for c in world.criteria] == ["ANNIHILATE blue", "SURVIVE_TURNS 9"]
    assert world.seed == 1


def test_criteria_for_slots_without_a_team_are_skipped():
    world = build_world(a_game(criteria=[{"type": "ANNIHILATE", "slot": 2}]))
    assert world.criteria == []


def test_check_game_finds_team_mistakes():
    game = a_game()
    game["teams"][0].update(slot=7, speed=0, startTree="missing")
    game["teams"][0]["trees"].append(tree(output("CHANGE_TREE", "elsewhere"), name="u"))
    assert check_game(game) == [
        "team 'red' uses slot 7, which the map doesn't have",
        "team 'red' needs a speed of at least 1",
        "team 'red' starts with tree 'missing', which it doesn't have",
        "team 'red': 'u' switches to tree 'elsewhere', which the team doesn't have",
    ]


def test_the_same_record_replays_the_same_game():
    game = a_game(output("REPRODUCE"))
    first, second = build_world(copy.deepcopy(game)), build_world(copy.deepcopy(game))
    for _ in range(4):
        first.step()
        second.step()
    assert [(a.id, a.pos, a.max_health) for a in first.agents] == [
        (a.id, a.pos, a.max_health) for a in second.agents]


# ---- importing .map files ------------------------------------------------------------


def test_import_map_text_makes_slots_and_json_trees():
    text = (FIXTURES.parent / "maps" / "node.map").read_text()
    data, teams = import_map_text(text, "node")
    assert check_map(data) == []
    assert [t["slot"] for t in teams] == [1, 2, 3, 4, 5]
    assert data["starts"][2] == {"slot": 3, "x": 2, "y": 2}
    assert data["criteria"] == [
        {"type": "PERFORM_ACTION", "slot": 3, "action": "MOVE_LEFT", "times": 5},
        {"type": "TRAVEL_TO", "slot": 3, "x": 0, "y": 0},
    ]
    assert [t["name"] for t in teams[2]["trees"]] == ["default", "second"]
