"""Core simulation state: the map (World), its tiles, players, agents and plants.

Ported from the Java classes model.Map, Tile, Agent, Player, Plant, Thing and XY.
Coordinates follow the Java version: x grows to the right and y grows "up",
so UP is (x, y + 1) and DOWN is (x, y - 1).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .actions import Action
    from .criteria import Criterion
    from .tree import Tree

MIN_DIRT = 0
MAX_DIRT = 15
MIN_FOOD = 0
MAX_FOOD = 100

PICKUP_FOOD = 10
PICKUP_DIRT = 2
LEVEL_PROG = 2
MOVE_HEALTH = 1

MODES = ("CLICK", "CONST", "FIXED")


class DecisionError(Exception):
    """Raised while evaluating a tree input that can't be answered.

    The agent becomes CONFUSED for the turn, as in the Java version.
    """


@dataclass(frozen=True)
class XY:
    x: int
    y: int

    def offset(self, dx: int, dy: int) -> XY:
        return XY(self.x + dx, self.y + dy)

    def __str__(self) -> str:
        return f"x={self.x} y={self.y}"


# Offsets for the four adjacent tiles, in the order the Java code checks them.
LEFT = (-1, 0)
RIGHT = (1, 0)
DOWN = (0, -1)
UP = (0, 1)
ADJACENT = (LEFT, RIGHT, DOWN, UP)


class Tile:
    def __init__(self, dirt: int = 0, food: int = 0):
        self._dirt = 0
        self._food = 0
        self.dirt = dirt
        self.food = food
        self.agent: Agent | None = None
        self.plant: Plant | None = None

    @property
    def dirt(self) -> int:
        return self._dirt

    @dirt.setter
    def dirt(self, value: int) -> None:
        self._dirt = max(MIN_DIRT, min(MAX_DIRT, value))

    @property
    def food(self) -> int:
        return self._food

    @food.setter
    def food(self, value: int) -> None:
        self._food = max(MIN_FOOD, min(MAX_FOOD, value))

    def add_food(self, amount: int) -> None:
        self.food = self.food + amount

    @property
    def occupied(self) -> bool:
        return self.agent is not None


class Plant:
    def __init__(self, id: str, pos: XY, rate: int):
        self.id = id
        self.pos = pos
        self.rate = rate

    def update(self, world: World) -> None:
        """Put half the rate on this tile and an eighth on each adjacent tile."""
        world.tile(self.pos).add_food(self.rate // 2)
        spill = self.rate // 8
        for pos in world.adjacent(self.pos):
            world.tile(pos).add_food(spill)


@dataclass(frozen=True)
class AgentSnapshot:
    """An agent's state after one of its turns (the Java AgentHistory)."""

    time: int
    action: str | None
    health: int
    exp: int
    dirt: int
    food: int
    tree: str


class Agent:
    def __init__(self, id: str, pos: XY, player: Player, speed: int, max_health: int,
                 power: int, tree: Tree, birth: int):
        self.id = id
        self.pos = pos
        self.player = player
        self.speed = speed
        self.max_health = max_health
        self._health = max_health
        self.power = power
        self.exp = 0
        self.level = 1
        self.dirt = 0
        self.food = 0
        self.tree = tree
        self.birth = birth
        self.death: int | None = None
        self.action: Action | None = None
        self.action_history: list[Action] = []
        self.visited: list[XY] = [pos]
        self.primary: XY | None = None
        self.secondary: XY | None = None
        # The tree and node ids this agent used for its last decision.
        self.last_path_tree: str | None = None
        self.last_path: list[int] = []
        self.history: list[AgentSnapshot] = [self.snapshot(birth)]

    @property
    def x(self) -> int:
        return self.pos.x

    @property
    def y(self) -> int:
        return self.pos.y

    @property
    def health(self) -> int:
        return self._health

    @health.setter
    def health(self, value: int) -> None:
        self._health = min(value, self.max_health)

    @property
    def alive(self) -> bool:
        return self.death is None

    @property
    def previous_pos(self) -> XY | None:
        return self.visited[-2] if len(self.visited) >= 2 else None

    @property
    def previous_action(self) -> Action | None:
        return self.action_history[-1] if self.action_history else None

    def set_action(self, action: Action) -> None:
        self.action = action
        self.action_history.append(action)

    def gain_exp(self, amount: int) -> None:
        self.exp += amount
        if self.exp > LEVEL_PROG ** self.level:
            self.level += 1

    def move_to(self, pos: XY) -> None:
        self.pos = pos
        self.visited.append(pos)

    def snapshot(self, time: int) -> AgentSnapshot:
        return AgentSnapshot(
            time=time,
            action=self.action.activity.value if self.action else None,
            health=self.health,
            exp=self.exp,
            dirt=self.dirt,
            food=self.food,
            tree=self.tree.name,
        )


