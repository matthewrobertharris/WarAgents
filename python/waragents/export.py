"""Exporting a player's games, every turn of them, to take away and analyse.

export() streams a zip of CSV files for the player's finished games that pass the Analytics
filters. Each game is replayed from its record, so the export has every turn: where every agent
was, its health and what it did, and the board (dirt, food and plants) as it changed.

It shows exactly what the replay viewer shows. Every team's agents are there, with what they did
and whether it worked, but only the player's own teams come with their trees, the tree each agent
was using, the path it took through it and the positions it remembered. Opponents' trees stay
private.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import zipfile
from typing import Any, Iterator

from .analytics import Analytics, Filters, _mine
from .catalogue import Catalogue
from .scenario import build_world

MAX_GAMES = 500  # the newest games that pass the filters, so one export can't run for ever

README = """WarAgents export
================

Your finished games ({count}) that matched these filters: {filters}
{truncated}
Every file is CSV with a header row. game_id joins them. Turn 0 is how a game started; turn n is
the end of turn n. Slots are the map's start slots, and "yours" marks your team(s).

games.csv     one row per game: when, mode, map, seed, how it ended, and how you did
teams.csv     one row per team per game: who, where they placed, and what they did in total
turns.csv     one row per team per turn: agents alive and their total health
agents.csv    one row per agent per turn: where it was, its health and stats, what it carried,
              the action it took that turn and whether it worked. For your agents only: the
              tree it was using, the path it took (node ids, see below), and the positions it
              remembered (PRIMARY and SECONDARY)
tiles.csv     the board: every tile at turn 0, then only the tiles that changed each turn
events.csv    what happened: births, deaths, failed actions, confusion and the end of the game
trees.json    the trees each of your teams played with, by version fingerprint (the "version"
              column in games.csv), as JSON

