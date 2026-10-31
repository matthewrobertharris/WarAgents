"""Friends, and players' public profiles.

A player asks another to be friends, by name or from their profile, and the other accepts or
declines. Until then the request is only seen by the two of them, and neither shows up in the
other's friends. Either can withdraw a request or stop being friends at any time.

Anyone signed in can open a player's profile (from a leaderboard or a result, say) to see their
public details and ask them to be friends. The list of every player is for admins only.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, abort, current_app, request

from ..battles import tree_status
from ..catalogue import Catalogue, NotFound, slugify
from ..progression import level_for
from .auth import me

bp = Blueprint("friends", __name__)


def _catalogue() -> Catalogue:
    return current_app.extensions["waragents"]["catalogue"]


def _card(catalogue: Catalogue, player: dict[str, Any]) -> dict[str, Any]:
    """What anyone may see of a player: name, colour, level, and whether they can be picked to fight."""
    status = tree_status(catalogue, player["id"], player.get("startTree"))
    return {"id": player["id"], "name": player["name"], "colour": player.get("colour"),
            "level": level_for(player.get("xp") or 0), "ready": status["ready"],
            "treeCost": status["cost"] if status["ready"] else None}


@bp.get("/api/players/<player_id>")
def read_player(player_id: str):
    """A player's public profile, and how you stand with them."""
    catalogue, user = _catalogue(), me()
    player = {"id": player_id, **catalogue.get("players", player_id)}
    return {**_card(catalogue, player), "created": player.get("created"), "you": player_id == user["id"],
            "friendship": "you" if player_id == user["id"] else catalogue.friendship(user["id"], player_id)}


@bp.get("/api/friends")
def list_friends():
    """Your friends, the requests waiting for your answer, and the ones you're waiting on."""
    catalogue, user = _catalogue(), me()
    found = catalogue.friends(user["id"])
    return {kind: [{**_card(catalogue, p), "since": p["since"], "requested": p["requested"]} for p in players]
            for kind, players in found.items()}


@bp.post("/api/friends")
def add_friend():
    """Ask someone to be your friend: {player} (their id) or {name}. If they've already asked
    you, you're friends straight away."""
    body = request.get_json(silent=True) or {}
    wanted = body.get("player") or body.get("name")
    if not isinstance(wanted, str) or not wanted.strip():
        abort(422, "Send the player's name")
    catalogue, user = _catalogue(), me()
    other = slugify(wanted)
    if not other or not catalogue.exists("players", other):
        abort(404, f"There's no player called '{wanted.strip()}'")
    status = catalogue.ask_friend(user["id"], other)
    return {"player": other, "friendship": status}, 201


@bp.post("/api/friends/<player_id>/accept")
def accept_friend(player_id: str):
    catalogue = _catalogue()
    if not catalogue.accept_friend(me()["id"], player_id):
        raise NotFound(f"There's no request from '{player_id}' to accept")
    return {"player": player_id, "friendship": "friends"}


@bp.delete("/api/friends/<player_id>")
def remove_friend(player_id: str):
    """Decline their request, withdraw yours, or stop being friends."""
    catalogue = _catalogue()
    if not catalogue.remove_friend(me()["id"], player_id):
        raise NotFound(f"You and '{player_id}' aren't friends and haven't asked to be")
    return {"player": player_id, "friendship": "none"}
