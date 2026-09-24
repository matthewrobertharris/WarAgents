"""Tests for the parser, the turn loop, inputs and criteria, including fixes to Java behaviour."""

import pytest
from helpers import FIXTURES, load, make, map_text

from waragents import MapFormatError, parse_map, parse_tree
from waragents.actions import Activity
from waragents.world import XY

MOVE5 = "(OUTPUT MOVE_LEFT) (OUTPUT MOVE_RIGHT) (OUTPUT MOVE_UP) (OUTPUT MOVE_DOWN) (OUTPUT DEFEND)"


# ---- parsing -------------------------------------------------------------------


def test_every_current_format_fixture_parses():
    failures = []
    for path in FIXTURES.rglob("*.map"):
        if path.name == "test_changeTree_fail_agentNoTree.map":
            continue  # two agents on one tile, see test_outputs
        try:
            parse_map(path.read_text())
        except MapFormatError as e:
            failures.append(f"{path.name}: {e}")
    assert failures == []


def test_bare_action_is_shorthand_for_output():
    world = load("basic.map")
    assert world.agents[0].tree.root.action.activity is Activity.DEFEND


def test_tree_source_round_trips():
    source = (f"t (BOOLEAN HAS_ENEMY LEFT (OUTPUT ATTACK_LEFT) (NUMERIC RANDOM VALUE 30 "
              f"(OUTPUT SET_PRIMARY XY_VALUE 1 2) (OUTPUT CHANGE_TREE other) "
              f"(POSITION DIRECTION_TO PRIMARY {MOVE5})))")
    tree = parse_tree(source)
    assert parse_tree(tree.source().removeprefix("tree=")).source() == tree.source()
    assert [n.id for n in tree.nodes()] == list(range(len(tree.nodes())))


@pytest.mark.parametrize("tree, message", [
    ("t (OUTPUT FLY)", "unknown action 'FLY'"),
    ("t (BOOLEAN RANDOM (OUTPUT DEFEND) (OUTPUT DEFEND))", "BOOLEAN nodes need boolean inputs"),
    ("t (NUMERIC VALUE 1 (OUTPUT DEFEND))", "NUMERIC nodes need 2 numeric inputs, found OUTPUT"),
    ("t (NUMERIC VALUE x VALUE 2 (OUTPUT DEFEND))", "expected a number for VALUE's value but found 'x'"),
    ("t (BOOLEAN LEGAL_MOVE (OUTPUT DEFEND))", "tree ended early"),
    ("t (OUTPUT DEFEND) (OUTPUT DEFEND)", "extra tokens"),
    ("t (BOOLEAN HAS_FOOD SIDEWAYS (OUTPUT DEFEND) (OUTPUT DEFEND))", "unknown position 'SIDEWAYS'"),
    ("t (BOOLEAN ENEMY_SPEED (OUTPUT DEFEND) (OUTPUT DEFEND))", "unknown input 'ENEMY_SPEED'"),
])
def test_tree_errors(tree, message):
    with pytest.raises(MapFormatError, match=message):
        parse_tree(tree)


def test_map_errors_report_line_numbers():
    text = map_text(players=[("red", 9, 9, ["t (OUTPUT DEFEND)"])])
    with pytest.raises(MapFormatError, match=r"Line 17: player 'red' starts at x=9 y=9, which is off the map"):
        parse_map(text)


def test_legacy_decision_format_is_explained():
    with pytest.raises(MapFormatError, match="old 'decision=' format"):
        parse_map((FIXTURES.parent / "maps" / "attack.map").read_text())


def test_grid_rows_are_y():
    world = make(width=3, height=2, food=[[1, 2, 3], [4, 5, 6]],
                 players=[("red", 0, 0, ["t (OUTPUT DEFEND)"])])
    assert world.tile(XY(2, 0)).food == 3
    assert world.tile(XY(0, 1)).food == 4


# ---- turn loop -----------------------------------------------------------------


