"""Flask server: the catalogue API, running games, and the front end.

Running games are kept in memory, keyed by their catalogue id. A game that isn't in memory, for
example after a restart, is rebuilt from its saved record, which holds its seed and starting
conditions. The catalogue folder defaults to python/catalogue. Set WARAGENTS_CATALOGUE, or pass
--catalogue to `python -m waragents.web`, to use another one.
"""

from __future__ import annotations

import os
import random
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from ..actions import ACTION_ARGS, Activity
from ..catalogue import KINDS, Catalogue, CatalogueError, NotFound
from ..inputs import INPUTS
from ..mapfile import MapFormatError
from ..positions import SIMPLE_POSITIONS
from ..scenario import (CRITERIA, ScenarioError, build_world, check_map, check_tree, map_size,
                        map_slots)
from ..serialize import event_to_dict, world_to_dict
from ..tree import NODE_SHAPES
from ..world import MAX_DIRT, MAX_FOOD, MODES, World

PYTHON_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_CATALOGUE = PYTHON_DIR / "catalogue"

SUMMARY_FIELDS = {"id", "width", "height", "slots", "problems", "error"}
MAX_SESSIONS = 50
MAX_TURNS_PER_STEP = 1000
RECENT_EVENTS = 200


@dataclass
class Session:
    """A game being played: its saved record and its world as it stands now."""

    id: str
    record: dict[str, Any]
    world: World
    lock: threading.Lock = field(default_factory=threading.Lock)


class Sessions:
    def __init__(self, catalogue: Catalogue):
        self.catalogue = catalogue
        self.games: OrderedDict[str, Session] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, game_id: str) -> Session:
        with self.lock:
            session = self.games.get(game_id)
            if session is not None:
                self.games.move_to_end(game_id)
                return session
        return self.add(game_id, self.catalogue.get("games", game_id))

    def add(self, game_id: str, record: dict[str, Any]) -> Session:
        session = Session(game_id, record, build_world(record))
        with self.lock:
            self.games[game_id] = session
            while len(self.games) > MAX_SESSIONS:
                self.games.popitem(last=False)
        return session

    def drop(self, game_id: str) -> None:
        with self.lock:
            self.games.pop(game_id, None)


def recent(events: list) -> list:
    """The last RECENT_EVENTS events, plus fewer failed actions so they don't crowd out the rest."""
    keep = {id(e) for e in [e for e in events if e.kind != "fail"][-RECENT_EVENTS:]}
    keep |= {id(e) for e in [e for e in events if e.kind == "fail"][-RECENT_EVENTS // 2:]}
    return [e for e in events if id(e) in keep]


def game_state(session: Session, new_events=None) -> dict[str, Any]:
    world = session.world
    events = recent(world.events if new_events is None else new_events)
    return {
        "id": session.id,
        "name": session.record["name"],
        "mapId": session.record.get("mapId"),
        "state": world_to_dict(world),
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
        return {**item, "problems": [p.to_dict() for p in problems]}
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


def create_app(catalogue_dir: Path | str | None = None) -> Flask:
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
    app.json.sort_keys = False
    catalogue = Catalogue(catalogue_dir or os.environ.get("WARAGENTS_CATALOGUE") or DEFAULT_CATALOGUE)
    sessions = Sessions(catalogue)
    app.extensions["waragents"] = {"catalogue": catalogue, "sessions": sessions}

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
            return "" if text.startswith(cls.__name__ + "(") else text.splitlines()[0] if text else ""

        return {
            "nodes": {kind.value: {"input": shape[0], "count": shape[1], "branches": list(shape[2])}
                      for kind, shape in NODE_SHAPES.items()},
            "inputs": [{"name": c.name, "kind": c.kind, "args": list(c.args), "doc": doc(c)}
                       for c in INPUTS.values()],
            "actions": [{"name": a.value, "args": list(ACTION_ARGS.get(a.value, ()))} for a in Activity],
            "positions": [*SIMPLE_POSITIONS, "XY_VALUE x y"],
            "criteria": {name: [list(f) for f in spec] for name, spec in CRITERIA.items()},
            "modes": list(MODES),
            "limits": {"dirt": MAX_DIRT, "food": MAX_FOOD},
        }

    # ---- catalogue -------------------------------------------------------------------

    def check_kind(kind: str) -> None:
        if kind not in KINDS:
            abort(404, f"There's no '{kind}' in the catalogue")

    @app.get("/api/catalogue/<kind>")
    def list_items(kind: str):
        check_kind(kind)
        items = [summarise(kind, item) for item in catalogue.list(kind)]
        if kind == "games":
            items.sort(key=lambda g: g.get("created") or "", reverse=True)
        return items

    def one_item(kind: str, item_id: str) -> dict[str, Any]:
        """A whole item. Maps and trees also say what stops them being played, as in the list."""
        item = {"id": item_id, **catalogue.get(kind, item_id)}
        return summarise(kind, item) if kind in ("maps", "trees") else item

    @app.get("/api/catalogue/<kind>/<item_id>")
    def read_item(kind: str, item_id: str):
        check_kind(kind)
        return one_item(kind, item_id)

    def item_body() -> dict[str, Any]:
        """The item in the request, without the fields one_item() adds, so a client can send
        back what it was given."""
        return {k: v for k, v in json_object().items() if k not in SUMMARY_FIELDS}

    @app.post("/api/catalogue/<kind>")
    def create_item(kind: str):
        check_kind(kind)
        item_id = catalogue.create(kind, item_body())
        return one_item(kind, item_id), 201

    @app.put("/api/catalogue/<kind>/<item_id>")
    def update_item(kind: str, item_id: str):
        check_kind(kind)
        catalogue.update(kind, item_id, item_body())
        if kind == "games":
            sessions.drop(item_id)
        return one_item(kind, item_id)

    @app.delete("/api/catalogue/<kind>/<item_id>")
    def delete_item(kind: str, item_id: str):
        check_kind(kind)
        catalogue.delete(kind, item_id)
        if kind == "games":
            sessions.drop(item_id)
        return {"deleted": item_id}

    @app.post("/api/catalogue/import")
    def import_map():
        """Add a .map file's map and trees to the catalogue."""
        body = json_object()
        text = optional_field(body, "text", str)
        name = optional_field(body, "name", str)
        if not text or not name:
            abort(422, "Send the .map file's text and a name for the map")
        return catalogue.import_map(text, name, optional_field(body, "owner", str)), 201

    # ---- games -----------------------------------------------------------------------

    @app.post("/api/games")
    def create_game():
        body = json_object()
        map_id = optional_field(body, "map", str)
        if map_id is None:
            abort(422, "Choose a map")
        seed = optional_field(body, "seed", int)
        if seed is None:
            seed = random.randrange(1_000_000)
        game_id, record = catalogue.new_game(map_id, body.get("teams"), seed,
                                             optional_field(body, "name", str))
        return game_state(sessions.add(game_id, record)), 201

    @app.get("/api/games/<game_id>")
    def read_game(game_id: str):
        session = sessions.get(game_id)
        with session.lock:
            return game_state(session)

    @app.post("/api/games/<game_id>/step")
    def step_game(game_id: str):
        turns = optional_field(json_object(), "turns", int)
        turns = 1 if turns is None else turns
        if not 1 <= turns <= MAX_TURNS_PER_STEP:
            abort(422, f"`turns` must be between 1 and {MAX_TURNS_PER_STEP}")
        session = sessions.get(game_id)
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
        session = sessions.get(game_id)
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
        session = sessions.get(game_id)
        with session.lock:
            session.world = build_world(session.record)
            return game_state(session)

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    return app


app = create_app()
