"""Actions an agent can take: the leaves (OUTPUT nodes) of a decision tree.

Ported from model.output. perform() returns True if the action succeeded. A failed action
logs a "Cannot ..." event with the same wording as the Java version.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from .positions import Position
from .world import DOWN, LEFT, MOVE_HEALTH, PICKUP_DIRT, PICKUP_FOOD, RIGHT, UP, XY, Agent, World


class Activity(str, Enum):
    ATTACK_DOWN = "ATTACK_DOWN"
    ATTACK_LEFT = "ATTACK_LEFT"
    ATTACK_RIGHT = "ATTACK_RIGHT"
    ATTACK_UP = "ATTACK_UP"
    CHANGE_TREE = "CHANGE_TREE"
    DEFEND = "DEFEND"
    DROP_DIRT = "DROP_DIRT"
    DROP_FOOD = "DROP_FOOD"
    EAT = "EAT"
    LIFT_DIRT = "LIFT_DIRT"
    LIFT_FOOD = "LIFT_FOOD"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    MOVE_UP = "MOVE_UP"
    REPRODUCE = "REPRODUCE"
    SET_PRIMARY = "SET_PRIMARY"
    CLEAR_PRIMARY = "CLEAR_PRIMARY"
    SET_SECONDARY = "SET_SECONDARY"
    CLEAR_SECONDARY = "CLEAR_SECONDARY"
    CONFUSED = "CONFUSED"
    DEATH = "DEATH"


DIRECTIONS = {"LEFT": LEFT, "RIGHT": RIGHT, "UP": UP, "DOWN": DOWN}

CONFUSED_HARM = 10


class Action(ABC):
    activity: ClassVar[Activity]

    @abstractmethod
    def perform(self, agent: Agent, world: World) -> bool: ...

    def fail(self, agent: Agent, world: World, reason: str) -> bool:
        world.log("fail", f"Cannot {self.activity.value} {reason}", agent)
        return False

    def source(self) -> str:
        return self.activity.value

    def __str__(self) -> str:
        return self.activity.value


class _Directional(Action):
    """Base for the four MOVE_* and four ATTACK_* actions."""

    prefix: ClassVar[str]

    def __init__(self, direction: str):
        self.direction = direction
        self.offset = DIRECTIONS[direction]

    @property
    def activity(self) -> Activity:  # type: ignore[override]
        return Activity(f"{self.prefix}_{self.direction}")

    def target(self, agent: Agent) -> XY:
        return agent.pos.offset(*self.offset)


class Move(_Directional):
    prefix = "MOVE"

    def perform(self, agent: Agent, world: World) -> bool:
        target = self.target(agent)
        if not world.in_bounds(target):
            return self.fail(agent, world, "because of out of bounds")
        height_diff = abs(world.tile(agent.pos).dirt - world.tile(target).dirt)
        if height_diff >= 3:
            return self.fail(agent, world, "because of height difference")
        occupant = world.tile(target).agent
        if occupant is not None:
            return self.fail(agent, world, f"because of {occupant.id}")

        # Climbing (a height difference of 2) and carrying dirt or food each cost health.
        carrying = agent.dirt > 0 or agent.food > 0
        climbing = height_diff > 1
        cost = MOVE_HEALTH * (int(carrying) + int(climbing))
        if cost and agent.health <= cost:
            return self.fail(agent, world, "because move would kill")
        world.move_agent(agent, target)
        agent.health -= cost
        return True


# Attack power multiplier by (attacker height - defender height). Anything else can't attack.
HEIGHT_POWER = {
    3: lambda p: p * 4,
    2: lambda p: p * 3,
    1: lambda p: p * 2,
    0: lambda p: p,
    -1: lambda p: p // 2,
    -2: lambda p: p // 3,
}


class Attack(_Directional):
    prefix = "ATTACK"

    def perform(self, agent: Agent, world: World) -> bool:
        target = self.target(agent)
        if not world.in_bounds(target):
            return self.fail(agent, world, "because attack is out of bounds")
        defender = world.tile(target).agent
        if defender is None:
            return self.fail(agent, world, "because no agent to attack")
        if not attack(agent, defender, world):
            return self.fail(agent, world, "because attack failed")
        return True


def attack(attacker: Agent, defender: Agent, world: World) -> bool:
    power = attacker.power
    if defender.action is not None and defender.action.activity is Activity.DEFEND:
        power //= 2
    height_diff = world.tile(attacker.pos).dirt - world.tile(defender.pos).dirt
    if height_diff not in HEIGHT_POWER:
        return False
    defender.health = defender.health - HEIGHT_POWER[height_diff](power)
    if defender.health < 1:
        world.kill(defender)
    return True


@dataclass
class ChangeTree(Action):
    activity: ClassVar[Activity] = Activity.CHANGE_TREE
    tree: str

    def perform(self, agent: Agent, world: World) -> bool:
        tree = agent.player.tree(self.tree)
        if tree is None:
            return self.fail(agent, world, "because no tree with that name exists")
        agent.tree = tree
        return True

    def source(self) -> str:
        return f"{self.activity.value} {self.tree}"


@dataclass
class SetPrimary(Action):
    activity: ClassVar[Activity] = Activity.SET_PRIMARY
    position: Position

    def perform(self, agent: Agent, world: World) -> bool:
        agent.primary = self.position.resolve(agent, world)
        return True

    def source(self) -> str:
        return f"{self.activity.value} {self.position.source()}"


@dataclass
class SetSecondary(Action):
    activity: ClassVar[Activity] = Activity.SET_SECONDARY
    position: Position

    def perform(self, agent: Agent, world: World) -> bool:
        agent.secondary = self.position.resolve(agent, world)
        return True

    def source(self) -> str:
        return f"{self.activity.value} {self.position.source()}"


class ClearPrimary(Action):
    activity = Activity.CLEAR_PRIMARY

    def perform(self, agent: Agent, world: World) -> bool:
        agent.primary = None
        return True


class ClearSecondary(Action):
    activity = Activity.CLEAR_SECONDARY

    def perform(self, agent: Agent, world: World) -> bool:
        agent.secondary = None
        return True


class Confused(Action):
    """What an agent does when its tree can't be evaluated. It costs CONFUSED_HARM health."""

    activity = Activity.CONFUSED

    def perform(self, agent: Agent, world: World) -> bool:
        if agent.health <= CONFUSED_HARM:
            world.kill(agent)
        else:
            agent.health -= CONFUSED_HARM
        return True


