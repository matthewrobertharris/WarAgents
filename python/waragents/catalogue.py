"""The catalogue: maps, trees, players and games, stored as one JSON file per item.

    catalogue/
      maps/skirmish.json
      trees/graze.json
      players/matthew.json
      games/20261002-140301-3f9a.json
      results/20261002-140301-3f9a.json

An item's id is its file name. A new item's id is made from its name, and renaming the item later
keeps the id. scenario.py describes what's in each kind of file.

A player is an account, and its id is the username:
{"name": "Matthew", "colour": "#1c7ed6", "created": "2026-10-03T09:30:00", "startTree": "graze",
 "xp": 350, "passwordHash": "...", "admin": true}.
xp is their account XP, which sets their level and so their tree budget (progression.py).
startTree is their default tree: the one their teams start with unless another is chosen, and the
one that plays for them when someone else picks them as an opponent. Like CHANGE_TREE, it's looked
up in their own trees and then the defaults. passwordHash and admin are managed by web/auth.py.

A tree with an owner belongs to that player. A tree with no owner is a default tree, which every
player can use. When a team switches trees with CHANGE_TREE, it looks in its player's trees first,
then the defaults. Maps have an owner too (null for a system map) and can be published, which
lets every player use them.

A game's result is saved next to it, under the same id, once the game is over: who placed where
and the XP each player got for it (battles.py). It's kept apart from the game record because the
record is what replays the game, and must never change.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from .progression import DEFAULT_MAX_TURNS
from .scenario import (RULES_VERSION, ScenarioError, check_game, check_map, check_tree,
                       import_map_text, rename_trees, tree_references)

KINDS = ("maps", "trees", "players", "games", "results", "tutorials", "seasons")
GAME_MODES = ("sandbox", "training", "skirmish", "season")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
_COLOUR = re.compile(r"#[0-9a-fA-F]{6}")
DEFAULT_STATS = {"speed": 10, "health": 100, "power": 10}


class NotFound(LookupError):
    pass


class CatalogueError(ValueError):
    """A save or delete that was refused. problems lists the reasons."""

    def __init__(self, problems: list):
        self.problems = [str(p) for p in problems]
        super().__init__("; ".join(self.problems[:5]))


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def dumps(value: Any, indent: int = 0, width: int = 100) -> str:
    """JSON that keeps short objects and rows of numbers on one line, so files diff well."""
    compact = json.dumps(value, ensure_ascii=False)
    if not isinstance(value, (list, dict)) or not value or len(compact) + indent <= width:
        return compact
    pad = " " * (indent + 2)
    if isinstance(value, list):
        if not any(isinstance(v, (list, dict)) for v in value):
            return compact
        items = [pad + dumps(v, indent + 2, width) for v in value]
        return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"
    items = [f"{pad}{json.dumps(k, ensure_ascii=False)}: {dumps(v, indent + 2, width)}"
             for k, v in value.items()]
    return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"


class Catalogue:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    # ---- files ---------------------------------------------------------------------

    def _path(self, kind: str, item_id: str) -> Path:
        if kind not in KINDS:
            raise NotFound(f"There's no '{kind}' in the catalogue")
        if not isinstance(item_id, str) or not _ID.fullmatch(item_id):
            raise NotFound(f"No {kind[:-1]} called '{item_id}'")
        return self.root / kind / f"{item_id}.json"

    def exists(self, kind: str, item_id: str) -> bool:
        try:
            return self._path(kind, item_id).exists()
        except NotFound:
            return False

    def list(self, kind: str) -> list[dict[str, Any]]:
        """Every item of a kind, each with its "id". Unreadable files are listed with an "error"."""
        if kind not in KINDS:
            raise NotFound(f"There's no '{kind}' in the catalogue")
        items = []
        for path in sorted((self.root / kind).glob("*.json"), key=lambda p: p.stem):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                data = {"name": path.stem, "error": f"Can't read {path.name}: {e}"}
            items.append({"id": path.stem, **data})
        return items

    def get(self, kind: str, item_id: str) -> dict[str, Any]:
        path = self._path(kind, item_id)
        if not path.exists():
            raise NotFound(f"No {kind[:-1]} called '{item_id}'")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, kind: str, item_id: str, data: dict[str, Any]) -> None:
        path = self._path(kind, item_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in data.items() if k != "id"}
        temp = path.with_suffix(".tmp")
        temp.write_text(dumps(data) + "\n", encoding="utf-8")
        os.replace(temp, path)  # so a crash never leaves half a file

    def new_id(self, kind: str, name: str) -> str:
        base = slugify(name) or kind[:-1]
        item_id, n = base, 2
        while self.exists(kind, item_id):
            item_id, n = f"{base}-{n}", n + 1
        return item_id

    # ---- checked changes -----------------------------------------------------------

    def create(self, kind: str, data: dict[str, Any]) -> str:
        """Save a new item with an id made from its name. Returns the id."""
        return self.create_with_id(kind, None, data)

    def create_with_id(self, kind: str, item_id: str | None, data: dict[str, Any]) -> str:
        """Save a new item as item_id (or an id made from its name), which mustn't be taken."""
        if kind in ("games", "results"):
            raise CatalogueError(["Games and their results are saved by playing a game"])
        self._check(kind, data, None)
        if kind == "players" and not data.get("created"):
            data = {**data, "created": datetime.now().isoformat(timespec="seconds")}
        if item_id is None:
            item_id = self.new_id(kind, str(data.get("name", "")))
        elif self.exists(kind, item_id):
            raise CatalogueError([f"There's already a {kind[:-1]} called '{item_id}'"])
        self._path(kind, item_id)  # checks the id is allowed
        self._write(kind, item_id, data)
        return item_id

    def update(self, kind: str, item_id: str, data: dict[str, Any]) -> None:
        if not self.exists(kind, item_id):
            raise NotFound(f"No {kind[:-1]} called '{item_id}'")
        self._check(kind, data, item_id)
        self._write(kind, item_id, data)

    def delete(self, kind: str, item_id: str) -> None:
        path = self._path(kind, item_id)
        if not path.exists():
            raise NotFound(f"No {kind[:-1]} called '{item_id}'")
        if kind == "players":
            owned = [t["name"] for t in self.list("trees") if t.get("owner") == item_id]
            if owned:
                raise CatalogueError([f"This player still owns {len(owned)} tree(s): "
                                      f"{', '.join(owned)}. Delete or move them first."])
        path.unlink()
        if kind == "games" and self.exists("results", item_id):
            self._path("results", item_id).unlink()

    def _check(self, kind: str, data: Any, item_id: str | None) -> None:
        if not isinstance(data, dict):
            raise CatalogueError([f"A {kind[:-1]} must be a JSON object"])
        problems: list = []
        if kind == "maps":
            problems = check_map(data, allow_unfinished=True)
            owner = data.get("owner")
            if owner is not None and not self.exists("players", owner):
                problems.append(f"the owner '{owner}' isn't a player in the catalogue")
            if not isinstance(data.get("published", False), bool):
                problems.append("published must be true or false")
        elif kind == "trees":
            problems = check_tree(data, allow_empty=True)
            owner = data.get("owner")
            if owner is not None and not self.exists("players", owner):
                problems.append(f"the owner '{owner}' isn't a player in the catalogue")
            clash = next((t for t in self.list("trees") if t["id"] != item_id
                          and t.get("owner") == owner and t.get("name") == data.get("name")), None)
            if clash:
                whose = "a default tree" if owner is None else f"a tree of {owner}'s"
                problems.append(f"there's already {whose} called '{data.get('name')}'")
        elif kind == "players":
            if not isinstance(data.get("name"), str) or not data["name"].strip():
                problems.append("the player needs a name")
            if data.get("colour") is not None and not _COLOUR.fullmatch(str(data["colour"])):
                problems.append("colour must look like #1c7ed6")
            if data.get("startTree") is not None and not isinstance(data["startTree"], str):
                problems.append("startTree must be a tree name")
            if data.get("created") is not None and not isinstance(data["created"], str):
                problems.append("created must be a date like 2026-10-03T09:30:00")
            if data.get("passwordHash") is not None and not isinstance(data["passwordHash"], str):
                problems.append("passwordHash must be a string")
            if not isinstance(data.get("admin", False), bool):
                problems.append("admin must be true or false")
            xp = data.get("xp", 0)
            if not isinstance(xp, int) or isinstance(xp, bool) or xp < 0:
                problems.append("xp must be a whole number of at least 0")
            if not isinstance(data.get("training", {}), dict):
                problems.append("training must be an object of completed tutorials")
        elif kind == "games":
            problems = check_game(data)
        elif kind == "results":
            problems = [] if isinstance(data.get("placements"), list) else ["a result needs its placements"]
        elif kind == "tutorials":
            from .training import check_tutorial
            problems = check_tutorial(data)
        elif kind == "seasons":
            from .seasons import check_season
            problems = check_season(data)
        if problems:
            raise CatalogueError(problems)

    # ---- trees and games -----------------------------------------------------------

    def trees_for(self, player_id: str | None) -> dict[str, dict[str, Any]]:
        """The trees a player can use, by name. The player's own trees hide defaults of the same name."""
        trees = self.list("trees")
        available = {t["name"]: t for t in trees if t.get("owner") is None and "error" not in t}
        if player_id is not None:
            available.update({t["name"]: t for t in trees
                              if t.get("owner") == player_id and "error" not in t})
        return available

    def new_game(self, map_id: str | dict[str, Any], teams: list[dict[str, Any]], seed: int,
                 name: str | None = None, created_by: str | None = None, mode: str = "sandbox",
                 extra: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        """Save a new game record. map_id is a map in the catalogue, or a map itself (such as a
        generated one). Each team request has slot, player, tree (a tree id), name, colour,
        speed, health and power. Everything but slot has a default: a team with a player and no
        tree starts with the player's startTree. created_by is the player who started the game,
        mode is one of GAME_MODES, and extra adds fields such as tutorialId."""
        if mode not in GAME_MODES:
            raise CatalogueError([f"mode must be one of {', '.join(GAME_MODES)}"])
        if isinstance(map_id, dict):
            map_data, map_id = map_id, None
        else:
            map_data = self.get("maps", map_id)
        if not isinstance(teams, list) or not teams:
            raise CatalogueError(["Choose at least one team"])
        built = [self._team(n, request) for n, request in enumerate(teams)]

        used = {t["slot"] for t in built}
        criteria = [c for c in map_data.get("criteria", []) if "slot" not in c or c["slot"] in used]
        if len(built) == 1:
            # With one team, "annihilate every other team" would be won on the first turn.
            criteria = [c for c in criteria if c.get("type") != "ANNIHILATE"]

        now = datetime.now()
        game = {
            "name": name or f"{map_data.get('name', map_id)} · {now:%d %b %H:%M}",
            "created": now.isoformat(timespec="seconds"),
            "mode": mode,
            "seed": seed,
            "mapId": map_id,
            "map": map_data,
            "teams": built,
            "criteria": criteria,
            "maxTurns": DEFAULT_MAX_TURNS,
            "rules": RULES_VERSION,
            "createdBy": created_by,
            # Everyone with a team, so each of them finds the game in their history.
            "participants": sorted({t["player"] for t in built if t["player"]}),
            **(extra or {}),
        }
        problems = check_game(game)
        if problems:
            raise CatalogueError(problems)
        game_id = f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
        self._write("games", game_id, game)
        return game_id, game

    def save_result(self, game_id: str, result: dict[str, Any]) -> None:
        """Save a finished game's result. A game only ever gets one."""
        if not self.exists("games", game_id):
            raise NotFound(f"No game called '{game_id}'")
        if self.exists("results", game_id):
            raise CatalogueError([f"Game '{game_id}' already has a result"])
        self._check("results", result, game_id)
        self._write("results", game_id, result)

    def result(self, game_id: str) -> dict[str, Any] | None:
        return self.get("results", game_id) if self.exists("results", game_id) else None

    def _team(self, n: int, request: Any) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise CatalogueError([f"Team {n + 1} must be an object"])
        player_id = request.get("player")
        player = None
        if player_id is not None:
            if not self.exists("players", player_id):
                raise CatalogueError([f"Team {n + 1}'s player '{player_id}' isn't in the catalogue"])
            player = self.get("players", player_id)

        if isinstance(request.get("trees"), list):
            # A team that brings its own trees, such as a tutorial's practice opponents.
            return self._team_with_trees(n, request, player_id, player)
        available = self.trees_for(player_id)
        if request.get("tree") is None and player and player.get("startTree") in available:
            start = available[player["startTree"]]
        else:
            start = next((t for t in available.values() if t["id"] == request.get("tree")), None)
        if start is None:
            whose = "the default trees" if player is None else f"{player['name']}'s trees or the defaults"
            raise CatalogueError([f"Team {n + 1}'s starting tree '{request.get('tree')}' isn't one of {whose}"])

        # Take the starting tree plus every tree it can reach with CHANGE_TREE.
        trees, queue = {}, [start]
        while queue:
            tree = queue.pop()
            if tree["name"] in trees:
                continue
            trees[tree["name"]] = {k: v for k, v in tree.items() if k != "id"}
            queue.extend(available[name] for name in tree_references(tree) if name in available)

        name = request.get("name")
        if not isinstance(name, str) or not name.strip():
            name = player["name"] if player else f"Team {n + 1}"
        team = {
            "slot": request.get("slot"),
            "name": name.strip(),
            "colour": request.get("colour") or (player or {}).get("colour"),
            "player": player_id,
            **{stat: value if request.get(stat) is None else request[stat]
               for stat, value in DEFAULT_STATS.items()},
            **({"startHealth": request["startHealth"]} if request.get("startHealth") is not None else {}),
            "startTree": start["name"],
            "trees": list(trees.values()),
        }
        return team

    def _team_with_trees(self, n: int, request: dict[str, Any], player_id: str | None,
                         player: dict[str, Any] | None) -> dict[str, Any]:
        name = request.get("name")
        if not isinstance(name, str) or not name.strip():
            name = player["name"] if player else f"Team {n + 1}"
        trees = [{k: v for k, v in t.items() if k != "id"} for t in request["trees"] if isinstance(t, dict)]
        return {
            "slot": request.get("slot"),
            "name": name.strip(),
            "colour": request.get("colour") or (player or {}).get("colour"),
            "player": player_id,
            **{stat: value if request.get(stat) is None else request[stat]
               for stat, value in DEFAULT_STATS.items()},
            **({"startHealth": request["startHealth"]} if request.get("startHealth") is not None else {}),
            "startTree": request.get("startTree") or (trees[0]["name"] if trees else None),
            "trees": trees,
        }

    def import_map(self, text: str, name: str, owner: str | None = None) -> dict[str, Any]:
        """Add a .map file's map, and its teams' trees owned by owner, to the catalogue.

        Tree names that are already taken get a number added, and references to them are
        updated. Raises MapFormatError or CatalogueError.
        """
        if owner is not None and not self.exists("players", owner):
            raise CatalogueError([f"The owner '{owner}' isn't a player in the catalogue"])
        data, teams = import_map_text(text, name)
        problems = check_map(data)
        if problems:
            raise CatalogueError(problems)

        taken = {t["name"] for t in self.list("trees") if t.get("owner") == owner}
        new_trees = []
        for team in teams:
            names = {}
            for tree in team["trees"]:
                new_name, n = tree["name"], 2
                while new_name in taken:
                    new_name, n = f"{tree['name']}-{n}", n + 1
                taken.add(new_name)
                names[tree["name"]] = new_name
            new_trees += [{**rename_trees(t, names), "owner": owner} for t in team["trees"]]

        map_id = self.create("maps", data)
        tree_ids = [self.create("trees", tree) for tree in new_trees]
        return {"map": map_id, "trees": tree_ids}


__all__ = ["Catalogue", "CatalogueError", "NotFound", "ScenarioError", "dumps", "slugify"]
