"""The content that ships with the game, and moving JSON catalogues into the database.

python/content/ holds the system maps, default trees and tutorials as one JSON file per item, named
by its id:

    content/
      maps/skirmish.json
      trees/graze.json
      tutorials/movement-1.json

seed() loads them into the database, replacing what's there, so editing a file (or running
tools/make_tutorials.py) and seeding again updates the game. Maps and trees loaded this way have
no owner, which makes them system maps and default trees.

import_folder() copies a whole JSON catalogue, the way the game stored everything before it had a
database (maps, trees, players, games, results, tutorials and seasons folders), into the database,
keeping every id. Items that are already there are skipped, so it's safe to run twice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from .catalogue import Catalogue, CatalogueError, NotFound
from .scenario import ScenarioError

CONTENT_DIR = Path(__file__).resolve().parents[1] / "content"
SEEDED = ("maps", "trees", "tutorials")
# Players before what they own, tutorials before the players who completed them, and so on.
IMPORT_ORDER = ("tutorials", "players", "maps", "trees", "seasons", "games", "results")


def dumps(value: Any, indent: int = 0, width: int = 100) -> str:
    """JSON that keeps short objects and rows of numbers on one line, so files diff well."""
    compact = json.dumps(value, ensure_ascii=False)
    if not isinstance(value, (list, dict)) or not value or len(compact) + indent <= width:
        return compact
    pad = " " * (indent + 2)
    if isinstance(value, list):
        if not any(isinstance(v, (list, dict)) for v in value):
            return compact
        items = [pad + dumps(v, indent + 2, width) for v in value]
        return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"
    items = [f"{pad}{json.dumps(k, ensure_ascii=False)}: {dumps(v, indent + 2, width)}"
             for k, v in value.items()]
    return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"


def read(root: Path, kind: str) -> Iterator[tuple[str, dict[str, Any]]]:
    """The (id, item) pairs in root/kind/*.json, in id order."""
    for path in sorted((Path(root) / kind).glob("*.json"), key=lambda p: p.stem):
        yield path.stem, json.loads(path.read_text(encoding="utf-8"))


def seed(catalogue: Catalogue, root: Path = CONTENT_DIR, only: dict[str, list[str]] | None = None) -> dict[str, int]:
    """Load the bundled maps, trees and tutorials (or, with only, just the listed ids of each
    kind). Returns how many of each were loaded. Raises CatalogueError if one is wrong, and then
    loads none of them."""
    counts = {}
    with catalogue.atomic():
        for kind in SEEDED:
            counts[kind] = 0
            for item_id, data in read(root, kind):
                if only is not None and item_id not in only.get(kind, []):
                    continue
                if kind in ("maps", "trees"):
                    data = {**data, "owner": None}
                try:
                    if catalogue.exists(kind, item_id):
                        catalogue.update(kind, item_id, data)
                    else:
                        catalogue.create_with_id(kind, item_id, data)
                except CatalogueError as e:
                    raise CatalogueError([f"{kind}/{item_id}.json: {p}" for p in e.problems]) from e
                counts[kind] += 1
    return counts


def import_folder(catalogue: Catalogue, root: Path) -> dict[str, dict[str, Any]]:
    """Copy a JSON catalogue folder into the database. Returns, for each kind, how many items
    were "added" and "skipped" (already there), and the "failed" ones with the reason."""
    report: dict[str, dict[str, Any]] = {}
    for kind in IMPORT_ORDER:
        added, skipped, failed = 0, 0, []
        for item_id, data in read(root, kind):
            try:
                if catalogue.exists(kind, item_id):
                    skipped += 1
                    continue
                if kind == "games":
                    catalogue.import_game(item_id, data)
                elif kind == "results":
                    catalogue.save_result(item_id, data)
                else:
                    catalogue.create_with_id(kind, item_id, data)
                added += 1
            except (CatalogueError, ScenarioError, NotFound, KeyError, TypeError, ValueError) as e:
                failed.append({"id": item_id, "problem": str(e)})
        report[kind] = {"added": added, "skipped": skipped, "failed": failed}
    return report
