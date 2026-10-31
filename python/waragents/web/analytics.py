"""Analytics: charts of how your trees have done, over your own finished games (analytics.py).

Every view takes the filters described in analytics.py as query parameters.
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, Response, abort, current_app, request

from ..analytics import Analytics, AnalyticsError, Filters
from ..export import export
from .auth import me

bp = Blueprint("analytics", __name__)


def _analytics() -> Analytics:
    return Analytics(current_app.extensions["waragents"]["catalogue"])


def _filters() -> Filters:
    try:
        return Filters.parse(request.args)
    except AnalyticsError as e:
        abort(422, str(e))


@bp.get("/api/analytics")
def summary():
    """Everything the Analytics screen charts: headline numbers, results over time, by tree, tree
    version, map, opponent and mode, the action mix, agents over a game, and the games."""
    return _analytics().summary(me()["id"], _filters())


@bp.get("/api/analytics/options")
def options():
    """What each filter can be set to, from your finished games, with your trees' versions."""
    return _analytics().options(me()["id"])


@bp.get("/api/analytics/nodes")
def nodes():
    """How often each node of one tree (tree=) was visited, for one version (version=, the newest
    by default), over the filtered games, with the copy of the tree that played."""
    try:
        found = _analytics().nodes(me()["id"], _filters())
    except AnalyticsError as e:
        abort(422, str(e))
    if found is None:
        abort(404, "None of your games pass these filters with that tree")
    return found



@bp.get("/api/analytics/export")
def export_games():
    """Every turn of your finished games that pass the filters, as a zip of CSV files. See
    export.py for what's in it."""
    filters, user = _filters(), me()
    catalogue = current_app.extensions["waragents"]["catalogue"]
    name = f"waragents-{user['id']}-{date.today().isoformat()}.zip"
    return Response(export(catalogue, user["id"], filters), mimetype="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
