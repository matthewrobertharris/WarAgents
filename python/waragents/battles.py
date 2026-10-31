"""Battles between players, and what they earn.

A battle is decided on the server as soon as it starts: the game record is saved, played through
to the end, and its result (places and XP) saved next to it. Players see the result first and can
watch the replay whenever they like, because the record replays exactly.

Every team in a battle uses the same agent stats, so only the trees differ. A player's own team
uses the tree they choose, which must fit their budget. Anyone they pick to fight plays with their
default tree. Practice opponents ("bots") play a default tree and have no player behind them.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from .catalogue import DEFAULT_STATS, Catalogue, CatalogueError
from .progression import (DEFAULT_MAX_TURNS, account_xp, budget_for, level_for, level_summary,
                          season_bonus)
from .scenario import build_world, check_map, check_tree, map_slots, team_cost
from .world import World


def budget_of(player: dict[str, Any]) -> int:
    """The points a player's trees can cost, from their account XP."""
    return budget_for(level_for(player.get("xp") or 0))


def tree_status(catalogue: Catalogue, player_id: str, tree_name: str | None) -> dict[str, Any]:
    """Whether a player can take a tree into a battle: it's one of the trees they can use, it's
    finished, and it fits their budget along with the trees it switches to.

    Returns {"name", "cost", "budget", "ready", "problem"}, where problem says what's wrong.
    """
    player = catalogue.get("players", player_id)
    budget = budget_of(player)
    status: dict[str, Any] = {"name": tree_name, "cost": None, "budget": budget, "ready": False,
                              "problem": None}
    available = catalogue.trees_for(player_id)
    tree = available.get(tree_name) if tree_name else None
    if tree_name is None:
        status["problem"] = "No tree chosen"
    elif tree is None:
        status["problem"] = f"There's no tree called '{tree_name}' any more"
    else:
        cost = team_cost(tree, available)
        status["cost"] = cost["cost"]
        unfinished = [name for name in cost["trees"] if check_tree(available[name], allow_empty=False)]
        if unfinished:
            status["problem"] = f"Not finished: {', '.join(unfinished)}"
        elif cost["cost"] > budget:
            status["problem"] = f"It costs {cost['cost']} points and the budget is {budget}"
        else:
            status["ready"] = True
    return status


def bot_trees(catalogue: Catalogue) -> dict[str, dict[str, Any]]:
    """The default trees practice opponents can play, by name: the finished ones."""
    return {name: tree for name, tree in catalogue.trees_for(None).items()
            if not check_tree(tree, allow_empty=False)}


def run_to_end(record: dict[str, Any]) -> World:
    """Build a game record's world and play it until it finishes. A record without maxTurns gets
    the default, so this always ends. Raises ScenarioError if the record is wrong."""
    if record.get("maxTurns") is None:
        record = {**record, "maxTurns": DEFAULT_MAX_TURNS}
    world = build_world(record)
    while not world.finished:
        world.step()
    return world


# ---- setting up a battle ------------------------------------------------------------------


def battle_teams(catalogue: Catalogue, player_id: str, tree_name: str, opponents: list[Any],
                 slots: list[int], slot: int | None = None) -> list[dict[str, Any]]:
    """The team requests for catalogue.new_game: the player's team with tree_name, then one per
    opponent, which is {"player": id} (they play their default tree) or {"bot": tree name}. Each
    may say which "slot" it takes; the rest fill the map's free slots in order. Raises
    CatalogueError listing everything that's wrong."""
    problems: list[str] = []
    status = tree_status(catalogue, player_id, tree_name)
    if not status["ready"]:
        problems.append(f"Your tree '{tree_name}' isn't ready: {status['problem']}")
    if not isinstance(opponents, list) or not opponents:
        problems.append("Choose at least one opponent")
        opponents = []
    if len(opponents) + 1 > len(slots):
        problems.append(f"This map has room for {len(slots)} teams, so at most {len(slots) - 1} opponents")

    me = catalogue.get("players", player_id)
    available = catalogue.trees_for(player_id)
    teams = [{"slot": slot, "player": player_id, "tree": available.get(tree_name, {}).get("id"),
              "name": me["name"], "colour": me.get("colour")}]
    bots = bot_trees(catalogue)
    seen_players = {player_id}
    for n, opponent in enumerate(opponents):
        if not isinstance(opponent, dict):
            problems.append(f"Opponent {n + 1} must be a player or a bot")
            continue
        if opponent.get("player"):
            other = opponent["player"]
            if other in seen_players:
                problems.append("You can't pick yourself, or the same player twice" if other == player_id
                                else f"'{other}' is picked twice")
                continue
            seen_players.add(other)
            if not catalogue.exists("players", other):
                problems.append(f"There's no player '{other}'")
                continue
            them = catalogue.get("players", other)
            theirs = tree_status(catalogue, other, them.get("startTree"))
            if not theirs["ready"]:
                problems.append(f"{them['name']} can't be picked yet: their default tree isn't ready")
                continue
            teams.append({"slot": opponent.get("slot"), "player": other, "tree": None,
                          "name": them["name"], "colour": them.get("colour")})
        elif opponent.get("bot"):
            tree = bots.get(opponent["bot"])
            if tree is None:
                problems.append(f"There's no practice opponent called '{opponent['bot']}'")
                continue
            teams.append({"slot": opponent.get("slot"), "player": None, "tree": tree["id"],
                          "name": f"Bot ({tree['name']})", "colour": None})
        else:
            problems.append(f"Opponent {n + 1} must be a player or a bot")
    if problems:
        raise CatalogueError(problems)

    # Fill in slots, names that clash and colours that clash, and give everyone the same stats.
    taken = {t["slot"] for t in teams if t["slot"] is not None}
    bad = taken - set(slots)
    if bad:
        raise CatalogueError([f"This map has no slot {', '.join(map(str, sorted(bad)))}"])
    if len(taken) < len([t for t in teams if t["slot"] is not None]):
        raise CatalogueError(["Two teams can't share a slot"])
    free = [s for s in slots if s not in taken]
    names: set[str] = set()
    colours: set[str] = set()
    for team in teams:
        if team["slot"] is None:
            team["slot"] = free.pop(0)
        base, n = team["name"], 2
        while team["name"] in names:
            team["name"], n = f"{base} {n}", n + 1
        names.add(team["name"])
        if team["colour"] in colours:
            team["colour"] = None  # the viewer gives it its slot's colour
        colours.add(team["colour"])
        team.update(DEFAULT_STATS)
    return teams


