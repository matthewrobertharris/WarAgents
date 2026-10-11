"""The JSON formats the catalogue stores (maps, trees and games), and building a World from them.

A map is the board without the teams. Grid row n holds y = n, as in the .map format, and null
marks a hole: a place with no tile, which agents treat like the edge of the map. Each start is
where one of a team's first agents goes, and a slot can have several starts. Criteria that name a
team refer to it by slot.

    {"name": "Skirmish", "mode": "FIXED", "maxAgents": 12,
     "dirt": [[0, 0, null], ...], "food": [[4, 0, null], ...],
     "plants": [{"x": 3, "y": 3, "rate": 16}],
     "starts": [{"slot": 1, "x": 2, "y": 4}, {"slot": 2, "x": 13, "y": 5}],
     "criteria": [{"type": "ANNIHILATE", "slot": 1}, {"type": "SURVIVE_TURNS", "turns": 500}]}

A tree has a name, an owner (a player id, or null for a default tree every player can use) and
nested nodes. children follow the node's branches: true/false, </=/>, or left/right/up/down/current.
A position argument is a name such as "CURRENT", or {"x": 3, "y": 4}. null is an empty slot, which
a saved tree may have while it's being edited, but a game can't.

    {"name": "eat-or-wait", "owner": null,
     "root": {"kind": "BOOLEAN", "inputs": [{"name": "HAS_FOOD", "args": ["CURRENT"]}],
              "children": [{"kind": "OUTPUT", "action": "EAT"}, {"kind": "OUTPUT", "action": "DEFEND"}]}}

A game is a seed plus a copy of everything it started with, so it replays the same way even if
the map or trees are edited later. Each team carries the trees it can switch to.

    {"name": "...", "created": "2026-10-02T14:03:00", "seed": 3, "mapId": "skirmish", "map": {...},
     "teams": [{"slot": 1, "name": "green", "colour": "#2f9e44", "player": null,
                "speed": 10, "health": 100, "power": 10, "startTree": "graze", "trees": [...]}],
     "criteria": [...]}
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, fields, is_dataclass
from typing import Any

from .actions import ACTION_ARGS, Action, Activity, make_action
from .criteria import (Annihilate, CollectFood, Criterion, FindThing, LevelUp, MapDirt,
                       PerformAction, SurviveTurns, TravelTo)
from .inputs import INPUTS, Input
from .mapfile import parse_map
from .positions import SIMPLE_POSITIONS, Position, XYValue
from .tree import NODE_SHAPES, Node, NodeKind, Tree
from .world import MAX_DIRT, MAX_FOOD, MODES, XY, Agent, Plant, Player, Tile, World

ACTIONS = {a.value for a in Activity}

# Each criterion's fields, in order. "slot" is a team's start slot and "x"/"y" a tile on the map.
CRITERIA: dict[str, tuple[tuple[str, str], ...]] = {
    "SURVIVE_TURNS": (("turns", "int"),),
    "ANNIHILATE": (("slot", "slot"),),
    "COLLECT_FOOD": (("slot", "slot"), ("amount", "int")),
    "LEVEL_UP": (("slot", "slot"), ("exp", "int")),
    "MAP_DIRT": (("dirt", "int"), ("x", "x"), ("y", "y")),
    "TRAVEL_TO": (("slot", "slot"), ("x", "x"), ("y", "y")),
    "PERFORM_ACTION": (("slot", "slot"), ("action", "action"), ("times", "int")),
    "FIND_THING": (("thing", "thing"),),
}


class ScenarioError(ValueError):
    """A map, tree or game that can't be used. problems lists everything wrong, not just the first."""

    def __init__(self, problems: list):
        self.problems = problems
        shown = "; ".join(str(p) for p in problems[:5])
        more = f" (and {len(problems) - 5} more)" if len(problems) > 5 else ""
        super().__init__(shown + more)


@dataclass(frozen=True)
class Problem:
    """Something wrong in a tree. path is the child indexes from the root to the node."""

    path: tuple[int, ...]
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {"path": list(self.path), "where": self.where, "message": self.message}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _name_problem(name: Any, what: str) -> str | None:
    if not isinstance(name, str) or not name.strip():
        return f"{what} needs a name"
    if any(c.isspace() for c in name):
        return f"{what} name '{name}' can't contain spaces"
    return None


