"""Reads the `.map` game format. Ported from the Java readers package.

The layout is positional at the top and free-form after the plants:

    height=5
    width=5
    food=
    <height rows of width numbers>
    dirt=
    <height rows of width numbers>
    plants=1
    x=2,y=2,rate=10
    maxAgents=10
    name=red,speed=10,health=100,power=10,x=0,y=0
    tree=main (BOOLEAN LEGAL_MOVE (OUTPUT MOVE_LEFT) (OUTPUT DEFEND))
    criteria=1
    SURVIVE_TURNS 50
    mode=CLICK

Grid row n holds y = n. Trees are written as prefix expressions. As in the Java reader, the
brackets are only there for readability: the structure comes from each node's arity.

Unlike the Java reader, this one reports problems (unknown tokens, a boolean input on a
NUMERIC node, agents off the map) as MapFormatError instead of failing later.
"""

from __future__ import annotations

from collections import deque

from .actions import SIMPLE_ACTIONS, Action, Activity, Attack, ChangeTree, Move, SetPrimary, SetSecondary
from .criteria import (Annihilate, CollectFood, Criterion, FindThing, LevelUp, MapDirt,
                       PerformAction, SurviveTurns, TravelTo)
from .inputs import INPUTS, Input
from .positions import SIMPLE_POSITIONS, Position, XYValue
from .tree import NODE_SHAPES, Node, NodeKind, Tree
from .world import MODES, XY, Agent, Plant, Player, Tile, World


class MapFormatError(ValueError):
    def __init__(self, message: str, line: int | None = None):
        super().__init__(f"Line {line}: {message}" if line else message)
        self.line = line


def parse_map(text: str, seed: int | None = None) -> World:
    return _Parser(text).parse(seed)


def parse_tree(source: str) -> Tree:
    """Parse one tree, e.g. "main (OUTPUT DEFEND)" (the part after "tree=")."""
    return _TreeParser(source, line=None).parse()


class _Tokens:
    def __init__(self, tokens: list[str], line: int | None):
        self.queue = deque(tokens)
        self.line = line

    def error(self, message: str) -> MapFormatError:
        return MapFormatError(message, self.line)

    def take(self, what: str) -> str:
        if not self.queue:
            raise self.error(f"the tree ended early, while expecting {what}")
        return self.queue.popleft()

    def take_int(self, what: str) -> int:
        token = self.take(what)
        try:
            return int(token)
        except ValueError:
            raise self.error(f"expected a number for {what} but found '{token}'") from None


class _TreeParser:
    def __init__(self, source: str, line: int | None):
        tokens = source.replace("(", " ").replace(")", " ").split()
        self.tokens = _Tokens(tokens, line)
        self.next_id = 0

    def parse(self) -> Tree:
        name = self.tokens.take("a tree name")
        root = self.node(depth=0)
        if self.tokens.queue:
            leftover = " ".join(self.tokens.queue)
            raise self.tokens.error(f"tree '{name}' has extra tokens after it ends: {leftover}")
        return Tree(name, root)

    def node(self, depth: int) -> Node:
        token = self.tokens.take("a node (OUTPUT, BOOLEAN, NUMERIC or POSITION)")
        try:
            kind = NodeKind(token)
        except ValueError:
            if token not in Activity.__members__:
                raise self.tokens.error(
                    f"expected OUTPUT, BOOLEAN, NUMERIC or POSITION but found '{token}'") from None
            # A bare action such as "(DEFEND)" is shorthand for "(OUTPUT DEFEND)".
            self.tokens.queue.appendleft(token)
            kind = NodeKind.OUTPUT
        node = Node(id=self.next_id, kind=kind, depth=depth)
        self.next_id += 1
        if kind is NodeKind.OUTPUT:
            node.action = self.action()
            return node
        input_kind, count, branches = NODE_SHAPES[kind]
        for _ in range(count):
            if self.tokens.queue and self.tokens.queue[0] in NodeKind.__members__:
                s = "s" if count > 1 else ""
                raise self.tokens.error(f"{kind.value} nodes need {count} {input_kind} input{s}, "
                                        f"found {self.tokens.queue[0]}")
            node.inputs.append(self.input(kind, input_kind))
        node.children = [self.node(depth + 1) for _ in branches]
        return node

    def action(self) -> Action:
        token = self.tokens.take("an action")
        if token in SIMPLE_ACTIONS:
            return SIMPLE_ACTIONS[token]()
        prefix, _, direction = token.partition("_")
        if prefix == "MOVE" and direction in ("LEFT", "RIGHT", "UP", "DOWN"):
            return Move(direction)
        if prefix == "ATTACK" and direction in ("LEFT", "RIGHT", "UP", "DOWN"):
            return Attack(direction)
        if token == "CHANGE_TREE":
            return ChangeTree(self.tokens.take("a tree name for CHANGE_TREE"))
        if token == "SET_PRIMARY":
            return SetPrimary(self.position("SET_PRIMARY"))
        if token == "SET_SECONDARY":
            return SetSecondary(self.position("SET_SECONDARY"))
        raise self.tokens.error(f"unknown action '{token}'")

    def input(self, node_kind: NodeKind, expected: str) -> Input:
        token = self.tokens.take(f"a {expected} input for a {node_kind.value} node")
        cls = INPUTS.get(token)
        if cls is None:
            raise self.tokens.error(f"unknown input '{token}'")
        if cls.kind != expected:
            raise self.tokens.error(
                f"{node_kind.value} nodes need {expected} inputs, but {token} is a {cls.kind} input")
        values = []
        for arg in cls.args:
            if arg == "position":
                values.append(self.position(token))
            elif arg == "int":
                values.append(self.tokens.take_int(f"{token}'s value"))
            elif arg == "activity":
                values.append(self.activity(token))
            else:
                values.append(self.tokens.take(f"{token}'s {arg}"))
        return cls(*values)

    def position(self, context: str) -> Position:
        token = self.tokens.take(f"a position for {context}")
        if token in SIMPLE_POSITIONS:
            return SIMPLE_POSITIONS[token]()
        if token == "XY_VALUE":
            return XYValue(self.tokens.take_int("XY_VALUE's x"), self.tokens.take_int("XY_VALUE's y"))
        known = ", ".join([*SIMPLE_POSITIONS, "XY_VALUE x y"])
        raise self.tokens.error(f"unknown position '{token}' for {context} (expected one of {known})")

    def activity(self, context: str) -> Activity:
        token = self.tokens.take(f"an action name for {context}")
        try:
            return Activity(token)
        except ValueError:
            raise self.tokens.error(f"unknown action '{token}' for {context}") from None