Node ids number a tree's nodes in pre-order: the root is 0, then its first branch and everything
under it, then the next branch, and so on. Branches are true/false for BOOLEAN nodes, < = > for
NUMERIC nodes, and left/right/up/down/current for POSITION nodes. Opponents' trees, paths and
remembered positions are private, so those columns are empty for their agents.
"""


class _Pipe(io.RawIOBase):
    """A write-only stream that collects what's written, so the zip can be sent as it's made."""

    def __init__(self):
        self.chunks: list[bytes] = []

    def writable(self) -> bool:
        return True

    def write(self, data) -> int:
        self.chunks.append(bytes(data))
        return len(data)

    def take(self) -> bytes:
        data, self.chunks = b"".join(self.chunks), []
        return data


COLUMNS = {
    "games": ["game_id", "created", "mode", "map_id", "map_name", "seed", "max_turns", "turns", "reason",
              "outcome", "teams", "your_slot", "your_place", "you_won", "your_tree", "version", "version_label",
              "your_xp"],
    "teams": ["game_id", "slot", "team", "yours", "player", "start_tree", "place", "won", "alive_at_end",
              "agents_in_all", "agent_xp", "eliminated_turn", "kills", "deaths", "births", "damage_dealt",
              "damage_taken", "blocks", "food_eaten"],
    "turns": ["game_id", "turn", "slot", "agents", "health"],
    "agents": ["game_id", "turn", "slot", "agent", "x", "y", "health", "max_health", "power", "speed", "level",
               "exp", "carrying_dirt", "carrying_food", "born", "died", "action", "worked", "tree", "path",
               "primary_x", "primary_y", "secondary_x", "secondary_y"],
    "tiles": ["game_id", "turn", "x", "y", "dirt", "food", "plant_rate"],
    "events": ["game_id", "turn", "kind", "agent", "message"],
}
CHUNK = 1 << 20


def export(catalogue: Catalogue, player_id: str, filters: Filters) -> Iterator[bytes]:
    """The zip, in pieces. The README comes first, so the download starts at once; the games are
    then replayed into a temporary file per CSV, which go into the zip one after another (a zip
    can only be written a file at a time)."""
    mine, params = _mine(player_id, filters)
    rows = catalogue.db.query(f"""
        with mine as ({mine})
        select m.game_id, min(m.created_at) as created_at from mine m
        group by m.game_id order by created_at desc, m.game_id limit {MAX_GAMES + 1}""", params)
    truncated = len(rows) > MAX_GAMES
    game_ids = [r["game_id"] for r in reversed(rows[:MAX_GAMES])]  # oldest first

    pipe = _Pipe()
    with zipfile.ZipFile(pipe, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        chosen = {k: v for k, v in filters.to_dict().items() if v}
        archive.writestr("README.txt", README.format(
            count=len(game_ids), filters=json.dumps(chosen) if chosen else "none",
            truncated=f"\nOnly the newest {MAX_GAMES} are here. Narrow the filters to export older ones.\n"
            if truncated else ""))
        yield pipe.take()

        files = {name: tempfile.TemporaryFile("w+", encoding="utf-8", newline="") for name in COLUMNS}
        try:
            writers = {name: csv.writer(f) for name, f in files.items()}
            for name, header in COLUMNS.items():
                writers[name].writerow(header)
            labels = {v["key"]: (tree, v["label"])
                      for tree, vs in Analytics(catalogue).versions(player_id).items() for v in vs}
            trees: dict[str, Any] = {}
            for game_id in game_ids:
                for name, game_rows in _game(catalogue, game_id, player_id, labels, trees).items():
                    writers[name].writerows(game_rows)
            for name, f in files.items():
                f.seek(0)
                with archive.open(f"{name}.csv", "w", force_zip64=True) as member:
                    while chunk := f.read(CHUNK):
                        member.write(chunk.encode("utf-8"))
                        yield pipe.take()
        finally:
            for f in files.values():
                f.close()
        archive.writestr("trees.json", json.dumps(trees, indent=1))
    yield pipe.take()


def _game(catalogue: Catalogue, game_id: str, player_id: str, labels: dict, trees: dict) -> dict[str, list]:
    """Every row a game adds to each file."""
    record = catalogue.get("games", game_id)
    result = catalogue.result(game_id) or {}
    teams = catalogue.db.query("""
        select t.slot, t.name, t.player_id, t.start_tree, t.tree_hash, t.trees, s.kills, s.deaths, s.births,
               s.damage_dealt, s.damage_taken, s.blocks, s.food_eaten
        from game_teams t left join team_stats s using (game_id, slot)
        where t.game_id = %s order by t.position""", (game_id,))
    placements = {p["slot"]: p for p in result.get("placements", [])}
    winners = set(result.get("winners", []))
    yours = [t for t in teams if t["player_id"] == player_id]
    me = yours[0] if yours else None
    xp = result.get("rewards", {}).get(player_id, {}).get("total")
    tree_key, label = labels.get(me["tree_hash"], (None, None)) if me else (None, None)
    for team in yours:
        tree_of = labels.get(team["tree_hash"], (None, None))
        trees.setdefault(team["tree_hash"], {"tree": tree_of[0], "label": tree_of[1],
                                             "startTree": team["start_tree"], "trees": team["trees"]})

    out: dict[str, list] = {"games": [[
        game_id, record.get("created"), record.get("mode"), record.get("mapId") or "", record["map"].get("name"),
        record.get("seed"), record.get("maxTurns"), result.get("turns"), result.get("reason"), result.get("outcome"),
        len(teams), me and me["slot"], me and placements.get(me["slot"], {}).get("place"),
        me and me["slot"] in winners, tree_key or (me and me["start_tree"]), me and me["tree_hash"], label, xp]]}
    out["teams"] = [[
        game_id, t["slot"], t["name"], t["player_id"] == player_id, t["player_id"] or "",
        t["start_tree"] if t["player_id"] == player_id else "",
        placements.get(t["slot"], {}).get("place"), t["slot"] in winners,
        placements.get(t["slot"], {}).get("alive"), placements.get(t["slot"], {}).get("agents"),
        placements.get(t["slot"], {}).get("exp"), placements.get(t["slot"], {}).get("eliminated"),
        t["kills"], t["deaths"], t["births"], t["damage_dealt"], t["damage_taken"], t["blocks"], t["food_eaten"],
    ] for t in teams]
    out.update({"turns": [], "agents": [], "tiles": [], "events": []})

    # Replay it, noting everything after each turn.
    world = build_world({**record, "maxTurns": record.get("maxTurns") or 2000})
    own = {p.slot for p in world.players if p.account == player_id}
    board: dict[tuple[int, int], tuple] = {}
    plants = {(p.pos.x, p.pos.y): p.rate for p in world.plants}

    def note(turn: int) -> None:
        for player in world.players:
            out["turns"].append([game_id, turn, player.slot, len(player.agents),
                                 sum(a.health for a in player.agents)])
            mine = player.slot in own
            for agent in player.all_agents:
                if agent.death is not None and agent.death < turn:
                    continue  # died on an earlier turn
                acted = agent.acted == turn and turn > 0
                out["agents"].append([
                    game_id, turn, player.slot, agent.id, agent.x, agent.y, agent.health, agent.max_health,
                    agent.power, agent.speed, agent.level, agent.exp, agent.dirt, agent.food, agent.birth,
                    agent.death if agent.death is not None else "",
                    agent.action.activity.value if acted and agent.action else "",
                    agent.worked if acted else "",
                    agent.tree.name if mine else "",
                    " ".join(map(str, agent.last_path)) if mine and acted else "",
                    *(_xy(agent.primary) if mine else ("", "")), *(_xy(agent.secondary) if mine else ("", ""))])
        for x in range(world.width):
            for y in range(world.height):
                tile = world.tiles[x][y]
                if tile is None:
                    continue
                now = (tile.dirt, tile.food, plants.get((x, y), ""))
                if board.get((x, y)) != now:
                    board[(x, y)] = now
                    out["tiles"].append([game_id, turn, x, y, *now])

    note(0)
    while not world.finished:
        world.step()
        note(world.time)
    for event in world.events:
        out["events"].append([game_id, event.time, event.kind, event.agent or "", event.message])
    if world.result and result and world.result["turns"] != result.get("turns"):
        out["events"].append([game_id, world.time, "warning", "",
                              "This replay didn't end the way the saved result says"])
    return out


def _xy(pos) -> tuple:
    return ("", "") if pos is None else (pos.x, pos.y)


__all__ = ["COLUMNS", "MAX_GAMES", "export"]
