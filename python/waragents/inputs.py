"""Inputs evaluated at the decision nodes of a tree. Ported from model.input.

There are three kinds, matching the three kinds of decision node:
  boolean  - BOOLEAN nodes branch on true/false
  numeric  - NUMERIC nodes compare two numeric inputs (<, =, >)
  position - POSITION nodes branch on the direction to the returned position

Each input declares the arguments it takes in the map file with `args`:
  "position" (a Position such as LEFT or XY_VALUE 3 4), "int", "activity" or "name".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import Any, ClassVar

from .actions import Activity
from .positions import Position
from .world import ADJACENT, MAX_DIRT, MAX_FOOD, XY, Agent, DecisionError, World

INPUTS: dict[str, type[Input]] = {}


def register(cls: type[Input]) -> type[Input]:
    INPUTS[cls.name] = cls
    return cls


class Input(ABC):
    name: ClassVar[str]
    kind: ClassVar[str]
    args: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def evaluate(self, agent: Agent, world: World) -> Any: ...

    def source(self) -> str:
        parts = [self.name]
        for f in fields(self) if hasattr(self, "__dataclass_fields__") else ():
            value = getattr(self, f.name)
            parts.append(value.source() if isinstance(value, Position)
                         else value.value if isinstance(value, Activity) else str(value))
        return " ".join(parts)

    def __str__(self) -> str:
        return self.source()


class BooleanInput(Input):
    kind = "boolean"

    @abstractmethod
    def evaluate(self, agent: Agent, world: World) -> bool: ...


class NumericInput(Input):
    kind = "numeric"

    @abstractmethod
    def evaluate(self, agent: Agent, world: World) -> int: ...


class PositionInput(Input):
    kind = "position"

    @abstractmethod
    def evaluate(self, agent: Agent, world: World) -> XY: ...


def _neighbours(agent: Agent, world: World) -> list[XY]:
    return world.adjacent(agent.pos)


def _is_enemy(agent: Agent, other: Agent | None) -> bool:
    return other is not None and other.player is not agent.player


def _is_ally(agent: Agent, other: Agent | None) -> bool:
    return other is not None and other.player is agent.player


# ---- boolean inputs --------------------------------------------------------------


@register
class LegalMove(BooleanInput):
    """Is any adjacent tile on the map and unoccupied? (Height isn't checked.)"""

    name = "LEGAL_MOVE"

    def evaluate(self, agent: Agent, world: World) -> bool:
        return any(not world.tile(p).occupied for p in _neighbours(agent, world))


@register
class FoodAdjacent(BooleanInput):
    name = "FOOD_ADJACENT"

    def evaluate(self, agent: Agent, world: World) -> bool:
        return any(world.tile(p).food > 0 for p in _neighbours(agent, world))


@register
class EnemyAdjacent(BooleanInput):
    name = "ENEMY_ADJACENT"

    def evaluate(self, agent: Agent, world: World) -> bool:
        return any(_is_enemy(agent, world.agent_at(p)) for p in _neighbours(agent, world))


@register
class AllyAdjacent(BooleanInput):
    name = "ALLY_ADJACENT"

    def evaluate(self, agent: Agent, world: World) -> bool:
        return any(_is_ally(agent, world.agent_at(p)) for p in _neighbours(agent, world))


@register
class PlantAdjacent(BooleanInput):
    """Is there a plant on this tile or an adjacent one?"""

    name = "PLANT_ADJACENT"

    def evaluate(self, agent: Agent, world: World) -> bool:
        tiles = [agent.pos, *_neighbours(agent, world)]
        return any(world.tile(p).plant is not None for p in tiles)


@register
class PlantCurrent(BooleanInput):
    name = "PLANT_CURRENT"

    def evaluate(self, agent: Agent, world: World) -> bool:
        return world.tile(agent.pos).plant is not None


@register
class ReproduceLegal(BooleanInput):
    """Enough health, room in the team and a free adjacent tile? (Height isn't checked.)"""

    name = "REPRODUCE_LEGAL"

    def evaluate(self, agent: Agent, world: World) -> bool:
        return (agent.health >= 2 and agent.player.has_space
                and any(not world.tile(p).occupied for p in _neighbours(agent, world)))


@register
@dataclass(frozen=True)
class HasFood(BooleanInput):
    name: ClassVar[str] = "HAS_FOOD"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        return world.tile(self.position.require(agent, world, self.name)).food > 0


@register
@dataclass(frozen=True)
class HasPlant(BooleanInput):
    name: ClassVar[str] = "HAS_PLANT"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        return world.tile(self.position.require(agent, world, self.name)).plant is not None


@register
@dataclass(frozen=True)
class HasEnemy(BooleanInput):
    name: ClassVar[str] = "HAS_ENEMY"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        pos = self.position.require(agent, world, self.name)
        return _is_enemy(agent, world.agent_at(pos))


@register
@dataclass(frozen=True)
class HasAlly(BooleanInput):
    name: ClassVar[str] = "HAS_ALLY"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        pos = self.position.require(agent, world, self.name)
        return _is_ally(agent, world.agent_at(pos))


@register
@dataclass(frozen=True)
class Occupied(BooleanInput):
    name: ClassVar[str] = "OCCUPIED"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        return world.tile(self.position.require(agent, world, self.name)).occupied


@register
@dataclass(frozen=True)
class InBounds(BooleanInput):
    name: ClassVar[str] = "IN_BOUNDS"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        pos = self.position.resolve(agent, world)
        return pos is not None and world.in_bounds(pos)


@register
@dataclass(frozen=True)
class ValidPosition(BooleanInput):
    """True if the position exists. Use it to guard PRIMARY, PREVIOUS, LEFT and so on."""

    name: ClassVar[str] = "VALID_POSITION"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        return self.position.resolve(agent, world) is not None


@register
@dataclass(frozen=True)
class PositionMatch(BooleanInput):
    name: ClassVar[str] = "POSITION_MATCH"
    args = ("position", "position")
    position1: Position
    position2: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        return (self.position1.require(agent, world, self.name)
                == self.position2.require(agent, world, self.name))


@register
@dataclass(frozen=True)
class AllyAction(BooleanInput):
    """Did the ally at the position last perform this action?"""

    name: ClassVar[str] = "ALLY_ACTION"
    args = ("activity", "position")
    activity: Activity
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        other = world.agent_at(self.position.require(agent, world, self.name))
        return (_is_ally(agent, other) and other.action is not None
                and other.action.activity is self.activity)


@register
@dataclass(frozen=True)
class EnemyAction(BooleanInput):
    """Did the enemy at the position last perform this action?"""

    name: ClassVar[str] = "ENEMY_ACTION"
    args = ("activity", "position")
    activity: Activity
    position: Position

    def evaluate(self, agent: Agent, world: World) -> bool:
        other = world.agent_at(self.position.require(agent, world, self.name))
        return (_is_enemy(agent, other) and other.action is not None
                and other.action.activity is self.activity)


@register
@dataclass(frozen=True)
class CurrentTree(BooleanInput):
    name: ClassVar[str] = "CURRENT_TREE"
    args = ("name",)
    tree: str

    def evaluate(self, agent: Agent, world: World) -> bool:
        return agent.tree.name == self.tree


@register
@dataclass(frozen=True)
class PreviousAction(BooleanInput):
    """Was this agent's previous action this one?"""

    name: ClassVar[str] = "SELF_PREVIOUS_ACTION"
    args = ("activity",)
    activity: Activity

    def evaluate(self, agent: Agent, world: World) -> bool:
        previous = agent.previous_action
        return previous is not None and previous.activity is self.activity


# ---- numeric inputs --------------------------------------------------------------


@register
@dataclass(frozen=True)
class Value(NumericInput):
    name: ClassVar[str] = "VALUE"
    args = ("int",)
    value: int

    def evaluate(self, agent: Agent, world: World) -> int:
        return self.value


@register
class RandomValue(NumericInput):
    """A random number from 0 to 99, drawn from the world's seeded generator."""

    name = "RANDOM"

    def evaluate(self, agent: Agent, world: World) -> int:
        return world.rng.randrange(100)


@register
class Time(NumericInput):
    name = "TIME"

    def evaluate(self, agent: Agent, world: World) -> int:
        return world.time


@register
@dataclass(frozen=True)
class FoodValue(NumericInput):
    name: ClassVar[str] = "FOOD_VALUE"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> int:
        return world.tile(self.position.require(agent, world, self.name)).food


@register
@dataclass(frozen=True)
class DirtValue(NumericInput):
    name: ClassVar[str] = "DIRT_VALUE"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> int:
        return world.tile(self.position.require(agent, world, self.name)).dirt


@register
@dataclass(frozen=True)
class GetX(NumericInput):
    name: ClassVar[str] = "GET_X"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> int:
        return self.position.require(agent, world, self.name).x


@register
@dataclass(frozen=True)
class GetY(NumericInput):
    name: ClassVar[str] = "GET_Y"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> int:
        return self.position.require(agent, world, self.name).y


@register
@dataclass(frozen=True)
class PlantRate(NumericInput):
    name: ClassVar[str] = "PLANT_RATE"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> int:
        plant = world.tile(self.position.require(agent, world, self.name)).plant
        if plant is None:
            raise DecisionError(f"{self.name}: no plant at {self.position.source()}")
        return plant.rate


@register
class MapWidth(NumericInput):
    name = "MAP_WIDTH"

    def evaluate(self, agent: Agent, world: World) -> int:
        return world.width


@register
class MapHeight(NumericInput):
    name = "MAP_HEIGHT"

    def evaluate(self, agent: Agent, world: World) -> int:
        return world.height


@register
class MaxDirt(NumericInput):
    name = "MAX_DIRT"

    def evaluate(self, agent: Agent, world: World) -> int:
        return MAX_DIRT


@register
class MaxFood(NumericInput):
    name = "MAX_FOOD"

    def evaluate(self, agent: Agent, world: World) -> int:
        return MAX_FOOD


@register
class TeamSize(NumericInput):
    name = "TEAM_SIZE"

    def evaluate(self, agent: Agent, world: World) -> int:
        return len(agent.player.agents)


@register
class MaxTeamSize(NumericInput):
    name = "MAX_TEAM_SIZE"

    def evaluate(self, agent: Agent, world: World) -> int:
        return agent.player.max_agents


@register
@dataclass(frozen=True)
class NumberTrees(NumericInput):
    """How many agents on this team are currently using the named tree."""

    name: ClassVar[str] = "NUMBER_TREES"
    args = ("name",)
    tree: str

    def evaluate(self, agent: Agent, world: World) -> int:
        return sum(1 for a in agent.player.agents if a.tree.name == self.tree)


class _SelfStat(NumericInput):
    """One of the agent's own stats. Listed in the Java Option enum but never implemented there."""

    def evaluate(self, agent: Agent, world: World) -> int:
        return self.stat(agent, world)


def _self_stat(input_name: str, doc: str, stat) -> type[Input]:
    cls = type(input_name.title().replace("_", ""), (_SelfStat,),
               {"name": input_name, "__doc__": doc, "stat": staticmethod(stat)})
    return register(cls)


_self_stat("SELF_HEALTH", "The agent's current health.", lambda a, w: a.health)
_self_stat("SELF_MAXHEALTH", "The agent's maximum health.", lambda a, w: a.max_health)
_self_stat("SELF_POWER", "The agent's attack power.", lambda a, w: a.power)
_self_stat("SELF_SPEED", "The agent's speed.", lambda a, w: a.speed)
_self_stat("SELF_EXP", "The agent's experience points.", lambda a, w: a.exp)
_self_stat("SELF_DIRT", "How much dirt the agent is carrying.", lambda a, w: a.dirt)
_self_stat("SELF_FOOD", "How much food the agent is carrying.", lambda a, w: a.food)
_self_stat("SELF_AGE", "Turns since the agent was born.", lambda a, w: w.time - a.birth)
_self_stat("SELF_X", "The agent's x position.", lambda a, w: a.x)
_self_stat("SELF_Y", "The agent's y position.", lambda a, w: a.y)


# ---- position inputs -------------------------------------------------------------


def _step_towards(start: XY, target: XY) -> XY:
    """One step from start towards target, moving along the longer axis first."""
    if start == target:
        return start
    dx = start.x - target.x
    dy = start.y - target.y
    if abs(dx) >= abs(dy):
        return start.offset(-1 if dx > 0 else 1, 0)
    return start.offset(0, -1 if dy > 0 else 1)


@register
@dataclass(frozen=True)
class DirectionTo(PositionInput):
    name: ClassVar[str] = "DIRECTION_TO"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> XY:
        return _step_towards(agent.pos, self.position.require(agent, world, self.name))


@register
@dataclass(frozen=True)
class AStar(PositionInput):
    """Meant to be the next step of an A* path. For now it's the same greedy step as DIRECTION_TO."""

    name: ClassVar[str] = "A_STAR"
    args = ("position",)
    position: Position

    def evaluate(self, agent: Agent, world: World) -> XY:
        return _step_towards(agent.pos, self.position.require(agent, world, self.name))


class _AdjacentAgentPos(PositionInput):
    """A random adjacent tile holding a matching agent, or the agent's own tile if none."""

    def matches(self, agent: Agent, other: Agent | None) -> bool:
        raise NotImplementedError

    def evaluate(self, agent: Agent, world: World) -> XY:
        options = [agent.pos.offset(dx, dy) for dx, dy in ADJACENT]
        world.rng.shuffle(options)
        for pos in options:
            if self.matches(agent, world.agent_at(pos)):
                return pos
        return agent.pos


@register
class EnemyAdjacentPos(_AdjacentAgentPos):
    name = "ENEMY_ADJACENT_POS"

    def matches(self, agent: Agent, other: Agent | None) -> bool:
        return _is_enemy(agent, other)


@register
class AllyAdjacentPos(_AdjacentAgentPos):
    name = "ALLY_ADJACENT_POS"

    def matches(self, agent: Agent, other: Agent | None) -> bool:
        return _is_ally(agent, other)
