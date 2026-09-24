"""Ports of the Java tests in test/model/output, using the same fixture maps."""

import pytest
from helpers import load, messages

from waragents.actions import CONFUSED_HARM, Activity
from waragents.world import MAX_DIRT, MAX_FOOD, MOVE_HEALTH, PICKUP_DIRT, PICKUP_FOOD, XY

DIRECTIONS = {"Down": (0, -1), "Left": (-1, 0), "Right": (1, 0), "Up": (0, 1)}


def out(name: str) -> str:
    return f"outputMaps/test_{name}.map"


def run_first(world):
    agent = world.agents[0]
    return agent, world.update_agent(agent)


# ---- attacks -------------------------------------------------------------------


@pytest.mark.parametrize("direction", DIRECTIONS)
class TestAttack:
    def activity(self, direction):
        return Activity(f"ATTACK_{direction.upper()}")

    def test_success_both_survive(self, direction):
        world = load(out(f"attack{direction}_success_2survive"))
        agent, ok = run_first(world)
        assert ok
        assert agent.action.activity is self.activity(direction)
        assert len(world.agents) == 2

    def test_success_defender_dies(self, direction):
        world = load(out(f"attack{direction}_success_defenderDeath"))
        _, ok = run_first(world)
        assert ok
        assert len(world.agents) == 1

    @pytest.mark.parametrize("height, damage", [
        ("1", lambda p: 2 * p), ("2", lambda p: 3 * p), ("3", lambda p: 4 * p),
        ("-1", lambda p: p // 2), ("-2", lambda p: p // 3),
    ])
    def test_success_height(self, direction, height, damage):
        world = load(out(f"attack{direction}_success_height{height}"))
        attacker, defender = world.agents
        health = defender.health
        assert world.update_agent(attacker)
        assert len(world.agents) == 2
        assert defender.health == health - damage(attacker.power)

    @pytest.mark.parametrize("height", ["4", "-3"])
    def test_fail_height(self, direction, height):
        world = load(out(f"attack{direction}_fail_height{height}"))
        attacker, defender = world.agents
        health = defender.health
        assert not world.update_agent(attacker)
        assert defender.health == health
        assert messages(world) == [f"Cannot ATTACK_{direction.upper()} because attack failed"]

    def test_fail_no_agent(self, direction):
        world = load(out(f"attack{direction}_fail_noAgent"))
        _, ok = run_first(world)
        assert not ok
        assert messages(world) == [f"Cannot ATTACK_{direction.upper()} because no agent to attack"]

    def test_fail_out_of_bounds(self, direction):
        world = load(out(f"attack{direction}_fail_outofbounds"))
        _, ok = run_first(world)
        assert not ok
        assert messages(world) == [f"Cannot ATTACK_{direction.upper()} because attack is out of bounds"]


# ---- moves ---------------------------------------------------------------------


@pytest.mark.parametrize("direction", DIRECTIONS)
class TestMove:
    @pytest.mark.parametrize("case, dirt, food, cost", [
        ("flat", 0, 0, 0),
        ("flatCarryingDirt", PICKUP_DIRT, 0, MOVE_HEALTH),
        ("flatCarryingFood", 0, PICKUP_FOOD, MOVE_HEALTH),
        ("heightDifference", 0, 0, MOVE_HEALTH),
        ("heightCarryingDirt", PICKUP_DIRT, 0, 2 * MOVE_HEALTH),
        ("heightCarryingFood", 0, PICKUP_FOOD, 2 * MOVE_HEALTH),
    ])
    def test_success(self, direction, case, dirt, food, cost):
        world = load(out(f"move{direction}_success_{case}"))
        agent = world.agents[0]
        agent.dirt, agent.food = dirt, food
        start, health = agent.pos, agent.health
        assert world.update_agent(agent)
        assert agent.action.activity is Activity(f"MOVE_{direction.upper()}")
        assert agent.pos == start.offset(*DIRECTIONS[direction])
        assert agent.health == health - cost
        assert world.agent_at(agent.pos) is agent
        assert world.agent_at(start) is None

    @pytest.mark.parametrize("case, dirt, health, reason", [
        ("heightDifference", 0, None, "because of height difference"),
        ("heightKill", 0, MOVE_HEALTH, "because move would kill"),
        ("heightCarryingKill", PICKUP_DIRT, 2 * MOVE_HEALTH, "because move would kill"),
        ("carryingKill", PICKUP_DIRT, MOVE_HEALTH, "because move would kill"),
        ("outOfBounds", 0, None, "because of out of bounds"),
    ])
    def test_fail(self, direction, case, dirt, health, reason):
        world = load(out(f"move{direction}_fail_{case}"))
        agent = world.agents[0]
        agent.dirt = dirt
        if health is not None:
            agent.health = health
        start, health = agent.pos, agent.health
        assert not world.update_agent(agent)
        assert agent.pos == start
        assert agent.health == health
        assert messages(world) == [f"Cannot MOVE_{direction.upper()} {reason}"]

    def test_fail_occupied(self, direction):
        world = load(out(f"move{direction}_fail_occupied"))
        agent, other = world.agents
        start = agent.pos
        assert not world.update_agent(agent)
        assert agent.pos == start
        assert messages(world) == [f"Cannot MOVE_{direction.upper()} because of {other.id}"]


# ---- everything else -----------------------------------------------------------


def test_change_tree_success():
    world = load(out("changeTree_success"))
    agent, ok = run_first(world)
    assert ok
    assert agent.action.activity is Activity.CHANGE_TREE
    assert agent.tree.name == "defend"


def test_change_tree_fail_no_tree():
    world = load(out("changeTree_fail_noTree"))
    agent, ok = run_first(world)
    assert not ok
    assert agent.tree.name == "change"
    assert messages(world) == ["Cannot CHANGE_TREE because no tree with that name exists"]


def test_change_tree_fail_tree_belongs_to_another_player():
    # The Java fixture puts both players on (2, 2), which this parser rejects, so move one.
    from helpers import load_text

    from waragents import parse_map
    text = load_text(out("changeTree_fail_agentNoTree"))
    head, sep, tail = text.rpartition("name=test1,speed=10,health=100,power=10,x=2,y=2")
    world = parse_map(head + "name=test1,speed=10,health=100,power=10,x=3,y=2" + tail)
    agent, ok = run_first(world)
    assert not ok
    assert agent.tree.name == "change"
    assert messages(world) == ["Cannot CHANGE_TREE because no tree with that name exists"]


def test_clear_primary():
    world = load(out("clearPrimary_success"))
    agent = world.agents[0]
    agent.primary = XY(1, 1)
    assert world.update_agent(agent)
    assert agent.primary is None


def test_clear_secondary():
    world = load(out("clearSecondary_success"))
    agent = world.agents[0]
    agent.secondary = XY(1, 1)
    assert world.update_agent(agent)
    assert agent.secondary is None


def test_set_primary():
    world = load(out("setPrimary_success"))
    agent, ok = run_first(world)
    assert ok
    assert agent.primary == XY(0, 0)


def test_set_secondary():
    world = load(out("setSecondary_success"))
    agent, ok = run_first(world)
    assert ok
    assert agent.secondary == XY(0, 0)


def test_confused_survive():
    world = load(out("confused_success_survive"))
    agent = world.agents[0]
    health = agent.health
    assert world.update_agent(agent)
    assert agent.action.activity is Activity.CONFUSED
    assert agent.health == health - CONFUSED_HARM


def test_confused_death():
    world = load(out("confused_success_survive"))
    agent = world.agents[0]
    agent.health = CONFUSED_HARM - 1
    assert world.update_agent(agent)
    assert world.agents == []
    assert not agent.alive


def test_death():
    world = load(out("death_success"))
    agent, ok = run_first(world)
    assert ok
    assert world.agents == []
    # A dead agent leaves a quarter of its max health behind as food.
    assert world.tile(agent.pos).food == int(agent.max_health * 0.25)


def test_defend_no_attack():
    world = load(out("defend_success_noattack"))
    agent, ok = run_first(world)
    assert ok
    assert agent.action.activity is Activity.DEFEND


def test_defend_halves_attack():
    world = load(out("defend_success_attack"))
    defender, attacker = world.agents
    assert world.update_agent(defender)
    assert world.update_agent(attacker)
    assert defender.health == 5
    assert len(world.agents) == 2


def test_drop_dirt():
    world = load(out("dropDirt_success"))
    agent = world.agents[0]
    before = world.tile(agent.pos).dirt
    agent.dirt = 1
    assert world.update_agent(agent)
    assert world.tile(agent.pos).dirt == before + 1
    assert agent.dirt == 0


def test_drop_dirt_caps_at_max():
    world = load(out("dropDirt_success_maxDirt"))
    agent = world.agents[0]
    agent.dirt = 1
    assert world.update_agent(agent)
    assert world.tile(agent.pos).dirt == MAX_DIRT


def test_drop_dirt_fail():
    world = load(out("dropDirt_fail_noDirt"))
    _, ok = run_first(world)
    assert not ok
    assert messages(world) == ["Cannot DROP_DIRT because agent has no dirt"]


def test_drop_food():
    world = load(out("dropFood_success"))
    agent = world.agents[0]
    before = world.tile(agent.pos).food
    agent.food = 1
    assert world.update_agent(agent)
    assert world.tile(agent.pos).food == before + 1


def test_drop_food_caps_at_max():
    world = load(out("dropFood_success_maxFood"))
    agent = world.agents[0]
    agent.food = 1
    assert world.update_agent(agent)
    assert world.tile(agent.pos).food == MAX_FOOD


def test_drop_food_fail():
    world = load(out("dropFood_fail_noFood"))
    _, ok = run_first(world)
    assert not ok
    assert messages(world) == ["Cannot DROP_FOOD because agent has no food"]


def test_eat_all_food():
    world = load(out("eat_success_allFood"))
    agent = world.agents[0]
    food = world.tile(agent.pos).food
    agent.health = 50
    assert world.update_agent(agent)
    assert agent.health == 50 + food
    assert world.tile(agent.pos).food == 0


def test_eat_partial_food():
    world = load(out("eat_success_partialFood"))
    agent = world.agents[0]
    food = world.tile(agent.pos).food
    agent.health = 95
    assert world.update_agent(agent)
    assert agent.health == agent.max_health
    assert world.tile(agent.pos).food == food - (agent.max_health - 95)


def test_eat_fail_no_food():
    world = load(out("eat_fail_noFood"))
    agent = world.agents[0]
    agent.health = 95
    assert not world.update_agent(agent)
    assert agent.health == 95
    assert messages(world) == ["Cannot EAT because map has no food"]


def test_eat_fail_full_health():
    world = load(out("eat_fail_maxHealth"))
    _, ok = run_first(world)
    assert not ok
    assert messages(world) == ["Cannot EAT because agent is at full health"]


@pytest.mark.parametrize("kind, limit", [("Dirt", PICKUP_DIRT), ("Food", PICKUP_FOOD)])
class TestLift:
    def amount(self, world, agent, kind):
        return getattr(world.tile(agent.pos), kind.lower())

    def test_all_full(self, kind, limit):
        world = load(out(f"lift{kind}_success_all{kind}Full"))
        agent, ok = run_first(world)
        assert ok
        assert self.amount(world, agent, kind) == 0
        assert getattr(agent, kind.lower()) == limit

    def test_partial(self, kind, limit):
        world = load(out(f"lift{kind}_success_partial{kind}"))
        agent = world.agents[0]
        before = self.amount(world, agent, kind)
        assert world.update_agent(agent)
        assert getattr(agent, kind.lower()) == limit
        assert self.amount(world, agent, kind) == before - limit

    def test_all_not_full(self, kind, limit):
        world = load(out(f"lift{kind}_success_all{kind}NotFull"))
        agent, ok = run_first(world)
        assert ok
        assert self.amount(world, agent, kind) == 0
        assert getattr(agent, kind.lower()) < limit

    def test_already_carrying_some(self, kind, limit):
        world = load(out(f"lift{kind}_success_has{kind}"))
        agent = world.agents[0]
        before = self.amount(world, agent, kind)
        setattr(agent, kind.lower(), 1)
        assert world.update_agent(agent)
        assert getattr(agent, kind.lower()) == limit
        assert self.amount(world, agent, kind) == before - (limit - 1)

    def test_fail_nothing_to_lift(self, kind, limit):
        world = load(out(f"lift{kind}_fail_no{kind}"))
        _, ok = run_first(world)
        assert not ok
        reason = "because there is no dirt" if kind == "Dirt" else "because no food left on map"
        assert messages(world) == [f"Cannot LIFT_{kind.upper()} {reason}"]


def test_lift_dirt_fail_full():
    world = load(out("liftDirt_fail_hasDirt"))
    agent = world.agents[0]
    agent.dirt = PICKUP_DIRT
    assert not world.update_agent(agent)
    assert messages(world) == ["Cannot LIFT_DIRT because agent already has maximum dirt"]


def test_lift_dirt_fail_carrying_food():
    world = load(out("liftDirt_fail_hasFood"))
    agent = world.agents[0]
    agent.food = PICKUP_FOOD
    assert not world.update_agent(agent)
    assert messages(world) == ["Cannot LIFT_DIRT because agent already has food"]


def test_lift_food_fail_full():
    world = load(out("liftFood_fail_hasFood"))
    agent = world.agents[0]
    agent.food = PICKUP_FOOD
    assert not world.update_agent(agent)
    assert messages(world) == ["Cannot LIFT_FOOD because agent already has maximum food"]


def test_lift_food_fail_carrying_dirt():
    # test_liftFood_fail_hasDirt.map holds a LIFT_DIRT tree, so (like the Java test) use this one.
    world = load(out("liftFood_fail_hasFood"))
    agent = world.agents[0]
    agent.dirt = PICKUP_DIRT
    assert not world.update_agent(agent)
    assert messages(world) == ["Cannot LIFT_FOOD because agent already has dirt"]


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("case", ["4free", "3free", "2free", "leftFree", "rightFree", "downFree", "upFree"])
def test_reproduce_success(case, seed):
    world = load(out(f"reproduce_success_{case}"), seed=seed)
    agent = world.agents[0]
    count, health = len(world.agents), agent.health
    assert world.update_agent(agent)
    assert len(world.agents) == count + 1
    assert agent.health == health // 2
    child = world.agents[-1]
    assert abs(child.x - agent.x) + abs(child.y - agent.y) == 1
    assert world.agent_at(child.pos) is child


@pytest.mark.parametrize("case", ["occupied", "heights", "boundaryTopLeftOccupied",
                                  "boundaryBottomRightOccupied"])
def test_reproduce_fail_no_room(case):
    world = load(out(f"reproduce_fail_{case}"))
    agent = world.agents[0]
    count, health = len(world.agents), agent.health
    assert not world.update_agent(agent)
    assert len(world.agents) == count
    assert agent.health == health
    assert messages(world) == ["Cannot REPRODUCE no extra locations"]


def test_reproduce_fail_health():
    world = load(out("reproduce_fail_health"))
    agent = world.agents[0]
    agent.health = 1
    assert not world.update_agent(agent)
    assert messages(world) == ["Cannot REPRODUCE not enough health"]


def test_reproduce_fail_team_full():
    world = load(out("reproduce_fail_teamSize"))
    _, ok = run_first(world)
    assert not ok
    assert messages(world) == ["Cannot REPRODUCE team full"]


@pytest.mark.parametrize("name", [a.value for a in Activity if a not in (
    Activity.CHANGE_TREE, Activity.SET_PRIMARY, Activity.SET_SECONDARY)])
def test_action_names(name):
    from waragents import parse_tree
    tree = parse_tree(f"t (OUTPUT {name})")
    assert str(tree.root.action) == name
