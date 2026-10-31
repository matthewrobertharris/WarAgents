"""Flask server: the catalogue API, running games, and the front end.

Every API call apart from signing in needs a signed-in player, and what they can see and change
is decided in auth.py. Running games are kept in memory, one copy per game and viewer, so two
people watching the same game don't move each other's turn. A game that isn't in memory, for
example after a restart, is rebuilt from its saved record, which holds its seed and starting
conditions. Everything is stored in the PostgreSQL database named by WARAGENTS_DATABASE_URL
(see db/__init__.py). For a production server, run create_app() under a WSGI server, such as
`waitress-serve --call waragents.web.app:create_app`.
"""

from __future__ import annotations

import random
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from .. import progression
from ..actions import ACTION_ARGS, ACTION_DOCS, Activity
from ..battles import tree_status
from ..progression import action_cost, action_exp, budget_for, input_cost, xp_for_level
from ..catalogue import KINDS, Catalogue, CatalogueError, NotFound
from ..db import Database, database_url
from ..db.migrate import require_current
from ..inputs import INPUTS
from ..mapfile import MapFormatError
from ..positions import SIMPLE_POSITIONS
from ..scenario import (CRITERIA, ScenarioError, build_world, check_map, check_tree, map_size,
                        map_slots, tree_cost)
from ..serialize import event_to_dict, world_to_dict
from ..tree import NODE_SHAPES
from ..world import MAX_DIRT, MAX_FOOD, MODES, World
from . import analytics, auth, friends, modes
from .auth import can_change, can_read, is_admin, me, public

STATIC_DIR = Path(__file__).resolve().parent / "static"

SUMMARY_FIELDS = {"id", "width", "height", "slots", "problems", "error", "cost"}
MAX_SESSIONS = 50
MAX_TURNS_PER_STEP = 1000
RECENT_EVENTS = 200


@dataclass
class Session:
    """A game being watched: its saved record and its world as it stands now for one viewer."""

    id: str
    record: dict[str, Any]
    world: World
    lock: threading.Lock = field(default_factory=threading.Lock)


class Sessions:
    """Running games, one per (game, viewer), dropping the least recently used."""

    def __init__(self, catalogue: Catalogue):
        self.catalogue = catalogue
        self.games: OrderedDict[tuple[str, str], Session] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, game_id: str, viewer: str, record: dict[str, Any] | None = None) -> Session:
        with self.lock:
            session = self.games.get((game_id, viewer))
            if session is not None:
                self.games.move_to_end((game_id, viewer))
                return session
        return self.add(game_id, viewer, record or self.catalogue.get("games", game_id))

    def add(self, game_id: str, viewer: str, record: dict[str, Any]) -> Session:
        session = Session(game_id, record, build_world(record))
        with self.lock:
            self.games[(game_id, viewer)] = session
            while len(self.games) > MAX_SESSIONS:
                self.games.popitem(last=False)
        return session

    def drop(self, game_id: str) -> None:
        with self.lock:
            for key in [k for k in self.games if k[0] == game_id]:
                del self.games[key]