class _Parser:
    def __init__(self, text: str):
        self.lines = text.splitlines()
        self.i = 0

    def error(self, message: str, line: int | None = None) -> MapFormatError:
        return MapFormatError(message, line if line is not None else self.i + 1)

    def key_line(self, key: str) -> str:
        if self.i >= len(self.lines):
            raise self.error(f"the file ended early, while expecting '{key}='")
        name, sep, value = self.lines[self.i].strip().partition("=")
        if not sep or name != key:
            raise self.error(f"expected '{key}=' but found '{self.lines[self.i].strip()}'")
        self.i += 1
        return value.strip()

    def int_value(self, text: str, what: str, line: int | None = None) -> int:
        try:
            return int(text)
        except ValueError:
            raise self.error(f"expected a number for {what} but found '{text}'", line) from None

    def grid(self, key: str, width: int, height: int) -> list[list[int]]:
        self.key_line(key)
        rows = []
        for y in range(height):
            if self.i >= len(self.lines):
                raise self.error(f"the {key} grid needs {height} rows")
            values = self.lines[self.i].split()
            if len(values) < width:
                raise self.error(f"the {key} grid needs {width} numbers per row, found {len(values)}")
            rows.append([self.int_value(v, f"{key} at x={x} y={y}") for x, v in enumerate(values[:width])])
            self.i += 1
        return rows

    def fields(self, line: str, required: tuple[str, ...]) -> dict[str, str]:
        values = {}
        for part in line.split(","):
            key, _, value = part.partition("=")
            values[key.strip()] = value.strip()
        missing = [k for k in required if k not in values]
        if missing:
            raise self.error(f"missing {', '.join(missing)}")
        return values

    def parse(self, seed: int | None) -> World:
        height = self.int_value(self.key_line("height"), "height", 1)
        width = self.int_value(self.key_line("width"), "width", 2)
        if width < 1 or height < 1:
            raise MapFormatError("width and height must be at least 1")
        food = self.grid("food", width, height)
        dirt = self.grid("dirt", width, height)
        tiles = [[Tile(dirt[y][x], food[y][x]) for y in range(height)] for x in range(width)]

        plants = []
        for n in range(self.int_value(self.key_line("plants"), "plants")):
            if self.i >= len(self.lines):
                raise self.error("the file ended early, while reading plants")
            values = self.fields(self.lines[self.i], ("x", "y", "rate"))
            pos = XY(self.int_value(values["x"], "plant x"), self.int_value(values["y"], "plant y"))
            if not (0 <= pos.x < width and 0 <= pos.y < height):
                raise self.error(f"plant at {pos} is off the map")
            plants.append(Plant(f"Plant{n}", pos, self.int_value(values["rate"], "plant rate")))
            self.i += 1

        max_agents = 1
        mode = None
        player_lines: list[tuple[int, dict[str, str], list[Tree]]] = []
        criteria_lines: list[tuple[int, str]] = []
        while self.i < len(self.lines):
            line_no = self.i + 1
            line = self.lines[self.i].strip()
            self.i += 1
            key, _, value = line.partition("=")
            if key == "maxAgents":
                max_agents = self.int_value(value, "maxAgents", line_no)
            elif key == "name":
                self.i -= 1
                values = self.fields(line, ("name", "speed", "health", "power", "x", "y"))
                self.i += 1
                player_lines.append((line_no, values, []))
            elif key == "tree":
                if not player_lines:
                    raise self.error("tree= must come after a player's name= line", line_no)
                player_lines[-1][2].append(_TreeParser(value, line_no).parse())
            elif key == "criteria":
                count = self.int_value(value, "criteria", line_no)
                for _ in range(count):
                    if self.i >= len(self.lines):
                        raise self.error(f"expected {count} criteria lines")
                    criteria_lines.append((self.i + 1, self.lines[self.i].strip()))
                    self.i += 1
            elif key == "mode" and mode is None:
                mode = value if value in MODES else "CLICK"
            # Anything else (blank lines, the legacy "players=" line and action legend) is ignored.

        players = [self.player(line_no, values, trees, max_agents, width, height)
                   for line_no, values, trees in player_lines]
        occupied: dict[XY, str] = {}
        for (line_no, _, _), player in zip(player_lines, players):
            pos = player.agents[0].pos
            if pos in occupied:
                raise self.error(f"{player.name}'s agent starts on the same tile as {occupied[pos]}'s",
                                 line_no)
            occupied[pos] = player.name
        for n, agent in enumerate(a for p in players for a in p.agents):
            agent.id = f"Agent{n}"

        criteria = [self.criterion(line_no, line, players, plants, width, height)
                    for line_no, line in criteria_lines]
        return World(width, height, tiles, players, plants, criteria, mode or "CLICK", seed)

    def player(self, line_no: int, values: dict[str, str], trees: list[Tree], max_agents: int,
               width: int, height: int) -> Player:
        name = values["name"]
        if not trees:
            hint = (" This looks like the old 'decision=' format, which isn't supported."
                    if "decision" in values or "nodes" in values else "")
            raise self.error(f"player '{name}' has no tree= lines.{hint}", line_no)
        stats = {k: self.int_value(values[k], k, line_no) for k in ("speed", "health", "power", "x", "y")}
        pos = XY(stats["x"], stats["y"])
        if not (0 <= pos.x < width and 0 <= pos.y < height):
            raise self.error(f"player '{name}' starts at {pos}, which is off the map", line_no)
        player = Player(name, stats["health"], stats["speed"], stats["power"], trees, max_agents)
        player.add_agent(Agent("", pos, player, stats["speed"], stats["health"], stats["power"],
                               trees[0], 0))
        return player

    def criterion(self, line_no: int, line: str, players: list[Player], plants: list[Plant],
                  width: int, height: int) -> Criterion:
        tokens = line.split()
        if not tokens:
            raise self.error("expected a criterion but found a blank line", line_no)

        def arg(n: int, what: str) -> str:
            if len(tokens) <= n:
                raise self.error(f"{tokens[0]} needs {what}", line_no)
            return tokens[n]

        def number(n: int, what: str) -> int:
            return self.int_value(arg(n, what), what, line_no)

        def player(n: int) -> Player:
            name = arg(n, "a player name")
            found = next((p for p in players if p.name == name), None)
            if found is None:
                raise self.error(f"{tokens[0]} refers to unknown player '{name}'", line_no)
            return found

        def position(n: int) -> XY:
            pos = XY(number(n, "an x position"), number(n + 1, "a y position"))
            if not (0 <= pos.x < width and 0 <= pos.y < height):
                raise self.error(f"{tokens[0]} position {pos} is off the map", line_no)
            return pos

        match tokens[0]:
            case "SURVIVE_TURNS":
                return SurviveTurns(number(1, "a number of turns"))
            case "ANNIHILATE":
                return Annihilate(player(1))
            case "COLLECT_FOOD":
                return CollectFood(player(1), number(2, "an amount of food"))
            case "LEVEL_UP":
                return LevelUp(player(1), number(2, "an amount of exp"))
            case "MAP_DIRT":
                return MapDirt(number(1, "an amount of dirt"), position(2))
            case "TRAVEL_TO":
                return TravelTo(player(1), position(2))
            case "PERFORM_ACTION":
                who = player(1)
                try:
                    activity = Activity(arg(2, "an action"))
                except ValueError:
                    raise self.error(f"unknown action '{tokens[2]}'", line_no) from None
                return PerformAction(who, activity, number(3, "a number of times"))
            case "FIND_THING":
                thing_id = arg(1, "an agent or plant id")
                things = [*(a for p in players for a in p.agents), *plants]
                thing = next((t for t in things if t.id == thing_id), None)
                if thing is None:
                    raise self.error(f"FIND_THING refers to unknown id '{thing_id}'", line_no)
                return FindThing(thing)
        raise self.error(f"unknown criterion '{tokens[0]}'", line_no)
