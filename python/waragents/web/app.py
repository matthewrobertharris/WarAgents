"""FastAPI server: serves the front end and runs games in memory.

Games live in this process only, so they are lost on restart. This is fine for a local app,
but a shared deployment will need a store and a way to expire old games.
"""

from __future__ import annotations

import random
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..actions import Activity
from ..inputs import INPUTS
from ..mapfile import MapFormatError, parse_map
from ..positions import SIMPLE_POSITIONS
from ..serialize import event_to_dict, world_to_dict
from ..world import World

PYTHON_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Where bundled maps come from, as (group, directory). Map ids are "group/stem".
MAP_SOURCES = [
    ("demo", PYTHON_DIR / "maps"),
    ("java", PYTHON_DIR.parent / "resources" / "maps"),
    ("java", PYTHON_DIR.parent / "resources" / "test"),
]
MAX_GAMES = 200
MAX_TURNS_PER_STEP = 1000
RECENT_EVENTS = 200


@dataclass
class Game:
    id: str
    map_name: str
    text: str
    seed: int
    world: World
    lock: threading.Lock = field(default_factory=threading.Lock)


GAMES: OrderedDict[str, Game] = OrderedDict()
GAMES_LOCK = threading.Lock()

app = FastAPI(title="WarAgents")


def bundled_maps() -> dict[str, Path]:
    maps = {}
    for group, directory in MAP_SOURCES:
        for path in sorted(directory.glob("*.map")):
            maps.setdefault(f"{group}/{path.stem}", path)
    return maps


def recent(events: list) -> list:
    """The last RECENT_EVENTS events, plus fewer failed actions so they don't crowd out the rest."""
    keep = {id(e) for e in [e for e in events if e.kind != "fail"][-RECENT_EVENTS:]}
    keep |= {id(e) for e in [e for e in events if e.kind == "fail"][-RECENT_EVENTS // 2:]}
    return [e for e in events if id(e) in keep]


def game_state(game: Game, new_events=None) -> dict:
    world = game.world
    events = recent(world.events if new_events is None else new_events)
    return {
        "id": game.id,
        "map": game.map_name,
        "text": game.text,
        "state": world_to_dict(world),
        "events": [event_to_dict(e) for e in events],
    }


def get_game(game_id: str) -> Game:
    game = GAMES.get(game_id)
    if game is None:
        raise HTTPException(404, "Game not found. The server may have restarted.")
    return game


class NewGame(BaseModel):
    map: str | None = Field(None, description="A bundled map id from /api/maps")
    text: str | None = Field(None, description="Map file contents, used instead of `map`")
    seed: int | None = None


class Step(BaseModel):
    turns: int = Field(1, ge=1, le=MAX_TURNS_PER_STEP)


@app.get("/api/maps")
def list_maps() -> list[dict]:
    result = []
    for map_id, path in bundled_maps().items():
        try:
            parse_map(path.read_text())
            error = None
        except MapFormatError as e:
            error = str(e)
        result.append({"id": map_id, "group": map_id.split("/")[0], "name": path.stem, "error": error})
    return result


@app.get("/api/maps/{group}/{name}")
def get_map(group: str, name: str) -> dict:
    path = bundled_maps().get(f"{group}/{name}")
    if path is None:
        raise HTTPException(404, f"No map called {group}/{name}")
    return {"id": f"{group}/{name}", "text": path.read_text()}


@app.get("/api/reference")
def reference() -> dict:
    """Everything that can go in a tree, for the editor's cheat sheet."""
    def doc(cls) -> str:
        text = (cls.__doc__ or "").strip()
        # Dataclasses without a docstring get their signature as __doc__.
        return "" if text.startswith(cls.__name__ + "(") else text.splitlines()[0] if text else ""

    action_args = {"CHANGE_TREE": ["name"], "SET_PRIMARY": ["position"], "SET_SECONDARY": ["position"]}
    return {
        "inputs": [{"name": c.name, "kind": c.kind, "args": list(c.args), "doc": doc(c)}
                   for c in INPUTS.values()],
        "actions": [{"name": a.value, "args": action_args.get(a.value, [])} for a in Activity],
        "positions": [*SIMPLE_POSITIONS, "XY_VALUE x y"],
        "criteria": ["SURVIVE_TURNS turns", "ANNIHILATE player", "COLLECT_FOOD player amount",
                     "LEVEL_UP player exp", "MAP_DIRT dirt x y", "TRAVEL_TO player x y",
                     "PERFORM_ACTION player action times", "FIND_THING id"],
    }


@app.post("/api/games")
def create_game(request: NewGame) -> dict:
    if request.text is not None:
        text, name = request.text, "custom"
    elif request.map is not None:
        path = bundled_maps().get(request.map)
        if path is None:
            raise HTTPException(404, f"No map called {request.map}")
        text, name = path.read_text(), request.map
    else:
        raise HTTPException(422, "Send either a map id or map text")

    seed = request.seed if request.seed is not None else random.randrange(1_000_000)
    try:
        world = parse_map(text, seed=seed)
    except MapFormatError as e:
        raise HTTPException(400, str(e)) from None

    game = Game(uuid.uuid4().hex[:12], name, text, seed, world)
    with GAMES_LOCK:
        GAMES[game.id] = game
        while len(GAMES) > MAX_GAMES:
            GAMES.popitem(last=False)
    return game_state(game)


@app.get("/api/games/{game_id}")
def read_game(game_id: str) -> dict:
    game = get_game(game_id)
    with game.lock:
        return game_state(game)


@app.post("/api/games/{game_id}/step")
def step_game(game_id: str, request: Step) -> dict:
    game = get_game(game_id)
    with game.lock:
        events = []
        for _ in range(request.turns):
            if game.world.finished:
                break
            events.extend(game.world.step())
        return game_state(game, events)


@app.post("/api/games/{game_id}/reset")
def reset_game(game_id: str) -> dict:
    game = get_game(game_id)
    with game.lock:
        game.world = parse_map(game.text, seed=game.seed)
        return game_state(game)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
