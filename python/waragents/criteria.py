"""Win conditions that end a game. Ported from model.criteria.

The game ends as soon as any criterion is met. A criterion can also raise GameOver to end the
game as a loss (for example, the player being annihilated).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .actions import Activity
from .world import XY, Agent, Plant, Player, World


class GameOver(Exception):
    pass


class Criterion(ABC):
    @abstractmethod
    def is_finished(self, world: World) -> bool: ...

    @abstractmethod
    def source(self) -> str: ...

    def describe_win(self, world: World) -> str:
        return f"Criteria met: {self.source()}"


@dataclass
class SurviveTurns(Criterion):
    turns: int

    def is_finished(self, world: World) -> bool:
        return world.time >= self.turns

    def source(self) -> str:
        return f"SURVIVE_TURNS {self.turns}"

    def describe_win(self, world: World) -> str:
        return f"Survived {self.turns} turns"


@dataclass
class Annihilate(Criterion):
    """The player wins when every other player has no agents, and loses if it has none."""

    player: Player

    def is_finished(self, world: World) -> bool:
        if not self.player.agents:
            raise GameOver(f"Game over: {self.player.name} has no agents left")
        return all(not p.agents for p in world.players if p is not self.player)

    def source(self) -> str:
        return f"ANNIHILATE {self.player.name}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} annihilated every other team"


@dataclass
class CollectFood(Criterion):
    """The player's agents have picked up at least this much food in total."""

    player: Player
    total: int

    def collected(self) -> int:
        total = 0
        for agent in self.player.all_agents:
            for before, after in zip(agent.history, agent.history[1:]):
                total += max(0, after.food - before.food)
        return total

    def is_finished(self, world: World) -> bool:
        return self.collected() >= self.total

    def source(self) -> str:
        return f"COLLECT_FOOD {self.player.name} {self.total}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} collected {self.total} food"


@dataclass
class LevelUp(Criterion):
    player: Player
    exp: int

    def is_finished(self, world: World) -> bool:
        return any(a.exp >= self.exp for a in self.player.agents)

    def source(self) -> str:
        return f"LEVEL_UP {self.player.name} {self.exp}"


@dataclass
class MapDirt(Criterion):
    """The tile at position has exactly this much dirt."""

    dirt: int
    position: XY

    def is_finished(self, world: World) -> bool:
        return world.tile(self.position).dirt == self.dirt

    def source(self) -> str:
        return f"MAP_DIRT {self.dirt} {self.position.x} {self.position.y}"


@dataclass
class TravelTo(Criterion):
    player: Player
    position: XY

    def is_finished(self, world: World) -> bool:
        return any(a.pos == self.position for a in self.player.agents)

    def source(self) -> str:
        return f"TRAVEL_TO {self.player.name} {self.position.x} {self.position.y}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} reached {self.position}"


@dataclass
class PerformAction(Criterion):
    player: Player
    activity: Activity
    times: int

    def count(self) -> int:
        return sum(1 for a in self.player.all_agents for s in a.history
                   if s.action == self.activity.value)

    def is_finished(self, world: World) -> bool:
        return self.count() >= self.times

    def source(self) -> str:
        return f"PERFORM_ACTION {self.player.name} {self.activity.value} {self.times}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} performed {self.activity.value} {self.times} times"


@dataclass
class FindThing(Criterion):
    """First agent next to the thing (an agent or plant) wins. Ties go to the fastest, then oldest."""

    thing: Agent | Plant
    winner: Agent | None = None

    def is_finished(self, world: World) -> bool:
        finders = [a for p in world.adjacent(self.thing.pos)
                   if (a := world.agent_at(p)) is not None and a is not self.thing]
        if not finders:
            return False
        self.winner = min(finders, key=lambda a: (-a.speed, a.birth))
        return True

    def source(self) -> str:
        return f"FIND_THING {self.thing.id}"

    def describe_win(self, world: World) -> str:
        return f"{self.winner.player.name} found {self.thing.id}"