def playable_map(catalogue: Catalogue, map_id: str) -> dict[str, Any]:
    map_data = catalogue.get("maps", map_id)
    problems = check_map(map_data)
    if problems:
        raise CatalogueError([f"That map can't be played yet: {problems[0]}"])
    return map_data


def start_skirmish(catalogue: Catalogue, player_id: str, map_id: str, tree_name: str,
                   opponents: list[Any], slot: int | None = None,
                   seed: int | None = None) -> tuple[str, dict[str, Any]]:
    """Set up, play and settle a skirmish. Returns (game id, result)."""
    map_data = playable_map(catalogue, map_id)
    teams = battle_teams(catalogue, player_id, tree_name, opponents, map_slots(map_data), slot)
    seed = random.randrange(1_000_000) if seed is None else seed
    game_id, record = catalogue.new_game(map_id, teams, seed, created_by=player_id, mode="skirmish",
                                         name=f"Skirmish on {map_data['name']}")
    return game_id, settle(catalogue, game_id, record, run_to_end(record))


# ---- results and rewards ------------------------------------------------------------------


def settle(catalogue: Catalogue, game_id: str, record: dict[str, Any], world: World,
           bonus: dict[str, int] | None = None, count_agent_xp: bool = True,
           extra_rewards: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Save a finished game's result and give each player their account XP: their agents' XP
    times the mode's factor (unless count_agent_xp is False), plus the Season bonus for their
    place and anything in bonus (player id to XP). extra_rewards adds fields to a player's
    rewards, such as their rating change. Returns the result."""
    mode = record.get("mode", "sandbox")
    teams = {t["slot"]: t for t in record["teams"]}
    placements = [{**p, "player": teams[p["slot"]].get("player"), "colour": teams[p["slot"]].get("colour")}
                  for p in world.result["placements"]]
    rewards: dict[str, dict[str, Any]] = {}
    with catalogue.atomic():
        for place in placements:
            player_id = place["player"]
            if not player_id or player_id in rewards:
                continue
            from_agents = account_xp(mode, place["exp"]) if count_agent_xp else 0
            extra = (bonus or {}).get(player_id, 0)
            if mode == "season":
                extra += season_bonus(place["place"], len(placements))
            xp = catalogue.add_xp(player_id, from_agents + extra)
            if xp is None:
                continue  # the player has been deleted
            before, after = xp
            rewards[player_id] = {
                "agentXp": place["exp"],
                "fromAgents": from_agents,
                "bonus": extra,
                "total": from_agents + extra,
                "before": level_summary(before),
                "after": level_summary(after),
                **(extra_rewards or {}).get(player_id, {}),
            }
        result = {
            "gameId": game_id,
            "mode": mode,
            "name": record.get("name"),
            "mapName": (record.get("map") or {}).get("name"),
            "created": record.get("created") or datetime.now().isoformat(timespec="seconds"),
            "finished": datetime.now().isoformat(timespec="seconds"),
            **{k: world.result[k] for k in ("reason", "outcome", "turns", "winners")},
            "placements": placements,
            "rewards": rewards,
            "seenBy": [],
        }
        catalogue.save_result(game_id, result)
        catalogue.save_stats(game_id, world.players)
    return result
