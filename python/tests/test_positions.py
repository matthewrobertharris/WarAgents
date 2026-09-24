"""Ports of the Java tests in test/model/position, using the same fixture maps.

Each fixture's tree is `POSITION DIRECTION_TO <position> (MOVE_LEFT) (MOVE_RIGHT) (MOVE_UP)
(MOVE_DOWN) (DEFEND)`, so the action shows which way the position pointed.
"""

import pytest
from helpers import load

from waragents.actions import Activity
from waragents.world import XY


def position_of(world, agent):
    return agent.tree.root.inputs[0].position.resolve(agent, world)


def pos_map(name: str) -> str:
    return f"positionMaps/test_{name}.map"


@pytest.mark.parametrize("name, offset, activity", [
    ("up", (0, 1), Activity.MOVE_UP),
    ("down", (0, -1), Activity.MOVE_DOWN),
    ("left", (-1, 0), Activity.MOVE_LEFT),
    ("right", (1, 0), Activity.MOVE_RIGHT),
])
def test_adjacent(name, offset, activity):
    world = load(pos_map(f"{name}_success"))
    agent = world.agents[0]
    assert position_of(world, agent) == agent.pos.offset(*offset)
    assert world.update_agent(agent)
    assert agent.action.activity is activity


@pytest.mark.parametrize("name", ["up", "down", "left", "right"])
def test_adjacent_off_map_confuses(name):
    world = load(pos_map(f"{name}_fail_outOfBounds"))
    agent = world.agents[0]
    assert position_of(world, agent) is None
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.CONFUSED
    assert len(world.agents) == 1


def test_current():
    world = load(pos_map("current_success"))
    agent = world.agents[0]
    assert position_of(world, agent) == agent.pos
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.DEFEND


def test_previous():
    world = load(pos_map("previous_success"))
    agent = world.agents[0]
    agent.visited.insert(0, XY(1, 2))
    assert position_of(world, agent) == XY(1, 2)
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.MOVE_LEFT


def test_previous_not_set():
    world = load(pos_map("previous_fail_noPrevious"))
    agent = world.agents[0]
    assert position_of(world, agent) is None
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.CONFUSED


@pytest.mark.parametrize("slot", ["primary", "secondary"])
def test_memory_slot(slot):
    world = load(pos_map(f"{slot}_success"))
    agent = world.agents[0]
    setattr(agent, slot, XY(0, 2))
    assert position_of(world, agent) == XY(0, 2)
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.MOVE_LEFT


@pytest.mark.parametrize("slot", ["primary", "secondary"])
def test_memory_slot_not_set(slot):
    world = load(pos_map(f"{slot}_fail_notSet"))
    agent = world.agents[0]
    assert position_of(world, agent) is None
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.CONFUSED


def test_xy_value():
    world = load(pos_map("xyvalue_success"))
    agent = world.agents[0]
    assert position_of(world, agent) == XY(0, 0)
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.MOVE_LEFT


@pytest.mark.parametrize("case", ["xTooSmall", "xTooBig", "yTooSmall", "yTooBig"])
def test_xy_value_off_map(case):
    world = load(pos_map(f"xyvalue_fail_{case}"))
    agent = world.agents[0]
    assert position_of(world, agent) is None
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.CONFUSED