# ---- trees -------------------------------------------------------------------------


def position_to_json(position: Position) -> str | dict[str, int]:
    if isinstance(position, XYValue):
        return {"x": position.x, "y": position.y}
    return position.name


def _args_to_json(obj: Input | Action) -> list:
    if not is_dataclass(obj):
        return []
    values = []
    for f in fields(obj):
        value = getattr(obj, f.name)
        values.append(position_to_json(value) if isinstance(value, Position)
                      else value.value if isinstance(value, Activity) else value)
    return values


def _with_args(data: dict[str, Any], args: list) -> dict[str, Any]:
    if args:
        data["args"] = args
    return data


def node_to_json(node: Node) -> dict[str, Any]:
    if node.kind is NodeKind.OUTPUT:
        return _with_args({"kind": "OUTPUT", "action": node.action.activity.value},
                          _args_to_json(node.action))
    return {
        "kind": node.kind.value,
        "inputs": [_with_args({"name": i.name}, _args_to_json(i)) for i in node.inputs],
        "children": [node_to_json(c) for c in node.children],
    }


def tree_to_json(tree: Tree, owner: str | None = None) -> dict[str, Any]:
    return {"name": tree.name, "owner": owner, "root": node_to_json(tree.root)}


_MISSING = object()  # an empty argument in a tree that's still being edited


class _TreeReader:
    def __init__(self, allow_empty: bool):
        self.allow_empty = allow_empty
        self.problems: list[Problem] = []
        self.next_id = 0

    def node(self, data: Any, depth: int, path: list[int], labels: list[str]) -> Node | None:
        def here(message: str) -> None:
            self.problems.append(Problem(tuple(path), " › ".join(["root", *labels]), message))

        if data is None:
            if not self.allow_empty:
                here("this slot is empty")
            return None
        if not isinstance(data, dict):
            here("a node must be an object")
            return None
        try:
            kind = NodeKind(data.get("kind"))
        except ValueError:
            here(f"unknown node kind {data.get('kind')!r}")
            return None
        node = Node(id=self.next_id, kind=kind, depth=depth)
        self.next_id += 1
        if kind is NodeKind.OUTPUT:
            node.action = self.action(data.get("action"), data.get("args", []), here)
            return node

        input_kind, count, branches = NODE_SHAPES[kind]
        inputs = data.get("inputs")
        if not isinstance(inputs, list) or len(inputs) != count:
            s = "s" if count > 1 else ""
            here(f"{kind.value} nodes need {count} {input_kind} input{s}")
            inputs = [None] * count
        node.inputs = [self.input(item, kind, input_kind, here) for item in inputs]
        children = data.get("children")
        if not isinstance(children, list) or len(children) != len(branches):
            here(f"{kind.value} nodes need {len(branches)} branches ({', '.join(branches)})")
            children = [None] * len(branches)
        node.children = [self.node(child, depth + 1, [*path, i], [*labels, branches[i]])
                         for i, child in enumerate(children)]
        return node

    def action(self, name: Any, args: Any, here) -> Action | None:
        if name is None:
            if not self.allow_empty:
                here("choose an action")
            return None
        if name not in ACTIONS:
            here(f"unknown action {name!r}")
            return None
        values = self.args(args, ACTION_ARGS.get(name, ()), name, here)
        return None if values is None else make_action(name, values)

    def input(self, data: Any, node_kind: NodeKind, expected: str, here) -> Input | None:
        if data is None:
            if not self.allow_empty:
                here(f"choose a {expected} input")
            return None
        name = data.get("name") if isinstance(data, dict) else None
        cls = INPUTS.get(name) if isinstance(name, str) else None
        if cls is None:
            here(f"unknown input {name!r}")
            return None
        if cls.kind != expected:
            here(f"{node_kind.value} nodes need {expected} inputs, but {name} is a {cls.kind} input")
            return None
        values = self.args(data.get("args", []), cls.args, name, here)
        return None if values is None else cls(*values)

    def args(self, given: Any, spec: tuple[str, ...], context: str, here) -> list | None:
        """The parsed arguments, or None if any are wrong or still empty."""
        if not isinstance(given, list) or len(given) != len(spec):
            wanted = f"{len(spec)} argument{'s' if len(spec) != 1 else ''} ({', '.join(spec)})"
            here(f"{context} takes {wanted}" if spec else f"{context} takes no arguments")
            return None
        values = [self.arg(kind, value, context, here) for kind, value in zip(spec, given)]
        return None if any(v is _MISSING for v in values) else values

    def arg(self, kind: str, value: Any, context: str, here) -> Any:
        if value is None:
            if not self.allow_empty:
                here(f"{context} needs its {kind} filled in")
            return _MISSING
        if kind == "position":
            if isinstance(value, str) and value in SIMPLE_POSITIONS:
                return SIMPLE_POSITIONS[value]()
            if isinstance(value, dict) and _is_int(value.get("x")) and _is_int(value.get("y")):
                return XYValue(value["x"], value["y"])
            known = ", ".join([*SIMPLE_POSITIONS, '{"x": .., "y": ..}'])
            here(f"unknown position {value!r} for {context} (expected one of {known})")
        elif kind == "int":
            if _is_int(value):
                return value
            here(f"{context} needs a whole number, not {value!r}")
        elif kind == "activity":
            if value in ACTIONS:
                return Activity(value)
            here(f"unknown action {value!r} for {context}")
        else:
            problem = _name_problem(value, f"{context}'s tree")
            if problem is None:
                return value
            here(problem)
        return _MISSING


