"""Accounts: registering, signing in and out, and who may see or change what.

A player record is an account. Its id is the username and it holds a password hash, which never
leaves the server. The signed-in player's id is kept in Flask's signed session cookie.

What each player may do:
- Maps and trees belong to their owner, who is the only one who can change them. A map or tree
  with no owner is a system map or a default tree: everyone can use it and only admins change it.
  Other players' trees can't be read at all. Other players' maps can be read once published.
- Anyone signed in can see everyone's public profile (no password hash, nothing private).
- A game can be seen by the player who started it and the players who had a team in it.
- Admins can do anything, including the raw catalogue screens.
"""

from __future__ import annotations

import os
import re
from functools import wraps
from typing import Any

from flask import Blueprint, abort, current_app, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from ..battles import tree_status
from ..catalogue import Catalogue, NotFound, slugify
from ..progression import level_summary

MIN_PASSWORD = 8
PRIVATE_FIELDS = ("passwordHash",)
# Requests anyone can make without signing in.
OPEN_PATHS = re.compile(r"^/api/(auth/|reference$)")

bp = Blueprint("auth", __name__)


def secret_key(catalogue: Catalogue) -> str:
    """The key that signs session cookies: WARAGENTS_SECRET, or one made once and kept in the
    database, so sign-ins survive a restart and work on every server."""
    return os.environ.get("WARAGENTS_SECRET") or catalogue.secret("session-key")


def _catalogue() -> Catalogue:
    return current_app.extensions["waragents"]["catalogue"]


def public(player: dict[str, Any]) -> dict[str, Any]:
    """A player record without the fields that must stay on the server."""
    return {k: v for k, v in player.items() if k not in PRIVATE_FIELDS}


# ---- who's signed in -----------------------------------------------------------------


def current_user() -> dict[str, Any] | None:
    """The signed-in player, with their id, or None. A deleted player is signed out."""
    player_id = session.get("player")
    if player_id is None:
        return None
    try:
        return {"id": player_id, **_catalogue().get("players", player_id)}
    except NotFound:
        session.pop("player", None)
        return None


def me() -> dict[str, Any]:
    """The signed-in player. Answers 401 if nobody is."""
    user = current_user()
    if user is None:
        abort(401, "Sign in first")
    return user


def is_admin(user: dict[str, Any] | None) -> bool:
    return bool(user and user.get("admin"))


def admin_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_admin(me()):
            abort(403, "Only an admin can do that")
        return view(*args, **kwargs)
    return wrapper


def require_sign_in() -> None:
    """Run before every request: the API needs a signed-in player, apart from OPEN_PATHS."""
    if request.path.startswith("/api/") and not OPEN_PATHS.match(request.path):
        me()


# ---- what they can do ------------------------------------------------------------------


def game_players(game: dict[str, Any]) -> set[str]:
    return {t.get("player") for t in game.get("teams", []) if t.get("player")}


def can_read(kind: str, item: dict[str, Any], user: dict[str, Any]) -> bool:
    if is_admin(user) or kind == "players":
        return True
    if kind == "trees":
        return item.get("owner") in (None, user["id"])
    if kind == "maps":
        return item.get("owner") in (None, user["id"]) or bool(item.get("published"))
    if kind == "games":
        return item.get("createdBy") == user["id"] or user["id"] in game_players(item)
    return False


def can_change(kind: str, item: dict[str, Any], user: dict[str, Any]) -> bool:
    if is_admin(user):
        return True
    if kind in ("trees", "maps"):
        return item.get("owner") == user["id"]
    if kind == "players":
        return item.get("id") == user["id"]
    if kind == "games":
        # Only a game nobody else played in, so nobody's history is changed behind their back.
        return item.get("createdBy") == user["id"] and game_players(item) <= {user["id"]}
    return False


# ---- routes ------------------------------------------------------------------------------