def test_faster_agents_bubble_forward_one_place_per_turn():
    world = make(width=5, height=1, players=[
        ("slow", 0, 0, ["t (OUTPUT DEFEND)"], {"speed": 1}),
        ("mid", 2, 0, ["t (OUTPUT DEFEND)"], {"speed": 5}),
        ("fast", 4, 0, ["t (OUTPUT DEFEND)"], {"speed": 9}),
    ])
    names = lambda: [a.player.name for a in world.agents]
    world.step()
    assert names() == ["mid", "fast", "slow"]
    world.step()
    assert names() == ["fast", "mid", "slow"]


def test_newborns_act_from_the_next_turn():
    world = make(players=[("red", 2, 2, ["t (OUTPUT REPRODUCE)"])], max_agents=2)
    world.step()
    child = world.agents[1]
    assert child.action is None
    world.step()
    assert child.action.activity is Activity.REPRODUCE


def test_plants_feed_their_tile_and_neighbours():
    world = make(plants=[(0, 0, 16)], players=[("red", 4, 4, ["t (OUTPUT DEFEND)"])])
    world.step()
    assert world.tile(XY(0, 0)).food == 8
    assert world.tile(XY(1, 0)).food == 2
    assert world.tile(XY(0, 1)).food == 2
    assert world.tile(XY(1, 1)).food == 0


def test_same_seed_same_game():
    tree = f"t (NUMERIC RANDOM VALUE 50 (OUTPUT REPRODUCE) (OUTPUT DEFEND) (POSITION ENEMY_ADJACENT_POS {MOVE5}))"
    kwargs = dict(width=8, height=8, food=5, players=[("red", 1, 1, [tree]), ("blue", 6, 6, [tree])])

    def run(seed):
        world = make(seed=seed, **kwargs)
        for _ in range(30):
            world.step()
        return [(a.id, a.pos, a.health) for a in world.agents]

    assert run(7) == run(7)
    assert run(7) != run(8)


# ---- behaviour fixed during the port -------------------------------------------


def test_numeric_inputs_are_evaluated_once_per_decision():
    # Java evaluated RANDOM again for the ">" check, so "=" and ">" had skewed odds.
    world = make(players=[("red", 2, 2, ["t (NUMERIC RANDOM RANDOM (OUTPUT MOVE_LEFT) (OUTPUT DEFEND) (OUTPUT MOVE_RIGHT))"])])
    calls = []
    original = world.rng.randrange
    world.rng.randrange = lambda n: calls.append(n) or original(n)
    world.update_agent(world.agents[0])
    assert len(calls) == 2


def test_previous_is_the_tile_before_the_current_one():
    # Java stored the agent's mutable position object in its visited list, so PREVIOUS
    # became the current tile after the second move.
    world = make(players=[("red", 4, 2, ["t (OUTPUT MOVE_LEFT)"])])
    agent = world.agents[0]
    world.step()
    world.step()
    assert agent.pos == XY(2, 2)
    assert agent.previous_pos == XY(3, 2)


def test_remembered_position_does_not_follow_the_agent():
    world = make(players=[("red", 2, 2, ["a (OUTPUT SET_PRIMARY CURRENT)", "b (OUTPUT MOVE_LEFT)"])])
    agent = world.agents[0]
    world.update_agent(agent)
    agent.tree = agent.player.tree("b")
    world.update_agent(agent)
    assert agent.primary == XY(2, 2)


@pytest.mark.parametrize("tree, expected", [
    ("t (BOOLEAN ENEMY_ADJACENT (OUTPUT ATTACK_LEFT) (OUTPUT DEFEND))", Activity.DEFEND),
    ("t (BOOLEAN ALLY_ADJACENT (OUTPUT ATTACK_LEFT) (OUTPUT DEFEND))", Activity.DEFEND),
    ("t (BOOLEAN PLANT_ADJACENT (OUTPUT ATTACK_LEFT) (OUTPUT DEFEND))", Activity.DEFEND),
    ("t (BOOLEAN IN_BOUNDS LEFT (OUTPUT ATTACK_LEFT) (OUTPUT DEFEND))", Activity.DEFEND),
])
def test_neighbour_checks_at_the_map_edge_are_false_not_confused(tree, expected):
    # Java threw (and so CONFUSED the agent) on empty or off-map neighbours.
    world = make(players=[("red", 0, 0, [tree])])
    world.update_agent(world.agents[0])
    assert world.agents[0].action.activity is expected