class Death(Action):
    activity = Activity.DEATH

    def perform(self, agent: Agent, world: World) -> bool:
        world.kill(agent)
        return True


class Defend(Action):
    """Does nothing itself, but halves the power of attacks against this agent."""

    activity = Activity.DEFEND

    def perform(self, agent: Agent, world: World) -> bool:
        return True


class DropDirt(Action):
    activity = Activity.DROP_DIRT

    def perform(self, agent: Agent, world: World) -> bool:
        if agent.dirt <= 0:
            return self.fail(agent, world, "because agent has no dirt")
        world.tile(agent.pos).dirt += agent.dirt
        agent.dirt = 0
        return True


class DropFood(Action):
    activity = Activity.DROP_FOOD

    def perform(self, agent: Agent, world: World) -> bool:
        if agent.food <= 0:
            return self.fail(agent, world, "because agent has no food")
        world.tile(agent.pos).food += agent.food
        agent.food = 0
        return True


class Eat(Action):
    """Eat food from the ground (not carried food), one food per health point."""

    activity = Activity.EAT

    def perform(self, agent: Agent, world: World) -> bool:
        tile = world.tile(agent.pos)
        if agent.health == agent.max_health:
            return self.fail(agent, world, "because agent is at full health")
        if tile.food == 0:
            return self.fail(agent, world, "because map has no food")
        eaten = min(tile.food, agent.max_health - agent.health)
        tile.food -= eaten
        agent.health += eaten
        return True


class LiftDirt(Action):
    activity = Activity.LIFT_DIRT

    def perform(self, agent: Agent, world: World) -> bool:
        tile = world.tile(agent.pos)
        if agent.food != 0:
            return self.fail(agent, world, "because agent already has food")
        if tile.dirt <= 0:
            return self.fail(agent, world, "because there is no dirt")
        if agent.dirt >= PICKUP_DIRT:
            return self.fail(agent, world, "because agent already has maximum dirt")
        lifted = min(tile.dirt, PICKUP_DIRT - agent.dirt)
        tile.dirt -= lifted
        agent.dirt += lifted
        return True


class LiftFood(Action):
    activity = Activity.LIFT_FOOD

    def perform(self, agent: Agent, world: World) -> bool:
        tile = world.tile(agent.pos)
        if tile.food <= 0:
            return self.fail(agent, world, "because no food left on map")
        if agent.dirt != 0:
            return self.fail(agent, world, "because agent already has dirt")
        if agent.food >= PICKUP_FOOD:
            return self.fail(agent, world, "because agent already has maximum food")
        lifted = min(tile.food, PICKUP_FOOD - agent.food)
        tile.food -= lifted
        agent.food += lifted
        return True


class Reproduce(Action):
    """Split into two. The child's stats are 95-105% of the parent's, scaled by its health."""

    activity = Activity.REPRODUCE

    def perform(self, agent: Agent, world: World) -> bool:
        if agent.health < 2:
            return self.fail(agent, world, "not enough health")
        if not agent.player.has_space:
            return self.fail(agent, world, "team full")
        change = agent.health / agent.max_health
        max_health = _random_range(world, agent.max_health, change)
        speed = _random_range(world, agent.speed, change)
        power = _random_range(world, agent.power, change)
        pos = _find_birth_position(world, agent.pos)
        if pos is None:
            return self.fail(agent, world, "no extra locations")
        child = world.spawn_agent(agent.player, pos, speed, max_health, power, agent.tree)
        child.health = max_health // 2
        agent.health = agent.health // 2
        return True


def _random_range(world: World, value: int, scale: float) -> int:
    chance = (95 + world.rng.random() * scale * 10) / 100
    return int(value * chance)


def _find_birth_position(world: World, pos: XY) -> XY | None:
    """A random free adjacent tile within climbing height (2) of pos, or None."""
    options = [pos.offset(*d) for d in (UP, LEFT, RIGHT, DOWN)]
    world.rng.shuffle(options)
    height = world.tile(pos).dirt
    for option in options:
        if (world.in_bounds(option) and not world.tile(option).occupied
                and abs(world.tile(option).dirt - height) <= 2):
            return option
    return None


# Actions that take no arguments, keyed by name. The parser handles the others.
SIMPLE_ACTIONS: dict[str, type[Action]] = {
    cls.activity.value: cls
    for cls in (ClearPrimary, ClearSecondary, Confused, Death, Defend, DropDirt, DropFood, Eat,
                LiftDirt, LiftFood, Reproduce)
}
