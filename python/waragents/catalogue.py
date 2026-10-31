"""The catalogue: maps, trees, players, games and the rest, stored in PostgreSQL.

The tables are described in db/migrations. Each kind of item still reads and writes as the JSON
object the web app and the game code use (scenario.py describes them), and its id is a readable
slug made from its name, which renaming the item later keeps.

A player is an account, and its id is the username:
{"name": "Matthew", "colour": "#1c7ed6", "created": "2026-10-03T09:30:00", "startTree": "graze",
 "xp": 350, "training": {"movement-1": {"completed": "...", "turns": 7}}, "passwordHash": "...",
 "admin": true}. passwordHash and admin are only there when they're set.
xp is their account XP, which sets their level and so their tree budget (progression.py).
startTree is their default tree: the one their teams start with unless another is chosen, and the
one that plays for them when someone else picks them as an opponent. Like CHANGE_TREE, it's looked
up in their own trees and then the defaults. passwordHash and admin are managed by web/auth.py.

A tree with an owner belongs to that player. A tree with no owner is a default tree, which every
player can use. When a team switches trees with CHANGE_TREE, it looks in its player's trees first,
then the defaults. Maps have an owner too (null for a system map) and can be published, which
lets every player use them.

A game's result is saved once the game is over: who placed where and the XP each player got for
it (battles.py). It's kept apart from the game record because the record is what replays the
game, and must never change.

Changes that read a value and write it back (account XP, ratings, tutorial progress) are done in
single statements or under row locks, so any number of servers can share one database. Use
atomic() to make several changes commit together.
"""

from __future__ import annotations

import re
import secrets
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Any

from psycopg import errors

from .db import Database, Jsonb
from .progression import DEFAULT_MAX_TURNS, band_label, level_summary
from .scenario import (RULES_VERSION, ScenarioError, check_game, check_map, check_tree,
                       import_map_text, map_size, rename_trees, tree_references)

KINDS = ("maps", "trees", "players", "games", "results", "tutorials", "seasons")
GAME_MODES = ("sandbox", "training", "skirmish", "season")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
_COLOUR = re.compile(r"#[0-9a-fA-F]{6}")
DEFAULT_STATS = {"speed": 10, "health": 100, "power": 10}

_KEY = {kind: "game_id" if kind == "results" else "id" for kind in KINDS}
# Fields of a game record that have columns of their own. Anything else is kept in games.extra.
_GAME_FIELDS = {"name", "created", "mode", "seed", "mapId", "map", "teams", "criteria", "maxTurns",
                "rules", "createdBy", "participants", "seasonId", "tutorialId"}
_TUTORIAL_FIELDS = {"name", "track", "order", "level", "maxTurns"}


class NotFound(LookupError):
    pass


class CatalogueError(ValueError):
    """A save or delete that was refused. problems lists the reasons."""

    def __init__(self, problems: list):
        self.problems = [str(p) for p in problems]
        super().__init__("; ".join(self.problems[:5]))


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def iso(moment: datetime | None) -> str | None:
    """A time as the app shows it: local time to the second, like 2026-10-03T09:30:00."""
    return None if moment is None else moment.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")


def _moment(text: Any, field: str) -> datetime | None:
    if text is None:
        return None
    try:
        moment = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise CatalogueError([f"{field} must be a date like 2026-10-03T09:30:00"]) from None
    return moment if moment.tzinfo else moment.astimezone()


def _jsonb(value: Any) -> Jsonb | None:
    return None if value is None else Jsonb(value)


