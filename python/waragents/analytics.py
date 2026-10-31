"""Analytics: how a player's trees have done, over their finished games, filtered any way.

The unit is one of the player's teams in a finished game (Training, Skirmish or Season; Sandbox
games are never settled, so they have no result). Players only ever see their own teams, though a
game's other teams are named when they're opponents. Every view takes the same filters, and every
breakdown is keyed by the value that filters on it, so the screen can turn any bar into a filter.

Filters (all optional, lists are comma-separated in the query string):
    since, until   dates, like 2026-10-01, inclusive
    mode           training, skirmish, season
    map            a map id, "tutorial:<id>" for a tutorial's map, or "generated" for Season maps
    tree           a tree id, or "~<name>" for a tree that has since been deleted
    version        a tree version: the fingerprint of the trees a team played (game_teams.tree_hash)
    opponent       a player id, or "bot:<team name>" for a practice team
    outcome        win or loss
    season         a season id

The counts behind it (kills, actions, node visits, ...) come from stats.py and are saved when a
game is settled. backfill() replays older games to count theirs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping

from .battles import run_to_end
from .catalogue import Catalogue, iso
from .stats import STATS_VERSION

MODES = ("training", "skirmish", "season")
OUTCOMES = ("win", "loss")
RECENT_GAMES = 50
TIMELINE_POINTS = 150

# Keys shared by filters and breakdowns. g is games, t the player's team, o another team.
MAP_KEY = ("coalesce(g.map_id, case when g.tutorial_id is not null then 'tutorial:' || g.tutorial_id "
           "else 'generated' end)")
TREE_KEY = "coalesce(t.tree_id, '~' || t.start_tree)"
OPPONENT_KEY = "coalesce(o.player_id, 'bot:' || o.name)"


class AnalyticsError(ValueError):
    pass


@dataclass
class Filters:
    since: date | None = None
    until: date | None = None
    modes: list[str] = field(default_factory=list)
    maps: list[str] = field(default_factory=list)
    trees: list[str] = field(default_factory=list)
    versions: list[str] = field(default_factory=list)
    opponents: list[str] = field(default_factory=list)
    outcome: str | None = None
    seasons: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, args: Mapping[str, str]) -> Filters:
        def many(name: str) -> list[str]:
            return [v.strip() for v in (args.get(name) or "").split(",") if v.strip()]

        def day(name: str) -> date | None:
            value = (args.get(name) or "").strip()
            if not value:
                return None
            try:
                return date.fromisoformat(value)
            except ValueError:
                raise AnalyticsError(f"`{name}` must be a date like 2026-10-01") from None

        filters = cls(since=day("since"), until=day("until"), modes=many("mode"), maps=many("map"),
                      trees=many("tree"), versions=many("version"), opponents=many("opponent"),
                      outcome=(args.get("outcome") or "").strip() or None, seasons=many("season"))
        bad = [m for m in filters.modes if m not in MODES]
        if bad:
            raise AnalyticsError(f"mode must be one of {', '.join(MODES)}, not {', '.join(bad)}")
        if filters.outcome is not None and filters.outcome not in OUTCOMES:
            raise AnalyticsError("outcome must be win or loss")
        return filters

    def to_dict(self) -> dict[str, Any]:
        return {"since": self.since and self.since.isoformat(), "until": self.until and self.until.isoformat(),
                "mode": self.modes, "map": self.maps, "tree": self.trees, "version": self.versions,
                "opponent": self.opponents, "outcome": self.outcome, "season": self.seasons}


def _mine(player_id: str, filters: Filters) -> tuple[str, dict[str, Any]]:
    """SQL for the player's teams in finished games that pass the filters, one row each."""
    where = ["t.player_id = %(me)s"]
    params: dict[str, Any] = {"me": player_id}
    if filters.since:
        where.append("g.created_at >= %(since)s::date")
        params["since"] = filters.since
    if filters.until:
        where.append("g.created_at < %(until)s::date + 1")
        params["until"] = filters.until
    for name, column in (("modes", "g.mode"), ("maps", MAP_KEY), ("trees", TREE_KEY),
                         ("versions", "t.tree_hash"), ("seasons", "g.season_id")):
        values = getattr(filters, name)
        if values:
            where.append(f"{column} = any(%({name})s)")
            params[name] = values
    if filters.opponents:
        where.append(f"""exists (select 1 from game_teams o where o.game_id = t.game_id and o.slot <> t.slot
                                 and {OPPONENT_KEY} = any(%(opponents)s))""")
        params["opponents"] = filters.opponents
    if filters.outcome:
        where.append(("" if filters.outcome == "win" else "not ") + "(t.slot = any(r.winners))")
    sql = f"""
        select t.game_id, t.slot, {TREE_KEY} as tree_key, t.start_tree, t.tree_hash,
               g.created_at, g.mode, {MAP_KEY} as map_key, g.map ->> 'name' as map_name,
               g.season_id, r.turns, p.place, t.slot = any(r.winners) as won,
               (select count(*) from game_teams o where o.game_id = t.game_id) as team_count,
               coalesce(w.total, 0) as xp
        from game_teams t
        join games g on g.id = t.game_id
        join results r on r.game_id = t.game_id
        join placements p on p.game_id = t.game_id and p.slot = t.slot
        left join rewards w on w.game_id = t.game_id and w.player_id = t.player_id
        where {' and '.join(where)}"""
    return sql, params