def recent(events: list) -> list:
    """The last RECENT_EVENTS events, plus fewer failed actions so they don't crowd out the rest."""
    keep = {id(e) for e in [e for e in events if e.kind != "fail"][-RECENT_EVENTS:]}
    keep |= {id(e) for e in [e for e in events if e.kind == "fail"][-RECENT_EVENTS // 2:]}
    return [e for e in events if id(e) in keep]


def game_state(session: Session, new_events=None) -> dict[str, Any]:
    """A game for the signed-in viewer. They see their own team's trees, practice teams' trees
    (which are default trees) and, if they're an admin, everyone's."""
    world = session.world
    events = recent(world.events if new_events is None else new_events)
    user = me()

    def visible(player) -> bool:
        return is_admin(user) or player.account in (None, user["id"])

    return {
        "id": session.id,
        "name": session.record["name"],
        "mode": session.record.get("mode", "sandbox"),
        "mapId": session.record.get("mapId"),
        "state": world_to_dict(world, visible=visible),
        "events": [event_to_dict(e) for e in events],
    }


def summarise(kind: str, item: dict[str, Any]) -> dict[str, Any]:
    """A catalogue list entry. Games are cut down. Maps and trees get a "problems" list of what
    stops them being played (empty when they're ready), and a map that can't be read at all gets
    an "error"."""
    if "error" in item:
        return item
    if kind == "games":
        return {
            "id": item["id"], "name": item.get("name"), "created": item.get("created"),
            "seed": item.get("seed"), "mapId": item.get("mapId"),
            "mapName": (item.get("map") or {}).get("name"),
            "teams": [{k: t.get(k) for k in ("name", "colour", "slot", "player", "startTree")}
                      for t in item.get("teams", [])],
        }
    if kind == "maps":
        broken = check_map(item, allow_unfinished=True)
        if broken:
            return {**item, "error": "; ".join(broken[:3])}
        width, height = map_size(item)
        return {**item, "width": width, "height": height, "slots": map_slots(item),
                "problems": check_map(item)}
    if kind == "trees":
        problems = check_tree(item, allow_empty=False)
        return {**item, "problems": [p.to_dict() for p in problems], "cost": tree_cost(item)}
    if kind == "players":
        return public(item)
    return item


def json_body() -> Any:
    body = request.get_json(silent=True)
    return {} if body is None else body


def json_object() -> dict[str, Any]:
    body = json_body()
    if not isinstance(body, dict):
        abort(422, "The request body must be a JSON object")
    return body


def optional_field(body: dict, name: str, kind: type):
    value = body.get(name)
    # bool is a subclass of int, but true isn't a seed or a turn count.
    if value is not None and (not isinstance(value, kind) or isinstance(value, bool)):
        abort(422, f"`{name}` must be {'an integer' if kind is int else 'a string'}")
    return value


def connect() -> Catalogue:
    """The catalogue in the database named by WARAGENTS_DATABASE_URL, which must be set up.
    Raises DatabaseNotReady with what to do if it isn't."""
    db = Database(database_url())
    try:
        require_current(db)
    except Exception:
        db.close()
        raise
    return Catalogue(db)


def create_app(catalogue: Catalogue | None = None) -> Flask:
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
    app.json.sort_keys = False
    catalogue = catalogue or connect()
    sessions = Sessions(catalogue)
    app.extensions["waragents"] = {"catalogue": catalogue, "sessions": sessions}
    app.secret_key = auth.secret_key(catalogue)
    app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True,
                      PERMANENT_SESSION_LIFETIME=timedelta(days=30))
    app.register_blueprint(auth.bp)
    app.register_blueprint(modes.bp)
    app.register_blueprint(analytics.bp)
    app.register_blueprint(friends.bp)
    app.before_request(auth.require_sign_in)

    # Errors are JSON with a `detail` message, which is what the front end shows.
    @app.errorhandler(HTTPException)
    def http_error(e: HTTPException):
        return jsonify(detail=e.description), e.code

    @app.errorhandler(NotFound)
    def not_found(e: NotFound):
        return jsonify(detail=str(e)), 404

    @app.errorhandler(CatalogueError)
    @app.errorhandler(ScenarioError)
    def bad_content(e: CatalogueError | ScenarioError):
        return jsonify(detail=str(e), problems=[str(p) for p in e.problems]), 400

    @app.errorhandler(MapFormatError)
    def bad_map_file(e: MapFormatError):
        return jsonify(detail=str(e)), 400

    # ---- reference -------------------------------------------------------------------

    @app.get("/api/reference")
    def reference():
        """Everything that can go in a map, tree or game, for the editors and cheat sheets."""
        def doc(cls) -> str:
            text = (cls.__doc__ or "").strip()
            # Dataclasses without a docstring get their signature as __doc__.
            if not text or text.startswith(cls.__name__ + "("):
                return ""
            return " ".join(text.split("\n\n")[0].split())

        return {
            "nodes": {kind.value: {"input": shape[0], "count": shape[1], "branches": list(shape[2])}
                      for kind, shape in NODE_SHAPES.items()},
            "inputs": [{"name": c.name, "kind": c.kind, "args": list(c.args), "doc": doc(c),
                        "cost": input_cost(c.name)} for c in INPUTS.values()],
            "actions": [{"name": a.value, "args": list(ACTION_ARGS.get(a.value, ())),
                         "doc": ACTION_DOCS.get(a.value, ""), "cost": action_cost(a.value),
                         "exp": action_exp(a.value)} for a in Activity],
            "positions": [*SIMPLE_POSITIONS, "XY_VALUE x y"],
            "criteria": {name: [list(f) for f in spec] for name, spec in CRITERIA.items()},
            "modes": list(MODES),
            "limits": {"dirt": MAX_DIRT, "food": MAX_FOOD},
            "progression": {
                "killExp": progression.KILL_EXP,
                "blockExp": progression.BLOCK_EXP,
                "modeXpFactor": progression.MODE_XP_FACTOR,
                "seasonPlayBonus": progression.SEASON_PLAY_BONUS,
                "seasonPlaceBonus": progression.SEASON_PLACE_BONUS,
                "tutorialBonus": progression.TUTORIAL_BONUS,
                "maxLevel": progression.MAX_LEVEL,
                "levels": [{"level": n, "xp": xp_for_level(n), "budget": budget_for(n)}
                           for n in (1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 50, 75, 100)],
            },
        }

    # ---- catalogue -------------------------------------------------------------------

    def check_kind(kind: str) -> None:
        if kind not in KINDS:
            abort(404, f"There's no '{kind}' in the catalogue")
        if kind in ("results", "tutorials", "seasons") and not is_admin(me()):
            abort(403, f"{kind.title()} are read through /api/{ {'tutorials': 'training', 'seasons': 'season'}.get(kind, kind)}")

    def stored(kind: str, item_id: str) -> dict[str, Any]:
        """An item as saved, with its id."""
        return {"id": item_id, **catalogue.get(kind, item_id)}

    def readable(kind: str, item_id: str) -> dict[str, Any]:
        item = stored(kind, item_id)
        if not can_read(kind, item, me()):
            abort(403, f"That {kind[:-1]} belongs to someone else")
        return item

    def changeable(kind: str, item_id: str) -> dict[str, Any]:
        item = stored(kind, item_id)
        if not can_change(kind, item, me()):
            abort(403, f"Only the owner of that {kind[:-1]} can change it")
        return item

    @app.get("/api/catalogue/<kind>")
    def list_items(kind: str):
        check_kind(kind)
        user = me()

        def visible(item: dict[str, Any]) -> bool:
            # A file that can't be read has no owner to check, so only admins see it.
            return is_admin(user) if "error" in item else can_read(kind, item, user)

        if kind == "games":
            return catalogue.game_summaries(None if is_admin(user) else user["id"])
        viewer = None if is_admin(user) else user["id"]
        return [summarise(kind, item) for item in catalogue.list(kind, viewer) if visible(item)]

    def one_item(kind: str, item_id: str) -> dict[str, Any]:
        """A whole item. Maps and trees also say what stops them being played, as in the list."""
        item = stored(kind, item_id)
        return summarise(kind, item) if kind in ("maps", "trees", "players") else item

    @app.get("/api/catalogue/<kind>/<item_id>")
    def read_item(kind: str, item_id: str):
        check_kind(kind)
        readable(kind, item_id)
        return one_item(kind, item_id)

    def item_body() -> dict[str, Any]:
        """The item in the request, without the fields one_item() adds, so a client can send
        back what it was given."""
        return {k: v for k, v in json_object().items() if k not in SUMMARY_FIELDS}

    def owned_body(kind: str, existing: dict[str, Any] | None) -> dict[str, Any]:
        """The request's item with the fields a player can't set for themselves put right: a
        map or tree belongs to whoever saves it unless they're an admin, and a player's password
        and admin flag only change through auth.py."""
        body, user = item_body(), me()
        if kind in ("maps", "trees") and not is_admin(user):
            body["owner"] = existing.get("owner") if existing else user["id"]
        if kind == "players":
            body.pop("passwordHash", None)
            if existing and existing.get("passwordHash"):
                body["passwordHash"] = existing["passwordHash"]
            if not is_admin(user):
                # Admin rights, XP and tutorial progress are earned, not set.
                for name in ("admin", "xp", "training"):
                    body.pop(name, None)
                    if existing and existing.get(name):
                        body[name] = existing[name]
        return body

    @app.post("/api/catalogue/<kind>")
    def create_item(kind: str):
        check_kind(kind)
        if kind == "players" and not is_admin(me()):
            abort(403, "New players sign up for themselves")
        item_id = catalogue.create(kind, owned_body(kind, None))
        return one_item(kind, item_id), 201

    @app.put("/api/catalogue/<kind>/<item_id>")
    def update_item(kind: str, item_id: str):
        check_kind(kind)
        if kind == "games" and not is_admin(me()):
            abort(403, "Games can't be changed once they've started")
        existing = changeable(kind, item_id)
        body = owned_body(kind, existing)
        if kind == "players" and body.get("startTree") and body["startTree"] != existing.get("startTree"):
            # A default tree defends you in other players' battles, so it has to be ready.
            status = tree_status(catalogue, item_id, body["startTree"])
            if not status["ready"]:
                abort(400, f"'{body['startTree']}' can't be your default tree. {status['problem']}.")
        catalogue.update(kind, item_id, body)
        if kind == "games":
            sessions.drop(item_id)
        return one_item(kind, item_id)

    @app.delete("/api/catalogue/<kind>/<item_id>")
    def delete_item(kind: str, item_id: str):
        check_kind(kind)
        changeable(kind, item_id)
        catalogue.delete(kind, item_id)
        if kind == "games":
            sessions.drop(item_id)
        return {"deleted": item_id}

    @app.post("/api/catalogue/import")
    def import_map():
        """Add a .map file's map and trees to the catalogue. They belong to whoever imports them,
        unless an admin says otherwise."""
        body, user = json_object(), me()
        text = optional_field(body, "text", str)
        name = optional_field(body, "name", str)
        if not text or not name:
            abort(422, "Send the .map file's text and a name for the map")
        owner = optional_field(body, "owner", str) if is_admin(user) else user["id"]
        return catalogue.import_map(text, name, owner), 201

    # ---- games -----------------------------------------------------------------------

    def watch(game_id: str) -> Session:
        """The signed-in player's running copy of a game they're allowed to see."""
        return sessions.get(game_id, me()["id"], readable("games", game_id))

    @app.post("/api/games")
    def create_game():
        body, user = json_object(), me()
        map_id = optional_field(body, "map", str)
        if map_id is None:
            abort(422, "Choose a map")
        readable("maps", map_id)
        teams = body.get("teams")
        if not is_admin(user) and isinstance(teams, list):
            for team in teams:
                if isinstance(team, dict) and team.get("player") not in (None, user["id"]):
                    abort(403, "You can only play as yourself")
        seed = optional_field(body, "seed", int)
        if seed is None:
            seed = random.randrange(1_000_000)
        game_id, record = catalogue.new_game(map_id, teams, seed, optional_field(body, "name", str),
                                             created_by=user["id"])
        return game_state(sessions.add(game_id, user["id"], record)), 201

    @app.get("/api/games/<game_id>")
    def read_game(game_id: str):
        session = watch(game_id)
        with session.lock:
            return game_state(session)

    @app.post("/api/games/<game_id>/step")
    def step_game(game_id: str):
        turns = optional_field(json_object(), "turns", int)
        turns = 1 if turns is None else turns
        if not 1 <= turns <= MAX_TURNS_PER_STEP:
            abort(422, f"`turns` must be between 1 and {MAX_TURNS_PER_STEP}")
        session = watch(game_id)
        with session.lock:
            events = []
            for _ in range(turns):
                if session.world.finished:
                    break
                events.extend(session.world.step())
            return game_state(session, events)

    @app.post("/api/games/<game_id>/seek")
    def seek_game(game_id: str):
        """Go to a turn. Going back rebuilds the game and replays it from turn 0, which ends up
        exactly where it was because all the randomness comes from the game's seed."""
        turn = optional_field(json_object(), "turn", int)
        if turn is None or turn < 0:
            abort(422, "Send the turn to go to, such as {\"turn\": 12}")
        session = watch(game_id)
        with session.lock:
            if turn < session.world.time:
                session.world = build_world(session.record)
            if turn - session.world.time > MAX_TURNS_PER_STEP:
                abort(422, f"You can only go {MAX_TURNS_PER_STEP} turns ahead at a time")
            while session.world.time < turn and not session.world.finished:
                session.world.step()
            return game_state(session)

    @app.post("/api/games/<game_id>/reset")
    def reset_game(game_id: str):
        session = watch(game_id)
        with session.lock:
            session.world = build_world(session.record)
            return game_state(session)

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    return app