class Player:
    def __init__(self, name: str, agent_health: int, agent_speed: int, agent_power: int,
                 trees: list[Tree], max_agents: int):
        self.name = name
        self.agent_health = agent_health
        self.agent_speed = agent_speed
        self.agent_power = agent_power
        self.trees = trees
        self.max_agents = max_agents
        self.agents: list[Agent] = []  # alive agents
        self.all_agents: list[Agent] = []  # every agent this player has had

    def add_agent(self, agent: Agent) -> None:
        self.agents.append(agent)
        self.all_agents.append(agent)

    @property
    def has_space(self) -> bool:
        return len(self.agents) < self.max_agents

    def tree(self, name: str) -> Tree | None:
        return next((t for t in self.trees if t.name == name), None)


@dataclass(frozen=True)
class Event:
    time: int
    kind: str  # "fail", "confused", "birth", "death" or "end"
    message: str
    agent: str | None = None


class World:
    """The whole game state. The Java equivalent is model.Map."""

    def __init__(self, width: int, height: int, tiles: list[list[Tile]], players: list[Player],
                 plants: list[Plant], criteria: list[Criterion], mode: str = "CLICK",
                 seed: int | None = None):
        self.width = width
        self.height = height
        self.tiles = tiles  # indexed tiles[x][y]
        self.players = players
        self.plants = plants
        self.criteria = criteria
        self.mode = mode
        self.seed = seed
        self.rng = random.Random(seed)
        self.time = 0
        self.events: list[Event] = []
        self.finished = False
        self.outcome: str | None = None

        for plant in plants:
            self.tile(plant.pos).plant = plant
        # Turn order. The Java version keeps this list separate from the players' lists.
        self.agents: list[Agent] = []
        for player in players:
            for agent in player.agents:
                self.tile(agent.pos).agent = agent
                self.agents.append(agent)
        self._agent_count = sum(len(p.all_agents) for p in players)

    # ---- geometry -------------------------------------------------------------

    def in_bounds(self, pos: XY) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def tile(self, pos: XY) -> Tile:
        return self.tiles[pos.x][pos.y]

    def adjacent(self, pos: XY) -> list[XY]:
        """In-bounds neighbours of pos: left, right, down, up."""
        return [p for p in (pos.offset(dx, dy) for dx, dy in ADJACENT) if self.in_bounds(p)]

    def agent_at(self, pos: XY | None) -> Agent | None:
        if pos is None or not self.in_bounds(pos):
            return None
        return self.tile(pos).agent

    # ---- lifecycle ------------------------------------------------------------

    def log(self, kind: str, message: str, agent: Agent | None = None) -> None:
        self.events.append(Event(self.time, kind, message, agent.id if agent else None))

    def spawn_agent(self, player: Player, pos: XY, speed: int, max_health: int, power: int,
                    tree: Tree) -> Agent:
        agent = Agent(f"Agent{self._agent_count}", pos, player, speed, max_health, power, tree,
                      self.time)
        self._agent_count += 1
        player.add_agent(agent)
        self.agents.append(agent)
        self.tile(pos).agent = agent
        self.log("birth", f"{agent.id} ({player.name}) was born at {pos}", agent)
        return agent

    def move_agent(self, agent: Agent, pos: XY) -> None:
        self.tile(agent.pos).agent = None
        self.tile(pos).agent = agent
        agent.move_to(pos)

    def kill(self, agent: Agent) -> None:
        """Remove an agent and drop a quarter of its max health as food."""
        agent.death = self.time
        tile = self.tile(agent.pos)
        tile.add_food(int(agent.max_health * 0.25))
        tile.agent = None
        agent.player.agents.remove(agent)
        self.agents.remove(agent)
        self.log("death", f"{agent.id} ({agent.player.name}) died at {agent.pos}", agent)

    def update_agent(self, agent: Agent) -> bool:
        """Run one agent's turn. Returns whether its action succeeded (Agent.update in Java)."""
        from .tree import decide

        if agent.health < 1:
            self.kill(agent)
            return False
        action, path = decide(agent.tree.root, agent, self)
        agent.last_path_tree = agent.tree.name
        agent.last_path = path
        agent.set_action(action)
        result = action.perform(agent, self)
        agent.history.append(agent.snapshot(self.time))
        return result

    def step(self) -> list[Event]:
        """Advance one turn and return the events it produced."""
        if self.finished:
            return []
        start = len(self.events)
        self.time += 1

        # One bubble-sort pass on speed per turn, so faster agents drift to the front.
        order = self.agents
        for i in range(len(order) - 1):
            if order[i].speed < order[i + 1].speed:
                order[i], order[i + 1] = order[i + 1], order[i]
        # Agents born this turn start acting next turn. Agents killed this turn are skipped.
        for agent in list(order):
            if agent.alive:
                self.update_agent(agent)

        for plant in self.plants:
            plant.update(self)

        self._check_finished()
        return self.events[start:]

    def _check_finished(self) -> None:
        from .criteria import GameOver

        for criterion in self.criteria:
            try:
                done = criterion.is_finished(self)
            except GameOver as e:
                self._finish(str(e))
                return
            if done:
                self._finish(criterion.describe_win(self))
                return
        if not self.agents:
            self._finish("Game over: no agents left")

    def _finish(self, outcome: str) -> None:
        self.finished = True
        self.outcome = outcome
        self.log("end", outcome)