def check_tree(data: Any, allow_empty: bool = True) -> list[Problem]:
    """Everything wrong with a tree. With allow_empty, unfilled slots aren't counted."""
    if not isinstance(data, dict):
        return [Problem((), "tree", "a tree must be an object")]
    reader = _TreeReader(allow_empty)
    problem = _name_problem(data.get("name"), "the tree")
    if problem:
        reader.problems.append(Problem((), "name", problem))
    reader.node(data.get("root"), 0, [], [])
    return reader.problems


def tree_from_json(data: dict[str, Any]) -> Tree:
    """A playable tree. Raises ScenarioError if the tree has mistakes or empty slots."""
    reader = _TreeReader(allow_empty=False)
    problem = _name_problem(data.get("name"), "the tree")
    root = reader.node(data.get("root"), 0, [], [])
    problems = ([f"tree: {problem}"] if problem else []) + [
        f"tree '{data.get('name')}', {p}" for p in reader.problems]
    if problems:
        raise ScenarioError(problems)
    return Tree(data["name"], root)


def _walk(node: Any):
    stack = [node]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            yield node
            stack.extend(node.get("children") or [])


def tree_references(data: dict[str, Any]) -> set[str]:
    """The names of the trees this tree can switch to with CHANGE_TREE."""
    return {node["args"][0] for node in _walk(data.get("root"))
            if node.get("action") == "CHANGE_TREE" and node.get("args")}


