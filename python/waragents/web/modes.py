"""The ways to play: Training (tutorials), Skirmish (pick the map and opponents), Season (ranked
battles on generated maps), and History (every game you've been in, with its result).

A battle is played through on the server when it starts (battles.py), so these return its result
straight away. Watching it is a replay through the usual /api/games/<id> calls.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, abort, current_app, request

from .. import seasons, training
from ..battles import bot_trees, start_skirmish, tree_status
from ..catalogue import Catalogue
from ..progression import level_for
from ..scenario import check_tree, tree_cost
from .auth import admin_only, can_read, me

bp = Blueprint("modes", __name__)


def _catalogue() -> Catalogue:
    return current_app.extensions["waragents"]["catalogue"]


def _body() -> dict[str, Any]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(422, "The request body must be a JSON object")
    return body


def _int_or_none(body: dict[str, Any], name: str) -> int | None:
    value = body.get(name)
    if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
        abort(422, f"`{name}` must be a whole number")
    return value


# ---- who you can fight ------------------------------------------------------------------------


@bp.get("/api/opponents")
def opponents():
    """Players you can pick to fight: everyone else whose default tree is ready. Their trees stay
    private, but their level and their tree's cost help you pick a fair fight."""
    catalogue, user = _catalogue(), me()
    found = []
    for player in catalogue.list("players"):
        if player["id"] == user["id"] or "error" in player:
            continue
        status = tree_status(catalogue, player["id"], player.get("startTree"))
        found.append({"id": player["id"], "name": player["name"], "colour": player.get("colour"),
                      "level": level_for(player.get("xp") or 0), "ready": status["ready"],
                      "treeCost": status["cost"] if status["ready"] else None})
    return sorted(found, key=lambda p: (not p["ready"], p["name"].lower()))


@bp.get("/api/bots")
def bots():
    """Practice opponents: the finished default trees."""
    return [{"name": name, "cost": tree_cost(tree)} for name, tree in sorted(bot_trees(_catalogue()).items())]


# ---- training ---------------------------------------------------------------------------------

SUMMARY = ("name", "track", "order", "level", "goal", "recommendedAfter", "concepts", "maxTurns")


@bp.get("/api/training")
def list_tutorials():
    """Every tutorial in order, with whether you've completed it."""
    catalogue, user = _catalogue(), me()
    done = training.progress(user)
    return [{"id": t["id"], **{k: t.get(k) for k in SUMMARY}, "completed": t["id"] in done,
             "turns": done.get(t["id"], {}).get("turns")} for t in training.ordered(catalogue)]


@bp.get("/api/training/<tutorial_id>")
def read_tutorial(tutorial_id: str):
    """A tutorial, its model answer, your progress and the state of your tree for it."""
    catalogue, user = _catalogue(), me()
    tutorial = catalogue.get("tutorials", tutorial_id)
    name = training.tree_name(tutorial_id)
    tree = catalogue.find_tree(user["id"], name)
    done = training.progress(user).get(tutorial_id)
    order = [t["id"] for t in training.ordered(catalogue)]
    position = order.index(tutorial_id)
    return {
        "id": tutorial_id,
        **{k: v for k, v in tutorial.items() if k != "bots"},
        "bots": [{k: b.get(k) for k in ("slot", "name")} for b in tutorial.get("bots", [])],
        "completed": done is not None,
        "turns": (done or {}).get("turns"),
        "tree": None if tree is None else {"id": tree["id"], "name": name,
                                           "cost": tree_cost(tree), "finished": not check_tree(tree, allow_empty=False)},
        "next": order[position + 1] if position + 1 < len(order) else None,
        "previous": order[position - 1] if position > 0 else None,
    }


@bp.post("/api/training/<tutorial_id>/tree")
def tutorial_tree(tutorial_id: str):
    """Your tree for a tutorial, made if you don't have one yet."""
    return {"treeId": training.ensure_tree(_catalogue(), me()["id"], tutorial_id)}, 201


@bp.post("/api/training/<tutorial_id>/run")
def run_tutorial(tutorial_id: str):
    """Play a tutorial: {tree?, seed?}. tree is one of your trees' names (your tutorial tree by
    default). It's played through at once; watch it with /api/games/<gameId>."""
    body = _body()
    if body.get("tree") is not None and not isinstance(body["tree"], str):
        abort(422, "`tree` must be a tree's name")
    return training.run(_catalogue(), me()["id"], tutorial_id, body.get("tree"), _int_or_none(body, "seed")), 201