class Catalogue:
    def __init__(self, db: Database):
        self.db = db

    def atomic(self) -> AbstractContextManager:
        """Everything done inside `with catalogue.atomic():` commits together, or not at all."""
        return self.db.transaction()

    # ---- reading -------------------------------------------------------------------

    def _check_id(self, kind: str, item_id: Any) -> None:
        if kind not in KINDS:
            raise NotFound(f"There's no '{kind}' in the catalogue")
        if not isinstance(item_id, str) or not _ID.fullmatch(item_id):
            raise NotFound(f"No {kind[:-1]} called '{item_id}'")

    def exists(self, kind: str, item_id: str) -> bool:
        try:
            self._check_id(kind, item_id)
        except NotFound:
            return False
        return self.db.value(f"select exists(select 1 from {kind} where {_KEY[kind]} = %s)", (item_id,))

    def list(self, kind: str, viewer: str | None = None) -> list[dict[str, Any]]:
        """Every item of a kind, each with its "id", in id order. With a viewer, maps and trees
        are cut down to the ones that player could read: their own, the system maps and default
        trees, and published maps."""
        if kind not in KINDS:
            raise NotFound(f"There's no '{kind}' in the catalogue")
        if viewer is not None and kind == "trees":
            return self._load(kind, "owner_id is null or owner_id = %s", (viewer,))
        if viewer is not None and kind == "maps":
            return self._load(kind, "owner_id is null or owner_id = %s or published", (viewer,))
        return self._load(kind)

    def get(self, kind: str, item_id: str) -> dict[str, Any]:
        self._check_id(kind, item_id)
        found = self._load(kind, f"{'r.' if kind == 'results' else ''}{_KEY[kind]} = %s", (item_id,))
        if not found:
            raise NotFound(f"No {kind[:-1]} called '{item_id}'")
        return {k: v for k, v in found[0].items() if k != "id"}

    def count(self, kind: str) -> int:
        if kind not in KINDS:
            raise NotFound(f"There's no '{kind}' in the catalogue")
        return self.db.value(f"select count(*) from {kind}")

    def _load(self, kind: str, where: str = "true", params: Any = ()) -> list[dict[str, Any]]:
        return getattr(self, f"_load_{kind}")(where, params)

    def _load_maps(self, where: str, params: Any) -> list[dict[str, Any]]:
        rows = self.db.query(f"select * from maps where {where} order by id collate \"C\"", params)
        return [{"id": r["id"], "name": r["name"], "owner": r["owner_id"], "published": r["published"],
                 "mode": r["mode"], "maxAgents": r["max_agents"], **r["layout"], "criteria": r["criteria"]}
                for r in rows]

    def _load_trees(self, where: str, params: Any) -> list[dict[str, Any]]:
        rows = self.db.query(f"select id, name, owner_id, root from trees where {where} "
                             "order by id collate \"C\"", params)
        return [{"id": r["id"], "name": r["name"], "owner": r["owner_id"], "root": r["root"]} for r in rows]

    def _load_players(self, where: str, params: Any) -> list[dict[str, Any]]:
        rows = self.db.query(f"""
            select p.*, c.password_hash from players p left join credentials c on c.player_id = p.id
            where {where} order by p.id collate "C" """, params)
        training: dict[str, dict[str, Any]] = {r["id"]: {} for r in rows}
        for r in self.db.query("""select * from tutorial_progress where player_id = any(%s)
                                  order by completed_at, tutorial_id""", ([r["id"] for r in rows],)):
            training[r["player_id"]][r["tutorial_id"]] = {"completed": iso(r["completed_at"]),
                                                          "turns": r["best_turns"]}
        return [{"id": r["id"], "name": r["name"], "colour": r["colour"], "startTree": r["start_tree"],
                 "created": iso(r["created_at"]), "xp": r["xp"], "training": training[r["id"]],
                 **({"passwordHash": r["password_hash"]} if r["password_hash"] else {}),
                 **({"admin": True} if r["is_admin"] else {})} for r in rows]

    def _load_tutorials(self, where: str, params: Any) -> list[dict[str, Any]]:
        rows = self.db.query(f"select * from tutorials where {where} order by id collate \"C\"", params)
        return [{"id": r["id"], "name": r["name"], "track": r["track"], "order": r["position"],
                 "level": r["level"], "maxTurns": r["max_turns"], **r["content"]} for r in rows]

    def _load_seasons(self, where: str, params: Any) -> list[dict[str, Any]]:
        rows = self.db.query(f"select * from seasons where {where} order by id collate \"C\"", params)
        ids = [r["id"] for r in rows]
        ratings: dict[str, dict[str, Any]] = {i: {} for i in ids}
        for r in self.db.query("select * from season_ratings where season_id = any(%s) "
                               "order by season_id, player_id", (ids,)):
            ratings[r["season_id"]][r["player_id"]] = {"rating": r["rating"], "games": r["games"],
                                                       "wins": r["wins"]}
        standings: dict[str, list[dict[str, Any]]] = {i: [] for i in ids}
        for r in self.db.query("""
                select s.*, p.name, p.colour from season_standings s join players p on p.id = s.player_id
                where s.season_id = any(%s) order by s.season_id, s.band, s.band_rank nulls last, s.rank
                """, (ids,)):
            bands = standings[r["season_id"]]
            if not bands or bands[-1]["band"] != r["band"]:
                bands.append({"band": r["band"], "label": band_label(r["band"]), "players": []})
            entry = {"player": r["player_id"], "name": r["name"], "colour": r["colour"], "level": r["level"],
                     "band": r["band"], "rating": r["rating"], "games": r["games"], "wins": r["wins"],
                     "rank": r["rank"], "bandRank": r["band_rank"], "reward": r["reward"]}
            if r["xp_before"] is not None:
                entry["before"] = level_summary(r["xp_before"])
                entry["after"] = level_summary(r["xp_before"] + r["reward"])
            bands[-1]["players"].append(entry)
        return [{"id": r["id"], "name": r["name"], "status": r["status"], "started": iso(r["started_at"]),
                 "ended": iso(r["ended_at"]), "ratings": ratings[r["id"]],
                 "standings": None if r["status"] == "open" else standings[r["id"]]} for r in rows]

    def _load_games(self, where: str, params: Any) -> list[dict[str, Any]]:
        rows = self.db.query(f"select * from games where {where} order by id collate \"C\"", params)
        teams = self._teams([r["id"] for r in rows])
        games = []
        for r in rows:
            built = teams.get(r["id"], [])
            games.append({
                "id": r["id"], "name": r["name"], "created": iso(r["created_at"]), "mode": r["mode"],
                "seed": r["seed"], "mapId": r["map_id"], "map": r["map"], "teams": built,
                "criteria": r["criteria"], "maxTurns": r["max_turns"], "rules": r["rules"],
                "createdBy": r["created_by"],
                "participants": sorted({t["player"] for t in built if t["player"]}),
                **({"seasonId": r["season_id"]} if r["season_id"] else {}),
                **({"tutorialId": r["tutorial_id"]} if r["tutorial_id"] else {}),
                **r["extra"],
            })
        return games

    def _teams(self, game_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        teams: dict[str, list[dict[str, Any]]] = {}
        for t in self.db.query("select * from game_teams where game_id = any(%s) order by game_id, position",
                               (game_ids,)):
            teams.setdefault(t["game_id"], []).append({
                "slot": t["slot"], "name": t["name"], "colour": t["colour"], "player": t["player_id"],
                "speed": t["speed"], "health": t["health"], "power": t["power"],
                **({"startHealth": t["start_health"]} if t["start_health"] is not None else {}),
                "startTree": t["start_tree"], "trees": t["trees"],
            })
        return teams

    def _load_results(self, where: str, params: Any) -> list[dict[str, Any]]:
        rows = self.db.query(f"""
            select r.*, g.mode, g.name, g.map ->> 'name' as map_name, g.created_at
            from results r join games g on g.id = r.game_id
            where {where} order by r.game_id collate "C" """, params)
        ids = [r["game_id"] for r in rows]
        placements: dict[str, list] = {i: [] for i in ids}
        for p in self.db.query("""
                select p.*, t.name, t.player_id, t.colour from placements p
                join game_teams t on t.game_id = p.game_id and t.slot = p.slot
                where p.game_id = any(%s) order by p.game_id, p.position""", (ids,)):
            placements[p["game_id"]].append({
                "slot": p["slot"], "name": p["name"], "place": p["place"], "alive": p["alive"],
                "agents": p["agents"], "exp": p["exp"], "eliminated": p["eliminated"],
                "player": p["player_id"], "colour": p["colour"]})
        rewards: dict[str, dict] = {i: {} for i in ids}
        # In the order of the players' best placements, as they were given out.
        for w in self.db.query("""
                select w.* from rewards w where w.game_id = any(%s)
                order by w.game_id, (select min(p.position) from placements p join game_teams t using (game_id, slot)
                                     where p.game_id = w.game_id and t.player_id = w.player_id) nulls last,
                         w.player_id""", (ids,)):
            rewards[w["game_id"]][w["player_id"]] = {
                "agentXp": w["agent_xp"], "fromAgents": w["from_agents"], "bonus": w["bonus"],
                "total": w["total"], "before": level_summary(w["xp_before"]),
                "after": level_summary(w["xp_after"]),
                **({"rating": {"before": w["rating_before"], "after": w["rating_after"]}}
                   if w["rating_before"] is not None else {})}
        seen: dict[str, list[str]] = {i: [] for i in ids}
        for v in self.db.query("select * from result_views where game_id = any(%s) order by game_id, seen_at, player_id",
                               (ids,)):
            seen[v["game_id"]].append(v["player_id"])
        return [{"id": r["game_id"], "gameId": r["game_id"], "mode": r["mode"], "name": r["name"],
                 "mapName": r["map_name"], "created": iso(r["created_at"]), "finished": iso(r["finished_at"]),
                 "reason": r["reason"], "outcome": r["outcome"], "turns": r["turns"],
                 "winners": list(r["winners"]), "placements": placements[r["game_id"]],
                 "rewards": rewards[r["game_id"]], "seenBy": seen[r["game_id"]]} for r in rows]

    # ---- checked changes -----------------------------------------------------------

    def new_id(self, kind: str, name: str) -> str:
        base = slugify(name) or kind[:-1]
        taken = {r["id"] for r in self.db.query(
            f"select {_KEY[kind]} as id from {kind} where {_KEY[kind]} = %s or {_KEY[kind]} like %s",
            (base, base + "-%"))}
        item_id, n = base, 2
        while item_id in taken:
            item_id, n = f"{base}-{n}", n + 1
        return item_id

    def create(self, kind: str, data: dict[str, Any]) -> str:
        """Save a new item with an id made from its name. Returns the id."""
        return self.create_with_id(kind, None, data)

    def create_with_id(self, kind: str, item_id: str | None, data: dict[str, Any]) -> str:
        """Save a new item as item_id (or an id made from its name), which mustn't be taken."""
        if kind in ("games", "results"):
            raise CatalogueError(["Games and their results are saved by playing a game"])
        self._check(kind, data, None)
        if kind == "players" and not data.get("created"):
            data = {**data, "created": iso(datetime.now().astimezone())}
        if item_id is not None:
            self._check_id(kind, item_id)
        for _ in range(5):
            chosen = item_id or self.new_id(kind, str(data.get("name", "")))
            try:
                with self.atomic():
                    self._save(kind, chosen, data, new=True)
                return chosen
            except errors.UniqueViolation as e:
                if e.diag.constraint_name != f"{kind}_pkey":
                    raise self._clash(kind, data) from e
                if item_id is not None:
                    raise CatalogueError([f"There's already a {kind[:-1]} called '{item_id}'"]) from e
                # Someone else took the id we picked a moment ago: pick again.
        raise CatalogueError([f"Couldn't find a free id for the {kind[:-1]}. Try again."])

    def update(self, kind: str, item_id: str, data: dict[str, Any]) -> None:
        """Replace an item with data."""
        if not self.exists(kind, item_id):
            raise NotFound(f"No {kind[:-1]} called '{item_id}'")
        self._check(kind, data, item_id)
        try:
            with self.atomic():
                self._save(kind, item_id, data, new=False)
        except errors.UniqueViolation as e:
            raise self._clash(kind, data) from e

    def delete(self, kind: str, item_id: str) -> None:
        if not self.exists(kind, item_id):
            raise NotFound(f"No {kind[:-1]} called '{item_id}'")
        if kind == "players":
            for owned in ("trees", "maps"):
                names = [r["name"] for r in self.db.query(
                    f"select name from {owned} where owner_id = %s order by name", (item_id,))]
                if names:
                    raise CatalogueError([f"This player still owns {len(names)} {owned[:-1]}(s): "
                                          f"{', '.join(names)}. Delete or move them first."])
        self.db.execute(f"delete from {kind} where {_KEY[kind]} = %s", (item_id,))

    def _clash(self, kind: str, data: dict[str, Any]) -> CatalogueError:
        if kind == "trees":
            owner = data.get("owner")
            whose = "a default tree" if owner is None else f"a tree of {owner}'s"
            return CatalogueError([f"there's already {whose} called '{data.get('name')}'"])
        if kind == "seasons":
            return CatalogueError(["A season is already running. End it first."])
        return CatalogueError([f"That {kind[:-1]} clashes with one that's already saved"])

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
            clash = self.db.value("select id from trees where owner_id is not distinct from %s and name = %s "
                                  "and id is distinct from %s", (owner, data.get("name"), item_id))
            if clash:
                problems.append(self._clash("trees", data).problems[0])
        elif kind == "players":
            if not isinstance(data.get("name"), str) or not data["name"].strip():
                problems.append("the player needs a name")
            if data.get("colour") is not None and not _COLOUR.fullmatch(str(data["colour"])):
                problems.append("colour must look like #1c7ed6")
            if data.get("startTree") is not None and not isinstance(data["startTree"], str):
                problems.append("startTree must be a tree name")
            if data.get("created") is not None:
                try:
                    _moment(data["created"], "created")
                except CatalogueError as e:
                    problems += e.problems
            if data.get("passwordHash") is not None and not isinstance(data["passwordHash"], str):
                problems.append("passwordHash must be a string")
            if not isinstance(data.get("admin", False), bool):
                problems.append("admin must be true or false")
            xp = data.get("xp", 0)
            if not isinstance(xp, int) or isinstance(xp, bool) or xp < 0:
                problems.append("xp must be a whole number of at least 0")
            training = data.get("training") or {}
            if not isinstance(training, dict):
                problems.append("training must be an object of completed tutorials")
            else:
                unknown = sorted(t for t in training if not self.exists("tutorials", t))
                if unknown:
                    problems.append(f"there's no tutorial called {', '.join(repr(t) for t in unknown)}")
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

    # ---- writing each kind ---------------------------------------------------------

    def _save(self, kind: str, item_id: str, data: dict[str, Any], new: bool) -> None:
        getattr(self, f"_save_{kind}")(item_id, data, new)

    def _upsert(self, table: str, row: dict[str, Any], new: bool, key: str = "id") -> None:
        """Insert a row, or update the one with the same key (setting updated_at if it has one)."""
        columns = list(row)
        if new:
            self.db.execute(f"insert into {table} ({', '.join(columns)}) "
                            f"values ({', '.join(f'%({c})s' for c in columns)})", row)
            return
        sets = [f"{c} = %({c})s" for c in columns if c != key]
        if table in ("maps", "trees"):
            sets.append("updated_at = now()")
        self.db.execute(f"update {table} set {', '.join(sets)} where {key} = %({key})s", row)

    def _save_maps(self, item_id: str, data: dict[str, Any], new: bool) -> None:
        width, height = map_size(data)
        self._upsert("maps", {
            "id": item_id, "name": data["name"], "owner_id": data.get("owner"),
            "published": data.get("published", False), "mode": data["mode"], "max_agents": data["maxAgents"],
            "width": width, "height": height,
            "layout": Jsonb({k: data.get(k) or [] for k in ("dirt", "food", "plants", "starts")}),
            "criteria": Jsonb(data.get("criteria") or []),
        }, new)

    def _save_trees(self, item_id: str, data: dict[str, Any], new: bool) -> None:
        self._upsert("trees", {"id": item_id, "name": data["name"], "owner_id": data.get("owner"),
                               "root": _jsonb(data.get("root"))}, new)

    def _save_players(self, item_id: str, data: dict[str, Any], new: bool) -> None:
        row = {"id": item_id, "name": data["name"], "colour": data.get("colour"),
               "start_tree": data.get("startTree"), "xp": data.get("xp") or 0,
               "is_admin": bool(data.get("admin"))}
        if data.get("created") or new:
            row["created_at"] = _moment(data.get("created"), "created") or datetime.now().astimezone()
        self._upsert("players", row, new)
        if data.get("passwordHash"):
            self.db.execute("""insert into credentials (player_id, password_hash) values (%s, %s)
                               on conflict (player_id) do update set password_hash = excluded.password_hash,
                               updated_at = now() where credentials.password_hash <> excluded.password_hash""",
                            (item_id, data["passwordHash"]))
        else:
            self.db.execute("delete from credentials where player_id = %s", (item_id,))
        self.db.execute("delete from tutorial_progress where player_id = %s", (item_id,))
        for tutorial_id, done in (data.get("training") or {}).items():
            done = done if isinstance(done, dict) else {}
            self.db.execute("""insert into tutorial_progress (player_id, tutorial_id, completed_at, best_turns)
                               values (%s, %s, coalesce(%s, now()), %s)""",
                            (item_id, tutorial_id, _moment(done.get("completed"), "completed"),
                             done.get("turns") or 0))

    def _save_tutorials(self, item_id: str, data: dict[str, Any], new: bool) -> None:
        self._upsert("tutorials", {
            "id": item_id, "name": data["name"], "track": data["track"], "position": data["order"],
            "level": data["level"], "max_turns": data["maxTurns"],
            "content": Jsonb({k: v for k, v in data.items() if k not in _TUTORIAL_FIELDS and k != "id"}),
        }, new)

    def _save_seasons(self, item_id: str, data: dict[str, Any], new: bool) -> None:
        row = {"id": item_id, "name": data["name"], "status": data["status"],
               "ended_at": _moment(data.get("ended"), "ended")}
        if data.get("started") or new:
            row["started_at"] = _moment(data.get("started"), "started") or datetime.now().astimezone()
        self._upsert("seasons", row, new)
        self.db.execute("delete from season_ratings where season_id = %s", (item_id,))
        for player_id, entry in (data.get("ratings") or {}).items():
            self.save_rating(item_id, player_id, entry)
        self.db.execute("delete from season_standings where season_id = %s", (item_id,))
        for band in data.get("standings") or []:
            for entry in band.get("players", []):
                self._save_standing(item_id, entry)

    def _save_standing(self, season_id: str, entry: dict[str, Any]) -> None:
        self.db.execute("""
            insert into season_standings (season_id, player_id, band, rank, band_rank, level, rating,
                                          games, wins, reward, xp_before)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (season_id, entry["player"], entry["band"], entry["rank"], entry.get("bandRank"),
             entry["level"], entry["rating"], entry["games"], entry["wins"], entry.get("reward") or 0,
             (entry.get("before") or {}).get("xp")))

    def _save_games(self, item_id: str, data: dict[str, Any], new: bool,
                    tree_ids: dict[int, str | None] | None = None, started: datetime | None = None) -> None:
        """started, if given, is the exact time the game started. The record's "created" is only
        to the second, which isn't enough to put games started close together in order."""
        self._upsert("games", {
            "id": item_id, "name": data["name"], "mode": data.get("mode", "sandbox"), "seed": data["seed"],
            "rules": data.get("rules"), "max_turns": data.get("maxTurns"),
            "created_at": started or _moment(data.get("created"), "created") or datetime.now().astimezone(),
            "created_by": data.get("createdBy"), "map_id": data.get("mapId"),
            "season_id": data.get("seasonId"), "tutorial_id": data.get("tutorialId"),
            "map": Jsonb(data["map"]), "criteria": Jsonb(data.get("criteria") or []),
            "extra": Jsonb({k: v for k, v in data.items() if k not in _GAME_FIELDS and k != "id"}),
        }, new)
        slots = [team["slot"] for team in data["teams"]]
        self.db.execute("delete from game_teams where game_id = %s and slot <> all(%s)", (item_id, slots))
        for position, team in enumerate(data["teams"]):
            self.db.execute("""
                insert into game_teams (game_id, slot, position, name, colour, player_id, speed, health,
                                        power, start_health, start_tree, tree_id, trees)
                values (%(game)s, %(slot)s, %(position)s, %(name)s, %(colour)s, %(player)s, %(speed)s,
                        %(health)s, %(power)s, %(start_health)s, %(start_tree)s, %(tree_id)s, %(trees)s)
                on conflict (game_id, slot) do update set
                    position = excluded.position, name = excluded.name, colour = excluded.colour,
                    player_id = excluded.player_id, speed = excluded.speed, health = excluded.health,
                    power = excluded.power, start_health = excluded.start_health,
                    start_tree = excluded.start_tree, trees = excluded.trees""",
                {"game": item_id, "slot": team["slot"], "position": position, "name": team["name"],
                 "colour": team.get("colour"), "player": team.get("player"), "speed": team["speed"],
                 "health": team["health"], "power": team["power"], "start_health": team.get("startHealth"),
                 "start_tree": team["startTree"], "tree_id": (tree_ids or {}).get(position),
                 "trees": Jsonb(team["trees"])})

    def _save_results(self, game_id: str, data: dict[str, Any], new: bool) -> None:
        if not new:
            self.db.execute("delete from results where game_id = %s", (game_id,))
        self.db.execute("""insert into results (game_id, reason, outcome, turns, winners, finished_at)
                           values (%s, %s, %s, %s, %s, coalesce(%s, now()))""",
                        (game_id, data.get("reason") or "", data.get("outcome") or "", data.get("turns") or 0,
                         list(data.get("winners") or []), _moment(data.get("finished"), "finished")))
        for position, p in enumerate(data["placements"]):
            self.db.execute("""
                insert into placements (game_id, slot, position, place, alive, agents, exp, eliminated)
                values (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (game_id, p["slot"], position, p["place"], p.get("alive", 0), p.get("agents", 0),
                 p.get("exp", 0), p.get("eliminated")))
        for player_id, w in (data.get("rewards") or {}).items():
            rating = w.get("rating") or {}
            self.db.execute("""
                insert into rewards (game_id, player_id, agent_xp, from_agents, bonus, total, xp_before,
                                     xp_after, rating_before, rating_after)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (game_id, player_id, w.get("agentXp", 0), w.get("fromAgents", 0), w.get("bonus", 0),
                 w.get("total", 0), w["before"]["xp"], w["after"]["xp"], rating.get("before"),
                 rating.get("after")))
        for player_id in data.get("seenBy") or []:
            self.mark_seen(game_id, player_id)

    # ---- players -------------------------------------------------------------------

    def any_admin(self) -> bool:
        return self.db.value("select exists(select 1 from players where is_admin)")

    def update_player(self, player_id: str, changes: dict[str, Any]) -> None:
        """Change some of a player's fields, leaving the rest (such as their XP) as they are."""
        with self.atomic():
            if not self.db.one("select id from players where id = %s for update", (player_id,)):
                raise NotFound(f"No player called '{player_id}'")
            self._check("players", {**self.get("players", player_id), **changes}, player_id)
            columns = {"name": "name", "colour": "colour", "startTree": "start_tree", "admin": "is_admin"}
            sets = {columns[k]: (bool(v) if k == "admin" else v) for k, v in changes.items() if k in columns}
            if sets:
                self.db.execute(f"update players set {', '.join(f'{c} = %({c})s' for c in sets)} "
                                "where id = %(id)s", {**sets, "id": player_id})
            if "passwordHash" in changes:
                self.db.execute("""insert into credentials (player_id, password_hash) values (%s, %s)
                                   on conflict (player_id) do update set password_hash = excluded.password_hash,
                                   updated_at = now()""", (player_id, changes["passwordHash"]))

    def add_xp(self, player_id: str, amount: int) -> tuple[int, int] | None:
        """Add account XP to a player in one step. Returns their XP (before, after), or None if
        there's no such player."""
        after = self.db.value("update players set xp = xp + %s where id = %s returning xp", (amount, player_id))
        return None if after is None else (after - amount, after)

    def complete_tutorial(self, player_id: str, tutorial_id: str, turns: int) -> bool:
        """Note that a player completed a tutorial, keeping their best number of turns. Returns
        True if it's the first time they have."""
        return self.db.value("""
            insert into tutorial_progress (player_id, tutorial_id, best_turns) values (%s, %s, %s)
            on conflict (player_id, tutorial_id)
                do update set best_turns = least(tutorial_progress.best_turns, excluded.best_turns)
            returning xmax = 0""", (player_id, tutorial_id, turns))

    # ---- friends -------------------------------------------------------------------

    def friendship(self, player_id: str, other_id: str) -> str:
        """How two players stand: "friends", "sent" (player asked other and is waiting),
        "received" (other asked player), or "none"."""
        row = self.db.one("""
            select requester_id, status from friendships
            where (requester_id, addressee_id) in ((%(a)s, %(b)s), (%(b)s, %(a)s))""", {"a": player_id, "b": other_id})
        if row is None:
            return "none"
        if row["status"] == "accepted":
            return "friends"
        return "sent" if row["requester_id"] == player_id else "received"

    def ask_friend(self, player_id: str, other_id: str) -> str:
        """Ask another player to be friends. If they've already asked, that makes the two of you
        friends. Returns how you stand afterwards (see friendship)."""
        if player_id == other_id:
            raise CatalogueError(["You can't add yourself as a friend"])
        if not self.exists("players", other_id):
            raise NotFound(f"There's no player called '{other_id}'")
        with self.atomic():
            accepted = self.db.execute("""
                update friendships set status = 'accepted', accepted_at = now()
                where requester_id = %s and addressee_id = %s and status = 'pending'""", (other_id, player_id))
            if not accepted:
                self.db.execute("""insert into friendships (requester_id, addressee_id, status) values (%s, %s, 'pending')
                                   on conflict do nothing""", (player_id, other_id))
        return self.friendship(player_id, other_id)

    def accept_friend(self, player_id: str, other_id: str) -> bool:
        """Accept another player's request. Returns False if there wasn't one."""
        return self.db.execute("""
            update friendships set status = 'accepted', accepted_at = now()
            where requester_id = %s and addressee_id = %s and status = 'pending'""", (other_id, player_id)) == 1

    def remove_friend(self, player_id: str, other_id: str) -> bool:
        """Decline or withdraw a request, or stop being friends. Returns False if there was nothing to remove."""
        return self.db.execute("""
            delete from friendships
            where (requester_id, addressee_id) in ((%(a)s, %(b)s), (%(b)s, %(a)s))""", {"a": player_id, "b": other_id}) == 1

    def friends(self, player_id: str) -> dict[str, list[dict[str, Any]]]:
        """A player's friends, the requests waiting for their answer ("received") and the ones
        they're waiting on ("sent"), each with the other player's public details, by name."""
        rows = self.db.query("""
            select p.id, p.name, p.colour, p.xp, p.start_tree, f.status, f.requested_at, f.accepted_at,
                   f.requester_id = %(me)s as asked
            from friendships f
            join players p on p.id = case when f.requester_id = %(me)s then f.addressee_id else f.requester_id end
            where %(me)s in (f.requester_id, f.addressee_id)
            order by lower(p.name), p.id""", {"me": player_id})
        out: dict[str, list[dict[str, Any]]] = {"friends": [], "received": [], "sent": []}
        for r in rows:
            kind = "friends" if r["status"] == "accepted" else "sent" if r["asked"] else "received"
            out[kind].append({"id": r["id"], "name": r["name"], "colour": r["colour"], "xp": r["xp"],
                              "startTree": r["start_tree"], "requested": iso(r["requested_at"]),
                              "since": iso(r["accepted_at"])})
        return out

    def friend_requests(self, player_id: str) -> int:
        """How many requests are waiting for this player's answer."""
        return self.db.value("select count(*) from friendships where addressee_id = %s and status = 'pending'",
                             (player_id,))

    def secret(self, name: str) -> str:
        """A random value made the first time it's asked for and the same ever after, for every
        server sharing the database."""
        self.db.execute("insert into settings (key, value) values (%s, %s) on conflict do nothing",
                        (name, secrets.token_hex(32)))
        return self.db.value("select value from settings where key = %s", (name,))

    # ---- trees and games -----------------------------------------------------------

    def trees_for(self, player_id: str | None) -> dict[str, dict[str, Any]]:
        """The trees a player can use, by name. The player's own trees hide defaults of the same name."""
        trees = self._load_trees("owner_id is null or owner_id = %s", (player_id,))
        available = {t["name"]: t for t in trees if t["owner"] is None}
        available.update({t["name"]: t for t in trees if t["owner"] is not None})
        return available

    def find_tree(self, owner: str | None, name: str) -> dict[str, Any] | None:
        """The tree an owner (None for the default trees) has with this name, with its id."""
        found = self._load_trees("owner_id is not distinct from %s and name = %s", (owner, name))
        return found[0] if found else None

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
            map_data = {k: v for k, v in self.get("maps", map_id).items() if k not in ("owner", "published")}
        if not isinstance(teams, list) or not teams:
            raise CatalogueError(["Choose at least one team"])
        built = [self._team(n, request) for n, request in enumerate(teams)]

        used = {t["slot"] for t, _ in built}
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
            "teams": [team for team, _ in built],
            "criteria": criteria,
            "maxTurns": DEFAULT_MAX_TURNS,
            "rules": RULES_VERSION,
            "createdBy": created_by,
            # Everyone with a team, so each of them finds the game in their history.
            "participants": sorted({t["player"] for t, _ in built if t["player"]}),
            **(extra or {}),
        }
        problems = check_game(game)
        if problems:
            raise CatalogueError(problems)
        tree_ids = {n: tree_id for n, (_, tree_id) in enumerate(built)}
        for _ in range(5):
            game_id = f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
            try:
                with self.atomic():
                    self._save_games(game_id, game, new=True, tree_ids=tree_ids, started=now.astimezone())
                return game_id, game
            except errors.UniqueViolation:
                continue  # two games started in the same second drew the same id
        raise CatalogueError(["Couldn't find a free id for the game. Try again."])

    def import_game(self, game_id: str, game: dict[str, Any]) -> None:
        """Save a game record made elsewhere (such as a JSON catalogue) under its own id."""
        self._check_id("games", game_id)
        self._check("games", game, None)
        with self.atomic():
            self._save_games(game_id, game, new=True)
            self.link_trees(game_id)

    def link_trees(self, game_id: str) -> None:
        """For a game that didn't record which catalogue tree each team started with (one from a
        JSON catalogue), find it by name: the team's player's own tree, or else a default tree."""
        self.db.execute("""
            update game_teams t set tree_id = coalesce(
                (select id from trees where owner_id = t.player_id and name = t.start_tree),
                (select id from trees where owner_id is null and name = t.start_tree))
            where t.game_id = %s and t.tree_id is null and t.player_id is not null""", (game_id,))

    def save_result(self, game_id: str, result: dict[str, Any]) -> None:
        """Save a finished game's result. A game only ever gets one."""
        if not self.exists("games", game_id):
            raise NotFound(f"No game called '{game_id}'")
        self._check("results", result, game_id)
        try:
            with self.atomic():
                self._save_results(game_id, result, new=True)
        except errors.UniqueViolation as e:
            raise CatalogueError([f"Game '{game_id}' already has a result"]) from e

    def save_stats(self, game_id: str, players: list) -> None:
        """Save (or replace) what each team did in a finished game: the stats.TeamStats of each
        of the world's players, matched to the game's teams by slot."""
        from .stats import STATS_VERSION

        with self.atomic():
            self.db.execute("delete from team_stats where game_id = %s", (game_id,))
            for player in players:
                s = player.stats
                self.db.execute("""
                    insert into team_stats (game_id, slot, stats_version, kills, deaths, births,
                        damage_dealt, damage_taken, blocks, food_eaten, confused, peak_agents, agents, health)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (game_id, player.slot, STATS_VERSION, s.kills, s.deaths, s.births, s.damage_dealt,
                     s.damage_taken, s.blocks, s.food_eaten, s.confused, max(s.agents, default=0),
                     s.agents, s.health))
                actions = sorted(set(s.succeeded) | set(s.failed))
                with self.db.transaction() as conn:
                    with conn.cursor() as cur:
                        cur.executemany("""insert into team_actions (game_id, slot, action, succeeded, failed)
                                           values (%s, %s, %s, %s, %s)""",
                                        [(game_id, player.slot, a, s.succeeded[a], s.failed[a]) for a in actions])
                        cur.executemany("""
                            insert into team_node_visits (game_id, slot, tree_name, node_id, visits, confused)
                            values (%s, %s, %s, %s, %s, %s)""",
                            [(game_id, player.slot, tree, node, count, s.confused_at.get(tree, {}).get(node, 0))
                             for tree, nodes in s.visits.items() for node, count in sorted(nodes.items())])

    def result(self, game_id: str) -> dict[str, Any] | None:
        return self.get("results", game_id) if self.exists("results", game_id) else None

    def mark_seen(self, game_id: str, player_id: str) -> None:
        self.db.execute("insert into result_views (game_id, player_id) values (%s, %s) on conflict do nothing",
                        (game_id, player_id))

    def game_summaries(self, player_id: str | None = None) -> list[dict[str, Any]]:
        """Games, newest first, cut down for a list: all of them, or with a player_id just the
        ones that player started or had a team in."""
        where, params = "true", {}
        if player_id is not None:
            where = ("g.created_by = %(me)s or exists (select 1 from game_teams t "
                     "where t.game_id = g.id and t.player_id = %(me)s)")
            params = {"me": player_id}
        rows = self.db.query(f"""
            select g.id, g.name, g.created_at, g.seed, g.map_id, g.map ->> 'name' as map_name
            from games g where {where} order by g.created_at desc, g.id collate "C" """, params)
        teams = self._team_summaries([r["id"] for r in rows])
        return [{"id": r["id"], "name": r["name"], "created": iso(r["created_at"]), "seed": r["seed"],
                 "mapId": r["map_id"], "mapName": r["map_name"],
                 "teams": [{k: t[k] for k in ("name", "colour", "slot", "player", "startTree")}
                           for t in teams.get(r["id"], [])]} for r in rows]

    def _team_summaries(self, game_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        teams: dict[str, list[dict[str, Any]]] = {}
        for t in self.db.query("""select game_id, name, colour, slot, player_id, start_tree from game_teams
                                  where game_id = any(%s) order by game_id, position""", (game_ids,)):
            teams.setdefault(t["game_id"], []).append({
                "name": t["name"], "colour": t["colour"], "slot": t["slot"], "player": t["player_id"],
                "startTree": t["start_tree"]})
        return teams

    def history(self, player_id: str) -> list[dict[str, Any]]:
        """Every game a player started or had a team in, newest first, with how they did."""
        rows = self.db.query("""
            select g.id, g.name, g.mode, g.created_at, g.map ->> 'name' as map_name, g.created_by,
                   r.game_id is not null as finished, r.outcome, r.winners,
                   (select p.place from placements p join game_teams t using (game_id, slot)
                    where p.game_id = g.id and t.player_id = %(me)s order by p.position limit 1) as place,
                   w.total as xp,
                   r.game_id is null or v.player_id is not null as seen
            from games g
            left join results r on r.game_id = g.id
            left join rewards w on w.game_id = g.id and w.player_id = %(me)s
            left join result_views v on v.game_id = g.id and v.player_id = %(me)s
            where g.created_by = %(me)s
               or exists (select 1 from game_teams t where t.game_id = g.id and t.player_id = %(me)s)
            order by g.created_at desc, g.id collate "C" """, {"me": player_id})
        teams = self._team_summaries([r["id"] for r in rows])
        entries = []
        for r in rows:
            mine = teams.get(r["id"], [])
            entries.append({
                "id": r["id"], "name": r["name"], "mode": r["mode"], "created": iso(r["created_at"]),
                "mapName": r["map_name"], "attacker": r["created_by"],
                "teams": [{k: t[k] for k in ("name", "colour", "slot", "player")} for t in mine],
                "finished": r["finished"], "outcome": r["outcome"], "place": r["place"],
                "winners": list(r["winners"] or []), "teamCount": len(mine), "xp": r["xp"],
                "seen": r["seen"],
            })
        return entries

    def _team(self, n: int, request: Any) -> tuple[dict[str, Any], str | None]:
        """A team for a new game, and the id of the catalogue tree it starts with (if any)."""
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
            return self._team_with_trees(n, request, player_id, player), None
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
        return team, start["id"]

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

        taken = {r["name"] for r in self.db.query("select name from trees where owner_id is not distinct from %s",
                                                  (owner,))}
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

        with self.atomic():
            map_id = self.create("maps", {**data, "owner": owner})
            tree_ids = [self.create("trees", tree) for tree in new_trees]
        return {"map": map_id, "trees": tree_ids}

    # ---- seasons -------------------------------------------------------------------

    def open_season(self) -> dict[str, Any] | None:
        """The open season, with its id, or None."""
        found = self._load_seasons("status = 'open'", ())
        return found[0] if found else None

    def lock_ratings(self, season_id: str, player_ids: list[str], start: float) -> dict[str, dict[str, Any]]:
        """Players' ratings in a season (start for anyone without one yet), locked until the
        transaction ends so no other battle changes them in the meantime. Use inside atomic()."""
        for player_id in sorted(set(player_ids)):  # always in the same order, so two battles can't deadlock
            self.db.execute("""insert into season_ratings (season_id, player_id, rating) values (%s, %s, %s)
                               on conflict do nothing""", (season_id, player_id, start))
        rows = self.db.query("""select * from season_ratings where season_id = %s and player_id = any(%s)
                                order by player_id for update""", (season_id, list(player_ids)))
        return {r["player_id"]: {"rating": r["rating"], "games": r["games"], "wins": r["wins"]} for r in rows}

    def save_rating(self, season_id: str, player_id: str, entry: dict[str, Any]) -> None:
        self.db.execute("""
            insert into season_ratings (season_id, player_id, rating, games, wins) values (%s, %s, %s, %s, %s)
            on conflict (season_id, player_id)
                do update set rating = excluded.rating, games = excluded.games, wins = excluded.wins""",
            (season_id, player_id, entry["rating"], entry.get("games", 0), entry.get("wins", 0)))

    def season_players(self, season_id: str) -> list[dict[str, Any]]:
        """Everyone with a rating in a season: their id, name, colour, account XP, rating,
        games and wins."""
        return self.db.query("""
            select p.id as player, p.name, p.colour, p.xp, r.rating, r.games, r.wins
            from season_ratings r join players p on p.id = r.player_id
            where r.season_id = %s""", (season_id,))

    def close_season(self, season_id: str) -> bool:
        """Mark a season closed. Returns False if it wasn't open. Use inside atomic() along with
        saving its standings."""
        return self.db.execute("update seasons set status = 'closed', ended_at = now() "
                               "where id = %s and status = 'open'", (season_id,)) == 1

    def save_standing(self, season_id: str, entry: dict[str, Any]) -> None:
        self._save_standing(season_id, entry)


__all__ = ["Catalogue", "CatalogueError", "NotFound", "ScenarioError", "iso", "slugify"]
