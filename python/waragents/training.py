"""Training: tutorials that each teach one idea on a small map.

A tutorial is written by tools/make_tutorials.py to content/tutorials/<id>.json and loaded
into the database by `python -m waragents.db seed`:

    {"name": "Simple move", "track": "Movement", "order": 1, "level": "Beginner",
     "recommendedAfter": [], "brief": "...", "goal": "...", "hints": ["..."],
     "concepts": ["MOVE_RIGHT"], "maxTurns": 20,
     "map": {...a map, with the win conditions for slot 1...},
     "team": {"speed": 10, "health": 100, "power": 10, "startHealth": 40},
     "bots": [{"slot": 2, "name": "Raiders", "trees": [...], "startTree": "...", "power": 8}],
     "solution": {"name": "...", "root": {...}}}

The player always plays slot 1, with a tree of their own (by default "tut-<id>", made from the
tutorial's starter if it has one). Nothing is locked: tutorials can be done in any order, and
recommendedAfter only suggests an order. A run is played through on the server, like a battle,
and the player watches it. Completing a tutorial the first time earns its agents' XP plus a bonus
for its level; runs after that, and failed runs, earn nothing.
"""

from __future__ import annotations

import random
from typing import Any

from .battles import run_to_end, settle
from .catalogue import Catalogue, CatalogueError
from .progression import TUTORIAL_BONUS
from .scenario import check_map, check_tree

TRACKS = ("Movement", "Food", "Combat", "Dirt", "Reproduction", "Misc")
LEVELS = tuple(TUTORIAL_BONUS)


def check_tutorial(data: Any) -> list[str]:
    """Everything wrong with a tutorial."""
    if not isinstance(data, dict):
        return ["a tutorial must be an object"]
    problems = []
    for field in ("name", "brief", "goal"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            problems.append(f"the tutorial needs a {field}")
    if data.get("track") not in TRACKS:
        problems.append(f"track must be one of {', '.join(TRACKS)}")
    if data.get("level") not in LEVELS:
        problems.append(f"level must be one of {', '.join(LEVELS)}")
    if not isinstance(data.get("order"), int):
        problems.append("order must be a whole number")
    if not isinstance(data.get("maxTurns"), int) or data["maxTurns"] < 1:
        problems.append("maxTurns must be a whole number of at least 1")
    problems += [f"map: {p}" for p in check_map(data.get("map"))]
    if isinstance(data.get("map"), dict) and 1 not in {s.get("slot") for s in data["map"].get("starts", [])}:
        problems.append("map: the player plays slot 1, so the map needs a start in it")
    if data.get("solution") is not None:
        problems += [f"solution: {p}" for p in check_tree(data["solution"], allow_empty=False)]
    return problems


def tree_name(tutorial_id: str) -> str:
    """The tree a player builds for a tutorial."""
    return f"tut-{tutorial_id}"


def ordered(catalogue: Catalogue) -> list[dict[str, Any]]:
    """Every tutorial, by track and then order."""
    tutorials = catalogue.list("tutorials")
    return sorted(tutorials, key=lambda t: (TRACKS.index(t["track"]) if t.get("track") in TRACKS else 99,
                                            t.get("order", 0)))


def progress(player: dict[str, Any]) -> dict[str, Any]:
    return player.get("training") or {}


def ensure_tree(catalogue: Catalogue, player_id: str, tutorial_id: str) -> str:
    """The id of the player's tree for a tutorial, made from its starter (or empty) if needed."""
    tutorial = catalogue.get("tutorials", tutorial_id)
    name = tree_name(tutorial_id)
    existing = catalogue.find_tree(player_id, name)
    if existing:
        return existing["id"]
    return catalogue.create("trees", {"name": name, "owner": player_id, "root": tutorial.get("starter")})


def run(catalogue: Catalogue, player_id: str, tutorial_id: str, tree: str | None = None,
        seed: int | None = None) -> dict[str, Any]:
    """Play a tutorial with one of the player's trees (by name; their tutorial tree by default).
    Returns {"gameId", "result", "passed", "firstTime"}."""
    tutorial = catalogue.get("tutorials", tutorial_id)
    tree = tree or tree_name(tutorial_id)
    available = catalogue.trees_for(player_id)
    if tree not in available:
        raise CatalogueError([f"You have no tree called '{tree}'"])

    team = {"slot": 1, "player": player_id, "tree": available[tree]["id"], **tutorial.get("team", {})}
    bots = [{**bot, "player": None} for bot in tutorial.get("bots", [])]
    seed = random.randrange(1_000_000) if seed is None else seed
    game_id, record = catalogue.new_game(
        tutorial["map"], [team, *bots], seed, name=f"Training: {tutorial['name']}", created_by=player_id,
        mode="training", extra={"tutorialId": tutorial_id, "maxTurns": tutorial["maxTurns"]})
    world = run_to_end(record)

    passed = 1 in world.result["winners"]
    with catalogue.atomic():
        first_time = passed and catalogue.complete_tutorial(player_id, tutorial_id, world.time)
        bonus = {player_id: TUTORIAL_BONUS.get(tutorial["level"], 0)} if first_time else {}
        result = settle(catalogue, game_id, record, world, bonus=bonus, count_agent_xp=first_time)
    return {"gameId": game_id, "result": result, "passed": passed, "firstTime": first_time}