def test_food_adjacent_sees_food_on_empty_tiles():
    world = make(food=[[0, 5, 0, 0, 0]] + [[0] * 5] * 4,
                 players=[("red", 0, 0, ["t (BOOLEAN FOOD_ADJACENT (OUTPUT MOVE_RIGHT) (OUTPUT DEFEND))"])])
    world.update_agent(world.agents[0])
    assert world.agents[0].action.activity is Activity.MOVE_RIGHT


def test_enemy_adjacent_pos_finds_enemies_not_allies():
    tree = f"t (POSITION ENEMY_ADJACENT_POS {MOVE5})"
    for seed in range(10):
        world = make(seed=seed, players=[("red", 2, 2, [tree]), ("blue", 3, 2, ["t (OUTPUT DEFEND)"])])
        world.update_agent(world.agents[0])
        assert world.agents[0].action.activity is Activity.MOVE_RIGHT


def test_previous_action_checks_the_named_action():
    tree = "t (BOOLEAN SELF_PREVIOUS_ACTION MOVE_LEFT (OUTPUT DEFEND) (OUTPUT MOVE_LEFT))"
    world = make(players=[("red", 4, 2, [tree])])
    agent = world.agents[0]
    activities = []
    for _ in range(4):
        world.step()
        activities.append(agent.action.activity)
    assert activities == [Activity.MOVE_LEFT, Activity.DEFEND, Activity.MOVE_LEFT, Activity.DEFEND]


# ---- criteria ------------------------------------------------------------------


def test_survive_turns():
    world = make(players=[("red", 0, 0, ["t (OUTPUT DEFEND)"])], criteria=["SURVIVE_TURNS 3"])
    for _ in range(3):
        world.step()
    assert world.finished
    assert world.outcome == "Survived 3 turns"
    assert world.step() == []


def test_annihilate_win_and_loss():
    win = make(width=2, height=1, players=[("red", 0, 0, ["t (OUTPUT ATTACK_RIGHT)"], {"power": 200}),
                                           ("blue", 1, 0, ["t (OUTPUT DEFEND)"])],
               criteria=["ANNIHILATE red"])
    win.step()
    assert win.outcome == "red annihilated every other team"

    loss = make(width=2, height=1, players=[("red", 0, 0, ["t (OUTPUT DEFEND)"]),
                                            ("blue", 1, 0, ["t (OUTPUT ATTACK_LEFT)"], {"power": 200})],
                criteria=["ANNIHILATE red"])
    loss.step()
    assert loss.outcome == "Game over: red has no agents left"


def test_travel_to():
    world = make(players=[("red", 3, 0, ["t (OUTPUT MOVE_LEFT)"])], criteria=["TRAVEL_TO red 1 0"])
    world.step()
    assert not world.finished
    world.step()
    assert world.outcome == "red reached x=1 y=0"


def test_perform_action():
    world = make(players=[("red", 0, 0, ["t (OUTPUT DEFEND)"])], criteria=["PERFORM_ACTION red DEFEND 2"])
    world.step()
    assert not world.finished
    world.step()
    assert world.finished


def test_collect_food():
    world = make(food=20, players=[("red", 0, 0, ["t (BOOLEAN HAS_FOOD CURRENT (OUTPUT LIFT_FOOD) (OUTPUT DEFEND))"])],
                 criteria=["COLLECT_FOOD red 10"])
    world.step()
    assert world.outcome == "red collected 10 food"


def test_map_dirt():
    world = make(dirt=3, players=[("red", 1, 1, ["t (OUTPUT LIFT_DIRT)"])], criteria=["MAP_DIRT 1 1 1"])
    world.step()
    assert world.finished


def test_find_thing():
    world = make(plants=[(0, 0, 8)], players=[("red", 2, 0, ["t (OUTPUT MOVE_LEFT)"])],
                 criteria=["FIND_THING Plant0"])
    world.step()
    assert world.outcome == "red found Plant0"


def test_game_ends_when_everyone_is_dead():
    world = make(players=[("red", 0, 0, ["t (OUTPUT DEATH)"])])
    world.step()
    assert world.outcome == "Game over: no agents left"