def _rate(wins: int, games: int) -> float | None:
    return round(wins / games, 3) if games else None


def _group(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"key": r["key"], "label": r["label"], "games": r["games"], "wins": r["wins"],
             "winRate": _rate(r["wins"], r["games"]),
             "avgPlace": None if r["avg_place"] is None else round(float(r["avg_place"]), 2)}
            for r in rows]


class Analytics:
    def __init__(self, catalogue: Catalogue):
        self.catalogue = catalogue
        self.db = catalogue.db

    def _query(self, player_id: str, filters: Filters, select: str) -> list[dict[str, Any]]:
        """Run select with two tables to hand: mine (the player's teams that pass the filters) and
        opp (the other teams in those games, or just the chosen opponents if there are some)."""
        mine, params = _mine(player_id, filters)
        chosen = f"and {OPPONENT_KEY} = any(%(opponents)s)" if filters.opponents else ""
        return self.db.query(f"""
            with mine as ({mine}),
            opp as (select distinct o.game_id, o.slot from mine m
                    join game_teams o on o.game_id = m.game_id and o.slot <> m.slot
                    where o.player_id is distinct from %(me)s {chosen})
            {select}""", params)

    def _breakdown(self, player_id: str, filters: Filters, key: str, label: str,
                   source: str = "mine m", order: str = "games desc, label") -> list[dict[str, Any]]:
        return _group(self._query(player_id, filters, f"""
            select {key} as key, {label} as label, count(*) as games, count(*) filter (where m.won) as wins,
                   avg(m.place) as avg_place
            from {source} group by 1 order by {order}"""))

    # ---- the dashboard ---------------------------------------------------------------------------

    def summary(self, player_id: str, filters: Filters) -> dict[str, Any]:
        """Everything the Analytics screen charts, for the games that pass the filters."""
        return {
            "filters": filters.to_dict(),
            "kpis": self._kpis(player_id, filters),
            "overTime": self._over_time(player_id, filters),
            "byTree": self._by_tree(player_id, filters),
            "byVersion": self._by_version(player_id, filters),
            "byMap": self._by_map(player_id, filters),
            "byOpponent": self._by_opponent(player_id, filters),
            "byMode": self._breakdown(player_id, filters, "m.mode", "initcap(m.mode)"),
            "you": self._side(player_id, filters, "mine"),
            "opponents": self._side(player_id, filters, "opp"),
            "timeline": self._timeline(player_id, filters),
            "games": self._games(player_id, filters),
        }

    def _kpis(self, player_id: str, filters: Filters) -> dict[str, Any]:
        row = self._query(player_id, filters, """
            select count(*) as games, count(*) filter (where m.won) as wins, avg(m.place) as avg_place,
                   avg(m.turns) as avg_turns, sum(m.xp) as xp, count(s.game_id) as counted,
                   sum(s.kills) as kills, sum(s.deaths) as deaths, sum(s.damage_dealt) as damage_dealt,
                   sum(s.damage_taken) as damage_taken, sum(s.food_eaten) as food_eaten, sum(s.births) as births,
                   sum(s.confused) as confused,
                   (select sum(a.succeeded) from team_actions a join mine x using (game_id, slot)
                    where a.action <> 'CONFUSED') as succeeded,
                   (select sum(a.succeeded + a.failed) from team_actions a join mine x using (game_id, slot)) as decisions
            from mine m left join team_stats s using (game_id, slot)""")[0]
        decisions = row["decisions"] or 0
        confused = row["confused"] or 0
        return {
            "games": row["games"], "wins": row["wins"], "winRate": _rate(row["wins"], row["games"]),
            "avgPlace": None if row["avg_place"] is None else round(float(row["avg_place"]), 2),
            "avgTurns": None if row["avg_turns"] is None else round(float(row["avg_turns"]), 1),
            "xp": row["xp"] or 0, "counted": row["counted"],
            **{k: row[k] or 0 for k in ("kills", "deaths", "births")},
            "damageDealt": row["damage_dealt"] or 0, "damageTaken": row["damage_taken"] or 0,
            "foodEaten": row["food_eaten"] or 0, "decisions": decisions,
            "confusedRate": round(confused / decisions, 3) if decisions else None,
            "successRate": round((row["succeeded"] or 0) / (decisions - confused), 3) if decisions > confused else None,
        }

    def _over_time(self, player_id: str, filters: Filters) -> dict[str, Any]:
        span = self._query(player_id, filters, "select min(created_at) as first, max(created_at) as last from mine")[0]
        if span["first"] is None:
            return {"bucket": "day", "points": []}
        days = (span["last"] - span["first"]).days
        bucket = "day" if days <= 45 else "week" if days <= 365 else "month"
        rows = self._query(player_id, filters, f"""
            select date_trunc('{bucket}', m.created_at)::date as start, count(*) as games,
                   count(*) filter (where m.won) as wins, avg(m.place) as avg_place
            from mine m group by 1 order by 1""")
        return {"bucket": bucket, "points": [
            {"start": r["start"].isoformat(), "games": r["games"], "wins": r["wins"],
             "winRate": _rate(r["wins"], r["games"]), "avgPlace": round(float(r["avg_place"]), 2)} for r in rows]}

    def _by_tree(self, player_id: str, filters: Filters) -> list[dict[str, Any]]:
        return self._breakdown(
            player_id, filters, "m.tree_key",
            "coalesce((select tr.name from trees tr where tr.id = m.tree_key), max(m.start_tree) || ' (deleted)')",
            order="games desc, 2")

    def _by_map(self, player_id: str, filters: Filters, order: str = "games desc, 2") -> list[dict[str, Any]]:
        return self._breakdown(player_id, filters, "m.map_key",
                               "case when m.map_key = 'generated' then 'Generated maps' else max(m.map_name) end",
                               order=order)

    def _by_opponent(self, player_id: str, filters: Filters, order: str = "games desc, 2") -> list[dict[str, Any]]:
        return self._breakdown(player_id, filters, OPPONENT_KEY, "max(o.name)",
                               source="mine m join game_teams o on o.game_id = m.game_id and o.slot <> m.slot",
                               order=order)

    def versions(self, player_id: str, tree_keys: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
        """Every version of the player's trees that has played, by tree key, oldest first, each
        labelled v1, v2, ... in the order they first played. Unfiltered, so labels don't change
        with the filters."""
        rows = self.db.query(f"""
            select {TREE_KEY} as tree_key, t.tree_hash, min(g.created_at) as first, max(g.created_at) as last,
                   count(*) as games
            from game_teams t join games g on g.id = t.game_id join results r on r.game_id = t.game_id
            where t.player_id = %(me)s {"and " + TREE_KEY + " = any(%(trees)s)" if tree_keys else ""}
            group by 1, 2 order by 1, 3""", {"me": player_id, "trees": tree_keys})
        out: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            versions = out.setdefault(r["tree_key"], [])
            versions.append({"key": r["tree_hash"], "label": f"v{len(versions) + 1}", "firstPlayed": iso(r["first"]),
                             "lastPlayed": iso(r["last"]), "games": r["games"]})
        return out

    def _by_version(self, player_id: str, filters: Filters) -> list[dict[str, Any]] | None:
        """Win rate by version, when the filters pick out a single tree."""
        if len(filters.trees) != 1:
            return None
        labels = {v["key"]: v for v in self.versions(player_id, filters.trees).get(filters.trees[0], [])}
        rows = self._breakdown(player_id, filters, "m.tree_hash", "''", order="min(m.created_at)")
        for row in rows:
            version = labels.get(row["key"], {})
            row.update(label=version.get("label", "?"), firstPlayed=version.get("firstPlayed"))
        return rows

    def _side(self, player_id: str, filters: Filters, side: str) -> dict[str, Any]:
        """What one side did: the player's teams (side "mine") or their opponents' ("opp").
        Averages are per team per game, so a side with more teams isn't made to look busier.
        Only what can be seen in a replay: nothing about anyone's trees."""
        row = self._query(player_id, filters, f"""
            select count(*) as teams, count(s.game_id) as counted,
                   avg(s.kills) as kills, avg(s.deaths) as deaths, avg(s.births) as births,
                   avg(s.damage_dealt) as damage_dealt, avg(s.damage_taken) as damage_taken,
                   avg(s.blocks) as blocks, avg(s.food_eaten) as food_eaten, avg(s.peak_agents) as peak_agents,
                   sum(s.confused) as confused,
                   (select sum(a.succeeded) from team_actions a join {side} x using (game_id, slot)
                    where a.action <> 'CONFUSED') as succeeded,
                   (select sum(a.succeeded + a.failed) from team_actions a join {side} x using (game_id, slot)) as decisions
            from {side} m left join team_stats s using (game_id, slot)""")[0]
        actions = self._query(player_id, filters, f"""
            select a.action, sum(a.succeeded) as succeeded, sum(a.failed) as failed
            from team_actions a join {side} m using (game_id, slot)
            group by 1 order by sum(a.succeeded + a.failed) desc, 1""")
        decisions = row["decisions"] or 0
        confused = row["confused"] or 0
        names = {"kills": "kills", "deaths": "deaths", "births": "births", "damage_dealt": "damageDealt",
                 "damage_taken": "damageTaken", "blocks": "blocks", "food_eaten": "foodEaten",
                 "peak_agents": "peakAgents"}
        return {
            "teams": row["teams"], "counted": row["counted"], "decisions": decisions,
            "averages": {name: None if row[column] is None else round(float(row[column]), 1)
                         for column, name in names.items()},
            "confusedRate": round(confused / decisions, 3) if decisions else None,
            "successRate": round((row["succeeded"] or 0) / (decisions - confused), 3) if decisions > confused else None,
            "actions": [{"key": r["action"], "label": r["action"], "succeeded": r["succeeded"], "failed": r["failed"]}
                        for r in actions],
        }

    def _timeline(self, player_id: str, filters: Filters) -> dict[str, Any]:
        """The average number of agents per team and their total health at each turn, for the
        player's teams and for their opponents, over the games still going at that turn. Long
        games are thinned to about TIMELINE_POINTS turns."""
        sides = {}
        for name, side in (("you", "mine"), ("opponents", "opp")):
            sides[name] = {r["turn"]: r for r in self._query(player_id, filters, f"""
                select i - 1 as turn, avg(s.agents[i]) as agents, avg(s.health[i]) as health,
                       count(distinct m.game_id) as games
                from {side} m join team_stats s using (game_id, slot), generate_subscripts(s.agents, 1) as i
                group by i order by i""")}
        last = max((max(rows, default=-1) for rows in sides.values()), default=-1)
        step = max(1, -(-(last + 1) // TIMELINE_POINTS))
        turns = [turn for turn in range(last + 1) if turn % step == 0 or turn == last]

        def series(rows: dict, field: str, digits: int) -> list:
            return [None if turn not in rows else round(float(rows[turn][field]), digits) for turn in turns]

        return {"turns": turns, **{name: {"agents": series(rows, "agents", 2), "health": series(rows, "health", 1),
                                          "games": [rows[turn]["games"] if turn in rows else 0 for turn in turns]}
                                   for name, rows in sides.items()}}

    def _games(self, player_id: str, filters: Filters) -> list[dict[str, Any]]:
        rows = self._query(player_id, filters, f"""
            select m.*, s.kills, s.deaths, s.peak_agents,
                   (select string_agg(o.name, ', ' order by o.slot) from game_teams o
                    where o.game_id = m.game_id and o.slot <> m.slot) as opponents
            from mine m left join team_stats s using (game_id, slot)
            order by m.created_at desc, m.game_id limit {RECENT_GAMES}""")
        versions = self.versions(player_id, sorted({r["tree_key"] for r in rows}))
        labels = {(k, v["key"]): v["label"] for k, vs in versions.items() for v in vs}
        return [{"id": r["game_id"], "created": iso(r["created_at"]), "mode": r["mode"], "map": r["map_key"],
                 "mapName": r["map_name"], "tree": r["tree_key"], "treeName": r["start_tree"],
                 "version": r["tree_hash"], "versionLabel": labels.get((r["tree_key"], r["tree_hash"])),
                 "place": r["place"], "teams": r["team_count"], "won": r["won"], "turns": r["turns"],
                 "xp": r["xp"], "kills": r["kills"], "deaths": r["deaths"], "opponents": r["opponents"]}
                for r in rows]

    # ---- filter choices ---------------------------------------------------------------------------

    def options(self, player_id: str) -> dict[str, Any]:
        """What each filter can be set to: the values that appear in the player's finished games."""
        everything = Filters()
        trees = self._by_tree(player_id, everything)
        versions = self.versions(player_id)
        for tree in trees:
            tree["versions"] = versions.get(tree["key"], [])
        span = self._query(player_id, everything, "select min(created_at) as first, max(created_at) as last from mine")[0]
        return {
            "trees": trees,
            "maps": self._by_map(player_id, everything, order="2"),
            "opponents": self._by_opponent(player_id, everything, order="2"),
            "modes": self._breakdown(player_id, everything, "m.mode", "initcap(m.mode)"),
            "seasons": self._breakdown(player_id, everything, "m.season_id",
                                       "(select s.name from seasons s where s.id = m.season_id)",
                                       source="mine m where m.season_id is not null", order="2"),
            "first": iso(span["first"]), "last": iso(span["last"]),
        }

    # ---- a tree's nodes ---------------------------------------------------------------------------

    def nodes(self, player_id: str, filters: Filters) -> dict[str, Any] | None:
        """How often each node of one version of one tree was visited, over the filtered games.
        Node ids differ between versions, so this needs a single tree; the version defaults to
        the newest one in the filtered games. Returns None if there are no such games."""
        if len(filters.trees) != 1:
            raise AnalyticsError("Choose one tree to see how its nodes were used")
        if len(filters.versions) > 1:
            raise AnalyticsError("Choose one version of the tree to see how its nodes were used")
        newest = self._query(player_id, filters, """
            select m.tree_hash, m.game_id, m.slot from mine m order by m.created_at desc, m.game_id limit 1""")
        if not newest:
            return None
        version = newest[0]["tree_hash"]
        filters = Filters(**{**filters.__dict__, "versions": [version]})
        team = self.db.one("select start_tree, trees from game_teams where game_id = %s and slot = %s",
                           (newest[0]["game_id"], newest[0]["slot"]))
        rows = self._query(player_id, filters, """
            select v.tree_name, v.node_id, sum(v.visits) as visits, sum(v.confused) as confused
            from team_node_visits v join mine m using (game_id, slot) group by 1, 2 order by 1, 2""")
        games = self._query(player_id, filters, "select count(*) as games, count(s.game_id) as counted "
                                                "from mine m left join team_stats s using (game_id, slot)")[0]
        visits: dict[str, dict[int, dict[str, int]]] = {}
        for r in rows:
            visits.setdefault(r["tree_name"], {})[r["node_id"]] = {"visits": r["visits"], "confused": r["confused"]}
        label = next((v["label"] for v in self.versions(player_id, filters.trees).get(filters.trees[0], [])
                      if v["key"] == version), None)
        return {"tree": filters.trees[0], "version": version, "versionLabel": label, "games": games["games"],
                "counted": games["counted"], "startTree": team["start_tree"], "trees": team["trees"],
                "visits": {name: {str(node): v for node, v in nodes.items()} for name, nodes in visits.items()}}


# ---- counting older games ------------------------------------------------------------------------


def backfill(catalogue: Catalogue, limit: int | None = None) -> dict[str, Any]:
    """Count the stats of finished games that don't have them yet (or were counted by an older
    version of stats.py) by replaying them. A replay that doesn't end the way the saved result
    did is reported and left uncounted. Returns {"counted", "mismatched": [game ids]}."""
    ids = [r["game_id"] for r in catalogue.db.query(f"""
        select r.game_id from results r join games g on g.id = r.game_id
        where exists (select 1 from game_teams t left join team_stats s using (game_id, slot)
                      where t.game_id = r.game_id and (s.game_id is null or s.stats_version < %s))
        order by g.created_at {f'limit {int(limit)}' if limit else ''}""", (STATS_VERSION,))]
    counted, mismatched = 0, []
    for game_id in ids:
        record = catalogue.get("games", game_id)
        saved = catalogue.result(game_id)
        world = run_to_end(record)
        if world.result["turns"] != saved["turns"] or (
                [(p["slot"], p["place"]) for p in world.result["placements"]]
                != [(p["slot"], p["place"]) for p in saved["placements"]]):
            mismatched.append(game_id)
            continue
        catalogue.save_stats(game_id, world.players)
        counted += 1
    return {"counted": counted, "mismatched": mismatched}


__all__ = ["Analytics", "AnalyticsError", "Filters", "backfill"]
