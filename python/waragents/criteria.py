"""Win conditions that end a game. Ported from model.criteria.

The game ends as soon as any criterion is met. A criterion can also raise GameOver to end the
game as a loss (for example, the player being annihilated). winners() says which teams won, so the
game's result can record it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

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

    def winners(self, world: World) -> list[Player]:
        """The teams that won when this criterion was met. By default, every team still in."""
        return [p for p in world.players if p.agents]


class _TeamCriterion(Criterion):
    """A criterion one team meets, so that team is the winner."""

    player: Player

    def winners(self, world: World) -> list[Player]:
        return [self.player]


class _HistoryCounter:
    """Adds up something from the team's agent histories, reading each snapshot only once."""

    def __init__(self, count):
        self.count = count  # count(before, after) for each pair of snapshots
        self.total = 0
        self.seen: dict[int, int] = {}

    def update(self, player: Player) -> int:
        for agent in player.all_agents:
            start = self.seen.get(id(agent), 0)
            history = agent.history
            for n in range(max(start, 1), len(history)):
                self.total += self.count(history[n - 1], history[n])
            self.seen[id(agent)] = len(history)
        return self.total


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
class Annihilate(_TeamCriterion):
    """The player wins when every other player has no agents, and loses if it has none.

    With three or more teams, losing your agents knocks you out but the game goes on until one
    team is left.
    """

    player: Player

    def is_finished(self, world: World) -> bool:
        if not self.player.agents:
            if sum(1 for p in world.players if p.agents) > 1:
                return False
            raise GameOver(f"Game over: {self.player.name} has no agents left")
        return all(not p.agents for p in world.players if p is not self.player)

    def source(self) -> str:
        return f"ANNIHILATE {self.player.name}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} annihilated every other team"


@dataclass
class CollectFood(_TeamCriterion):
    """The player's agents have picked up at least this much food in total."""

    player: Player
    total: int
    _counter: _HistoryCounter = field(
        default_factory=lambda: _HistoryCounter(lambda before, after: max(0, after.food - before.food)),
        init=False, repr=False, compare=False)

    def collected(self) -> int:
        return self._counter.update(self.player)

    def is_finished(self, world: World) -> bool:
        return self.collected() >= self.total

    def source(self) -> str:
        return f"COLLECT_FOOD {self.player.name} {self.total}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} collected {self.total} food"


@dataclass
class EatFood(_TeamCriterion):
    """The player's agents have eaten at least this much food in total (health gained by EAT)."""

    player: Player
    amount: int
    _counter: _HistoryCounter = field(
        default_factory=lambda: _HistoryCounter(
            lambda before, after: max(0, after.health - before.health) if after.action == "EAT" else 0),
        init=False, repr=False, compare=False)

    def eaten(self) -> int:
        return self._counter.update(self.player)

    def is_finished(self, world: World) -> bool:
        return self.eaten() >= self.amount

    def source(self) -> str:
        return f"EAT_FOOD {self.player.name} {self.amount}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} ate {self.amount} food"


@dataclass
class TeamSize(_TeamCriterion):
    """The player has at least this many agents alive at once."""

    player: Player
    size: int

    def is_finished(self, world: World) -> bool:
        return len(self.player.agents) >= self.size

    def source(self) -> str:
        return f"TEAM_SIZE {self.player.name} {self.size}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} has {self.size} agents"


@dataclass
class LevelUp(_TeamCriterion):
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
class TravelTo(_TeamCriterion):
    player: Player
    position: XY

    def is_finished(self, world: World) -> bool:
        return any(a.pos == self.position for a in self.player.agents)

    def source(self) -> str:
        return f"TRAVEL_TO {self.player.name} {self.position.x} {self.position.y}"

    def describe_win(self, world: World) -> str:
        return f"{self.player.name} reached {self.position}"


@dataclass
class PerformAction(_TeamCriterion):
    player: Player
    activity: Activity
    times: int
    _counter: _HistoryCounter | None = field(default=None, init=False, repr=False, compare=False)

    def count(self) -> int:
        if self._counter is None:
            name = self.activity.value
            self._counter = _HistoryCounter(lambda before, after: int(after.action == name))
        return self._counter.update(self.player)

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

    def winners(self, world: World) -> list[Player]:
        return [self.winner.player]
