"""Position arguments used by inputs and actions, e.g. `HAS_FOOD LEFT` or `SET_PRIMARY CURRENT`.

Ported from model.position. A position resolves to an XY, or to None when it doesn't
exist (off the map, or a memory slot that hasn't been set).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from .world import DOWN, LEFT, RIGHT, UP, XY, Agent, DecisionError, World


class Position(ABC):
    name: ClassVar[str]

    @abstractmethod
    def resolve(self, agent: Agent, world: World) -> XY | None: ...

    def require(self, agent: Agent, world: World, context: str) -> XY:
        """Resolve, raising DecisionError (so the agent is CONFUSED) if there's no position."""
        pos = self.resolve(agent, world)
        if pos is None:
            raise DecisionError(f"{context}: {self.source()} is not a valid position")
        return pos

    def source(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class _Adjacent(Position):
    offset: ClassVar[tuple[int, int]]

    def resolve(self, agent: Agent, world: World) -> XY | None:
        pos = agent.pos.offset(*self.offset)
        return pos if world.in_bounds(pos) else None


class Left(_Adjacent):
    name = "LEFT"
    offset = LEFT


class Right(_Adjacent):
    name = "RIGHT"
    offset = RIGHT


class Up(_Adjacent):
    name = "UP"
    offset = UP


class Down(_Adjacent):
    name = "DOWN"
    offset = DOWN


class Current(Position):
    name = "CURRENT"

    def resolve(self, agent: Agent, world: World) -> XY | None:
        return agent.pos


class Previous(Position):
    name = "PREVIOUS"

    def resolve(self, agent: Agent, world: World) -> XY | None:
        return agent.previous_pos


class Primary(Position):
    name = "PRIMARY"

    def resolve(self, agent: Agent, world: World) -> XY | None:
        return agent.primary


class Secondary(Position):
    name = "SECONDARY"

    def resolve(self, agent: Agent, world: World) -> XY | None:
        return agent.secondary


@dataclass(frozen=True)
class XYValue(Position):
    name: ClassVar[str] = "XY_VALUE"
    x: int
    y: int

    def resolve(self, agent: Agent, world: World) -> XY | None:
        pos = XY(self.x, self.y)
        return pos if world.in_bounds(pos) else None

    def source(self) -> str:
        return f"{self.name} {self.x} {self.y}"


SIMPLE_POSITIONS: dict[str, type[Position]] = {
    cls.name: cls for cls in (Left, Right, Up, Down, Current, Previous, Primary, Secondary)
}