# ---- skirmish ---------------------------------------------------------------------------------


@bp.post("/api/skirmish")
def skirmish():
    """Fight on a map of your choice: {map, tree, opponents: [{player} | {bot}], slot?, seed?}.
    tree is the name of one of your trees (or a default tree) and must fit your budget."""
    body, user = _body(), me()
    if not isinstance(body.get("map"), str):
        abort(422, "Choose a map")
    if not isinstance(body.get("tree"), str):
        abort(422, "Choose your tree")
    catalogue = _catalogue()
    map_data = {"id": body["map"], **catalogue.get("maps", body["map"])}
    if not can_read("maps", map_data, user):
        abort(403, "That map belongs to someone else")
    game_id, result = start_skirmish(catalogue, user["id"], body["map"], body["tree"],
                                     body.get("opponents"), _int_or_none(body, "slot"),
                                     _int_or_none(body, "seed"))
    return {"gameId": game_id, "result": result}, 201


# ---- season -----------------------------------------------------------------------------------


def _season_view(season: dict[str, Any] | None) -> dict[str, Any] | None:
    if season is None:
        return None
    catalogue, user = _catalogue(), me()
    board = seasons.leaderboard(catalogue, season)
    return {
        **{k: season.get(k) for k in ("id", "name", "status", "started", "ended", "standings")},
        "leaderboard": board,
        "me": next((r for r in board if r["player"] == user["id"]), None),
    }


@bp.get("/api/season")
def read_season():
    """The running season (or null), its leaderboard and where you stand, plus past seasons."""
    catalogue = _catalogue()
    past = sorted((s for s in catalogue.list("seasons") if s.get("status") == "closed"),
                  key=lambda s: s.get("ended") or "", reverse=True)
    return {"current": _season_view(seasons.current(catalogue)),
            "past": [{k: s.get(k) for k in ("id", "name", "started", "ended")} for s in past]}


@bp.get("/api/season/<season_id>")
def read_one_season(season_id: str):
    catalogue = _catalogue()
    return _season_view({"id": season_id, **catalogue.get("seasons", season_id)})


@bp.post("/api/season/battle")
def season_battle():
    """Fight a Season battle with one of your trees: {tree, seed?}."""
    body, user = _body(), me()
    if not isinstance(body.get("tree"), str):
        abort(422, "Choose your tree")
    return seasons.battle(_catalogue(), user["id"], body["tree"], _int_or_none(body, "seed")), 201


@bp.post("/api/season/start")
@admin_only
def start_season():
    body = request.get_json(silent=True) or {}
    name = body.get("name") if isinstance(body.get("name"), str) and body["name"].strip() else None
    season_id = seasons.start(_catalogue(), name)
    return _season_view({"id": season_id, **_catalogue().get("seasons", season_id)}), 201


@bp.post("/api/season/<season_id>/end")
@admin_only
def end_season(season_id: str):
    return _season_view(seasons.close(_catalogue(), season_id))


# ---- history and results ----------------------------------------------------------------------


@bp.get("/api/history")
def history():
    """Every game you started or had a team in, newest first, with how you did."""
    return _catalogue().history(me()["id"])


def _readable_game(game_id: str) -> dict[str, Any]:
    catalogue, user = _catalogue(), me()
    game = {"id": game_id, **catalogue.get("games", game_id)}
    if not can_read("games", game, user):
        abort(403, "You weren't in that game")
    return game


@bp.get("/api/results/<game_id>")
def read_result(game_id: str):
    game = _readable_game(game_id)
    result = _catalogue().result(game_id)
    if result is None:
        abort(404, "That game hasn't finished, so it has no result yet")
    return {**result, "teams": [{k: t.get(k) for k in ("name", "colour", "slot", "player", "startTree")}
                                for t in game["teams"]]}


@bp.post("/api/results/<game_id>/seen")
def mark_seen(game_id: str):
    """Note that you've looked at a result, so History stops calling it new."""
    _readable_game(game_id)
    catalogue = _catalogue()
    if not catalogue.exists("results", game_id):
        abort(404, "That game has no result yet")
    catalogue.mark_seen(game_id, me()["id"])
    return {"seen": True}