def rename_trees(data: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    """A copy of a tree with CHANGE_TREE, CURRENT_TREE and NUMBER_TREES pointed at new names."""
    data = copy.deepcopy(data)
    data["name"] = names.get(data["name"], data["name"])
    for node in _walk(data.get("root")):
        if node.get("action") in ACTION_ARGS and ACTION_ARGS[node["action"]] == ("name",):
            node["args"] = [names.get(a, a) for a in node.get("args", [])]
        for item in node.get("inputs") or []:
            cls = INPUTS.get(item.get("name")) if isinstance(item, dict) else None
            if cls is not None and "name" in cls.args:
                item["args"] = [names.get(a, a) if kind == "name" else a
                                for kind, a in zip(cls.args, item.get("args", []))]
    return data


# ---- maps ----------------------------------------------------------------------------


def map_size(data: dict[str, Any]) -> tuple[int, int]:
    return len(data["dirt"][0]), len(data["dirt"])


def map_slots(data: dict[str, Any]) -> list[int]:
    return sorted({s["slot"] for s in data["starts"]})


def _check_grids(data: dict[str, Any]) -> list[str]:
    grids = {key: data.get(key) for key in ("dirt", "food")}
    for key, grid in grids.items():
        if (not isinstance(grid, list) or not grid
                or not all(isinstance(row, list) and row for row in grid)):
            return [f"{key} must be a list of rows"]
    width = len(grids["dirt"][0])
    for key, grid in grids.items():
        if len(grid) != len(grids["dirt"]) or any(len(row) != width for row in grid):
            return [f"{key} must have {len(grids['dirt'])} rows of {width} values, like dirt"]

    problems = []
    limits = {"dirt": MAX_DIRT, "food": MAX_FOOD}
    tiles = 0
    for y, (dirt_row, food_row) in enumerate(zip(grids["dirt"], grids["food"])):
        for x, (dirt, food) in enumerate(zip(dirt_row, food_row)):
            if (dirt is None) != (food is None):
                problems.append(f"x={x} y={y} is a hole in one of dirt and food but not the other")
                continue
            if dirt is None:
                continue
            tiles += 1
            for key, value in (("dirt", dirt), ("food", food)):
                if not _is_int(value) or not 0 <= value <= limits[key]:
                    problems.append(f"{key} at x={x} y={y} must be a whole number from 0 to {limits[key]}")
    if not tiles:
        problems.append("the map has no tiles")
    return problems


def check_map(data: Any, allow_unfinished: bool = False) -> list[str]:
    """Everything wrong with a map.

    With allow_unfinished, things a map may lack while it's being edited aren't counted: having
    no starts, and win conditions that point at a slot or tile that isn't there (yet). A map like
    that can be saved but not played.
    """
    if not isinstance(data, dict):
        return ["a map must be an object"]
    problems: list[str] = []
    unfinished: list[str] = []
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        problems.append("the map needs a name")
    grid_problems = _check_grids(data)
    if grid_problems:
        return problems + grid_problems

    width, height = map_size(data)

    def on_map(item: dict, what: str, into: list[str] = problems) -> bool:
        x, y = item.get("x"), item.get("y")
        if not (_is_int(x) and _is_int(y)):
            problems.append(f"{what} needs a whole-number x and y")
        elif not (0 <= x < width and 0 <= y < height) or data["dirt"][y][x] is None:
            into.append(f"{what} at x={x} y={y} isn't on a tile")
        else:
            return True
        return False

    if data.get("mode") not in MODES:
        problems.append(f"mode must be one of {', '.join(MODES)}")
    if not _is_int(data.get("maxAgents")) or data["maxAgents"] < 1:
        problems.append("maxAgents must be a whole number of at least 1")

    plants, starts = data.get("plants"), data.get("starts")
    if not isinstance(plants, list) or not all(isinstance(p, dict) for p in plants):
        problems.append("plants must be a list of {x, y, rate}")
        plants = []
    planted = set()
    for n, plant in enumerate(plants):
        if on_map(plant, f"plant {n}"):
            if (plant["x"], plant["y"]) in planted:
                problems.append(f"two plants at x={plant['x']} y={plant['y']}")
            planted.add((plant["x"], plant["y"]))
        if not _is_int(plant.get("rate")) or plant["rate"] < 0:
            problems.append(f"plant {n} needs a rate of 0 or more")

    if not isinstance(starts, list) or not all(isinstance(s, dict) for s in starts):
        problems.append("starts must be a list of {slot, x, y}")
        starts = []
    if not starts:
        unfinished.append("the map needs at least one start")
    taken = set()
    for start in starts:
        slot = start.get("slot")
        if not _is_int(slot) or slot < 1:
            problems.append(f"start slot {slot!r} must be a whole number of at least 1")
            continue
        if on_map(start, f"slot {slot}'s start"):
            if (start["x"], start["y"]) in taken:
                problems.append(f"two starts at x={start['x']} y={start['y']}")
            taken.add((start["x"], start["y"]))

    slots = {s.get("slot") for s in starts}
    criteria = data.get("criteria")
    if not isinstance(criteria, list):
        problems.append("criteria must be a list")
        criteria = []
    for criterion in criteria:
        kind = criterion.get("type") if isinstance(criterion, dict) else None
        if kind not in CRITERIA:
            problems.append(f"unknown criterion {kind!r}")
            continue
        for key, value_kind in CRITERIA[kind]:
            value = criterion.get(key)
            if value_kind == "slot" and value not in slots:
                if _is_int(value):
                    unfinished.append(f"{kind} refers to slot {value}, which has no start")
                else:
                    problems.append(f"{kind} needs a slot number")
            elif value_kind == "int" and (not _is_int(value) or value < 0):
                problems.append(f"{kind} needs a {key} of 0 or more")
            elif value_kind == "action" and value not in ACTIONS:
                problems.append(f"{kind} refers to unknown action {value!r}")
            elif value_kind == "thing" and not isinstance(value, str):
                problems.append(f"{kind} needs the id of a plant or agent, such as Plant0")
        if any(value_kind == "x" for _, value_kind in CRITERIA[kind]):
            on_map(criterion, kind, unfinished)
    return problems if allow_unfinished else problems + unfinished


# ---- games ---------------------------------------------------------------------------


def check_game(game: Any) -> list[str]:
    """Everything wrong with a game record."""
    if not isinstance(game, dict):
        return ["a game must be an object"]
    map_problems = check_map(game.get("map"))
    if map_problems:
        return [f"map: {p}" for p in map_problems]
    problems = []
    if not _is_int(game.get("seed")):
        problems.append("the game needs a whole-number seed")
    slots = set(map_slots(game["map"]))
    teams = game.get("teams")
    if not isinstance(teams, list) or not teams:
        return problems + ["the game needs at least one team"]

    seen_slots, seen_names = set(), set()
    for n, team in enumerate(teams):
        if not isinstance(team, dict):
            problems.append(f"team {n + 1} must be an object")
            continue
        label = f"team '{team.get('name')}'"
        if not isinstance(team.get("name"), str) or not team["name"].strip():
            problems.append(f"team {n + 1} needs a name")
        elif team["name"] in seen_names:
            problems.append(f"two teams are called '{team['name']}'")
        seen_names.add(team.get("name"))
        if team.get("slot") not in slots:
            problems.append(f"{label} uses slot {team.get('slot')!r}, which the map doesn't have")
        elif team["slot"] in seen_slots:
            problems.append(f"two teams use slot {team['slot']}")
        seen_slots.add(team.get("slot"))
        for stat in ("speed", "health", "power"):
            if not _is_int(team.get(stat)) or team[stat] < 1:
                problems.append(f"{label} needs a {stat} of at least 1")
        problems.extend(_check_team_trees(team, label))
    if not isinstance(game.get("criteria"), list):
        problems.append("criteria must be a list")
    return problems


def _check_team_trees(team: dict[str, Any], label: str) -> list[str]:
    trees = team.get("trees")
    if not isinstance(trees, list) or not trees:
        return [f"{label} needs at least one tree"]
    problems = []
    names = set()
    for tree in trees:
        problems.extend(f"{label}: {p}" for p in _tree_problems(tree))
        if isinstance(tree, dict):
            if tree.get("name") in names:
                problems.append(f"{label} has two trees called '{tree.get('name')}'")
            names.add(tree.get("name"))
    if team.get("startTree") not in names:
        problems.append(f"{label} starts with tree '{team.get('startTree')}', which it doesn't have")
    for tree in trees:
        if isinstance(tree, dict):
            for missing in sorted(tree_references(tree) - names):
                problems.append(f"{label}: '{tree.get('name')}' switches to tree '{missing}', "
                                "which the team doesn't have")
    return problems


def _tree_problems(tree: Any) -> list[str]:
    try:
        tree_from_json(tree if isinstance(tree, dict) else {})
    except ScenarioError as e:
        return [str(p) for p in e.problems]
    return []


def build_world(game: dict[str, Any]) -> World:
    """Set up a game record's world at turn 0. Raises ScenarioError if the record is wrong."""
    problems = check_game(game)
    if problems:
        raise ScenarioError(problems)
    data = game["map"]
    width, height = map_size(data)
    tiles = [[None if data["dirt"][y][x] is None else Tile(data["dirt"][y][x], data["food"][y][x])
              for y in range(height)] for x in range(width)]
    plants = [Plant(f"Plant{n}", XY(p["x"], p["y"]), p["rate"]) for n, p in enumerate(data["plants"])]

    players: list[Player] = []
    by_slot: dict[int, Player] = {}
    for team in game["teams"]:
        trees = [tree_from_json(t) for t in team["trees"]]
        start_tree = next(t for t in trees if t.name == team["startTree"])
        player = Player(team["name"], team["health"], team["speed"], team["power"], trees,
                        data["maxAgents"])
        player.colour = team.get("colour")
        for start in data["starts"]:
            if start["slot"] == team["slot"]:
                player.add_agent(Agent("", XY(start["x"], start["y"]), player, team["speed"],
                                       team["health"], team["power"], start_tree, 0))
        players.append(player)
        by_slot[team["slot"]] = player
    agents = [a for p in players for a in p.agents]
    for n, agent in enumerate(agents):
        agent.id = f"Agent{n}"

    things = {t.id: t for t in [*plants, *agents]}
    criteria = []
    for item in game["criteria"]:
        criterion = criterion_from_json(item, by_slot, things)
        if criterion is not None:
            criteria.append(criterion)
    return World(width, height, tiles, players, plants, criteria, data["mode"], game["seed"])


def criterion_from_json(data: dict[str, Any], by_slot: dict[int, Player],
                        things: dict[str, Any]) -> Criterion | None:
    """The criterion, or None if it's about a slot that has no team in this game."""
    if "slot" in data and data["slot"] not in by_slot:
        return None
    player = by_slot.get(data.get("slot"))
    match data["type"]:
        case "SURVIVE_TURNS":
            return SurviveTurns(data["turns"])
        case "ANNIHILATE":
            return Annihilate(player)
        case "COLLECT_FOOD":
            return CollectFood(player, data["amount"])
        case "LEVEL_UP":
            return LevelUp(player, data["exp"])
        case "MAP_DIRT":
            return MapDirt(data["dirt"], XY(data["x"], data["y"]))
        case "TRAVEL_TO":
            return TravelTo(player, XY(data["x"], data["y"]))
        case "PERFORM_ACTION":
            return PerformAction(player, Activity(data["action"]), data["times"])
        case "FIND_THING":
            thing = things.get(data["thing"])
            if thing is None:
                raise ScenarioError([f"FIND_THING refers to '{data['thing']}', which isn't in this game"])
            return FindThing(thing)
    raise ScenarioError([f"unknown criterion {data['type']!r}"])


# ---- importing .map files ------------------------------------------------------------


def criterion_to_json(criterion: Criterion, slot_of: dict[int, int]) -> dict[str, Any]:
    """slot_of maps id(player) to the player's slot."""
    def slot(player: Player) -> int:
        return slot_of[id(player)]

    match criterion:
        case SurviveTurns():
            return {"type": "SURVIVE_TURNS", "turns": criterion.turns}
        case Annihilate():
            return {"type": "ANNIHILATE", "slot": slot(criterion.player)}
        case CollectFood():
            return {"type": "COLLECT_FOOD", "slot": slot(criterion.player), "amount": criterion.total}
        case LevelUp():
            return {"type": "LEVEL_UP", "slot": slot(criterion.player), "exp": criterion.exp}
        case MapDirt():
            return {"type": "MAP_DIRT", "dirt": criterion.dirt, "x": criterion.position.x,
                    "y": criterion.position.y}
        case TravelTo():
            return {"type": "TRAVEL_TO", "slot": slot(criterion.player), "x": criterion.position.x,
                    "y": criterion.position.y}
        case PerformAction():
            return {"type": "PERFORM_ACTION", "slot": slot(criterion.player),
                    "action": criterion.activity.value, "times": criterion.times}
        case FindThing():
            return {"type": "FIND_THING", "thing": criterion.thing.id}
    raise TypeError(f"can't convert {criterion!r}")


def import_map_text(text: str, name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Convert a .map file into a catalogue map and its teams.

    Each team becomes a slot, numbered in file order. Returns (map, teams), where each team has
    its stats, its trees as JSON and the name of its starting tree. Raises MapFormatError.
    """
    world = parse_map(text)
    slot_of = {id(p): n + 1 for n, p in enumerate(world.players)}
    data = {
        "name": name,
        "mode": world.mode,
        "maxAgents": max((p.max_agents for p in world.players), default=10),
        "dirt": [[world.tiles[x][y].dirt for x in range(world.width)] for y in range(world.height)],
        "food": [[world.tiles[x][y].food for x in range(world.width)] for y in range(world.height)],
        "plants": [{"x": p.pos.x, "y": p.pos.y, "rate": p.rate} for p in world.plants],
        "starts": [{"slot": slot_of[id(p)], "x": a.x, "y": a.y} for p in world.players for a in p.agents],
        "criteria": [criterion_to_json(c, slot_of) for c in world.criteria],
    }
    teams = [{
        "slot": slot_of[id(p)],
        "name": p.name,
        "speed": p.agent_speed,
        "health": p.agent_health,
        "power": p.agent_power,
        "startTree": p.agents[0].tree.name,
        "trees": [tree_to_json(t) for t in p.trees],
    } for p in world.players]
    return data, teams