def _credentials() -> tuple[str, str]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(422, "Send a name and a password")
    name, password = body.get("name"), body.get("password")
    if not isinstance(name, str) or not name.strip() or not isinstance(password, str) or not password:
        abort(422, "Send a name and a password")
    return name.strip(), password


def _signed_in(player_id: str):
    session.clear()
    session["player"] = player_id
    session.permanent = True
    return jsonify(profile(player_id))


def profile(player_id: str) -> dict[str, Any]:
    """What the signed-in player sees about themselves (GET /api/me): their record, their level
    and budget, and whether their default tree is ready to defend them."""
    catalogue = _catalogue()
    player = catalogue.get("players", player_id)
    return {
        "id": player_id,
        **public(player),
        **level_summary(player.get("xp") or 0),
        "defaultTree": tree_status(catalogue, player_id, player.get("startTree")),
        "friendRequests": catalogue.friend_requests(player_id),
    }


@bp.post("/api/auth/register")
def register():
    name, password = _credentials()
    catalogue = _catalogue()
    username = slugify(name)
    if not username:
        abort(422, "A name needs at least one letter or number")
    if catalogue.exists("players", username):
        abort(409, f"The name '{name}' is taken")
    if len(password) < MIN_PASSWORD:
        abort(422, f"Passwords need at least {MIN_PASSWORD} characters")
    # The first account on a server, or the first since every admin was deleted, runs it.
    first = not catalogue.any_admin()
    player = {"name": name, "colour": None, "startTree": None,
              "passwordHash": generate_password_hash(password), **({"admin": True} if first else {})}
    catalogue.create_with_id("players", username, player)
    return _signed_in(username), 201


@bp.post("/api/auth/login")
def login():
    name, password = _credentials()
    catalogue = _catalogue()
    username = slugify(name)
    try:
        player = catalogue.get("players", username) if username else None
    except NotFound:
        player = None
    if not player or not player.get("passwordHash") or not check_password_hash(player["passwordHash"], password):
        abort(401, "That name and password don't match")
    return _signed_in(username)


@bp.post("/api/auth/logout")
def logout():
    session.clear()
    return {"signedOut": True}


@bp.get("/api/auth/me")
def who_am_i():
    """The signed-in player, or null. Unlike /api/me this doesn't need anyone to be signed in."""
    user = current_user()
    return jsonify(None if user is None else profile(user["id"]))


@bp.get("/api/me")
def read_me():
    return profile(me()["id"])


@bp.put("/api/me")
def update_me():
    """Change your name, colour or default tree. Anything else in the body is ignored."""
    user = me()
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(422, "Send the fields to change")
    catalogue = _catalogue()
    if body.get("startTree") and body["startTree"] != user.get("startTree"):
        status = tree_status(catalogue, user["id"], body["startTree"])
        if not status["ready"]:
            abort(400, f"'{body['startTree']}' can't be your default tree. {status['problem']}.")
    catalogue.update_player(user["id"], {k: body[k] for k in ("name", "colour", "startTree") if k in body})
    return profile(user["id"])


@bp.put("/api/me/password")
def change_password():
    user = me()
    body = request.get_json(silent=True) or {}
    current, new = body.get("current"), body.get("new")
    if not isinstance(current, str) or not check_password_hash(user.get("passwordHash", ""), current):
        abort(403, "Your current password isn't right")
    if not isinstance(new, str) or len(new) < MIN_PASSWORD:
        abort(422, f"Passwords need at least {MIN_PASSWORD} characters")
    set_password(_catalogue(), user["id"], new)
    return {"changed": True}


def set_password(catalogue: Catalogue, player_id: str, password: str, admin: bool | None = None) -> None:
    """Give a player a new password (and make them an admin or not, if admin is given)."""
    changes: dict[str, Any] = {"passwordHash": generate_password_hash(password)}
    if admin is not None:
        changes["admin"] = admin
    catalogue.update_player(player_id, changes)
