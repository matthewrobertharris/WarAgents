"""Seasons: ranked battles on generated maps.

A season is saved in catalogue/seasons/<id>.json:

    {"name": "Season 1", "status": "open", "started": "2026-10-11T09:00:00", "ended": null,
     "ratings": {"alice": {"rating": 1016.0, "games": 3, "wins": 2}},
     "standings": null}

Only one season is open at a time. A Season battle generates a map for 2 to 4 teams and picks
opponents from the other players whose default trees are ready: those whose tree costs about the
same as yours, closest in rating first. Everyone in the battle has their rating updated, and gets
the Season XP bonus for their place. When an admin ends the season, players are ranked within
bands of levels and rewarded with a share of a level's XP (progression.season_reward), and the
final standings are saved in the season.
"""

from __future__ import annotations

import random
import threading
from datetime import datetime
from typing import Any

from . import mapgen
from .battles import battle_teams, run_to_end, settle, tree_status
from .catalogue import Catalogue, CatalogueError
from .progression import (MATCH_COST_RANGE, MATCH_COST_WIDEN, RATING_START, SEASON_MAX_TURNS,
                          SEASON_MIN_GAMES, band_label, level_band, level_for, level_summary,
                          rating_changes, season_reward)

# Ratings are read, changed and written back, so one battle's changes at a time.
_RATINGS = threading.Lock()


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def check_season(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return ["a season must be an object"]
    problems = []
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        problems.append("the season needs a name")
    if data.get("status") not in ("open", "closed"):
        problems.append("status must be open or closed")
    if not isinstance(data.get("ratings", {}), dict):
        problems.append("ratings must be an object")
    return problems


def current(catalogue: Catalogue) -> dict[str, Any] | None:
    """The open season, with its id, or None."""
    return next((s for s in catalogue.list("seasons") if s.get("status") == "open"), None)


def start(catalogue: Catalogue, name: str | None = None) -> str:
    if current(catalogue):
        raise CatalogueError(["A season is already running. End it first."])
    number = len(catalogue.list("seasons")) + 1
    return catalogue.create("seasons", {"name": name or f"Season {number}", "status": "open",
                                        "started": now(), "ended": None, "ratings": {}, "standings": None})


def rating_of(season: dict[str, Any], player_id: str) -> float:
    return season.get("ratings", {}).get(player_id, {}).get("rating", RATING_START)


def pick_opponents(catalogue: Catalogue, season: dict[str, Any], player_id: str, cost: int,
                   wanted: int) -> list[str]:
    """Up to `wanted` opponents: players with a ready default tree costing within range of `cost`
    (the range widens until there are enough), closest in rating first."""
    mine = rating_of(season, player_id)
    candidates = []
    for player in catalogue.list("players"):
        if player["id"] == player_id or "error" in player:
            continue
        status = tree_status(catalogue, player["id"], player.get("startTree"))
        if status["ready"]:
            candidates.append((player["id"], status["cost"]))
    if not candidates:
        return []
    spread = MATCH_COST_RANGE
    while True:
        low, high = cost * (1 - spread), cost * (1 + spread)
        in_range = [pid for pid, c in candidates if low <= c <= high]
        if len(in_range) >= wanted or len(in_range) == len(candidates):
            break
        spread *= MATCH_COST_WIDEN
    in_range.sort(key=lambda pid: (abs(rating_of(season, pid) - mine), pid))
    return in_range[:wanted]


def battle(catalogue: Catalogue, player_id: str, tree_name: str, seed: int | None = None) -> dict[str, Any]:
    """Play a Season battle. Returns {"gameId", "result"}."""
    season = current(catalogue)
    if season is None:
        raise CatalogueError(["No season is running at the moment"])
    status = tree_status(catalogue, player_id, tree_name)
    if not status["ready"]:
        raise CatalogueError([f"Your tree '{tree_name}' isn't ready: {status['problem']}"])

    rng = random.Random(seed)
    seed = rng.randrange(1_000_000) if seed is None else seed
    wanted = rng.randint(1, 3)
    opponents = pick_opponents(catalogue, season, player_id, status["cost"], wanted)
    if not opponents:
        raise CatalogueError(["Nobody else has a default tree ready yet, so there's no one to fight. "
                              "Try a Skirmish against practice bots."])
    map_data = mapgen.generate(seed, len(opponents) + 1)
    teams = battle_teams(catalogue, player_id, tree_name, [{"player": pid} for pid in opponents],
                         [s["slot"] for s in map_data["starts"]], 1)
    game_id, record = catalogue.new_game(
        map_data, teams, seed, name=f"Season battle on {map_data['name']}", created_by=player_id,
        mode="season", extra={"seasonId": season["id"], "maxTurns": SEASON_MAX_TURNS})
    world = run_to_end(record)

    # Every pair of teams counts as a match: a better place wins it.
    placements = world.result["placements"]
    by_slot = {t["slot"]: t["player"] for t in record["teams"]}
    players = [by_slot[p["slot"]] for p in placements]
    with _RATINGS:
        # Read it again, in case another battle has saved since.
        season = {"id": season["id"], **catalogue.get("seasons", season["id"])}
        before = [rating_of(season, pid) for pid in players]
        changes = rating_changes(before, [p["place"] for p in placements])
        ratings = season.setdefault("ratings", {})
        extra = {}
        outright = len(world.result["winners"]) == 1
        for pid, old, change, place in zip(players, before, changes, placements):
            entry = ratings.get(pid, {"rating": RATING_START, "games": 0, "wins": 0})
            entry = {"rating": round(old + change, 1), "games": entry["games"] + 1,
                     "wins": entry["wins"] + (1 if place["place"] == 1 and outright else 0)}
            ratings[pid] = entry
            extra[pid] = {"rating": {"before": round(old, 1), "after": entry["rating"]}}
        catalogue.update("seasons", season["id"], season)
    result = settle(catalogue, game_id, record, world, extra_rewards=extra)
    return {"gameId": game_id, "result": result}


def leaderboard(catalogue: Catalogue, season: dict[str, Any]) -> list[dict[str, Any]]:
    """Everyone who has played in the season, best rating first, with their level band."""
    rows = []
    for player_id, entry in season.get("ratings", {}).items():
        if not catalogue.exists("players", player_id):
            continue
        player = catalogue.get("players", player_id)
        level = level_for(player.get("xp") or 0)
        rows.append({"player": player_id, "name": player["name"], "colour": player.get("colour"),
                     "level": level, "band": level_band(level), **entry})
    rows.sort(key=lambda r: (-r["rating"], -r["wins"], r["name"].lower()))
    for n, row in enumerate(rows):
        row["rank"] = n + 1
    return rows


def close(catalogue: Catalogue, season_id: str) -> dict[str, Any]:
    """End a season: rank players within their level band, give out the rewards, and save the
    final standings. Returns the closed season."""
    season = catalogue.get("seasons", season_id)
    if season.get("status") != "open":
        raise CatalogueError(["That season has already ended"])
    rows = leaderboard(catalogue, season)
    standings = []
    for band in sorted({r["band"] for r in rows}):
        ranked = [r for r in rows if r["band"] == band and r["games"] >= SEASON_MIN_GAMES]
        unranked = [r for r in rows if r["band"] == band and r["games"] < SEASON_MIN_GAMES]
        entries = []
        for n, row in enumerate(ranked):
            xp = season_reward(row["level"], n + 1, len(ranked))
            player = catalogue.get("players", row["player"])
            before = player.get("xp") or 0
            catalogue.update("players", row["player"], {**player, "xp": before + xp})
            entries.append({**row, "bandRank": n + 1, "reward": xp,
                            "before": level_summary(before), "after": level_summary(before + xp)})
        entries += [{**row, "bandRank": None, "reward": 0} for row in unranked]
        standings.append({"band": band, "label": band_label(band), "players": entries})
    season.update({"status": "closed", "ended": now(), "standings": standings})
    catalogue.update("seasons", season_id, season)
    return {"id": season_id, **season}
