"""Set up and look after the database.

    python -m waragents.db setup            apply the migrations, load the bundled content, count stats
    python -m waragents.db migrate          apply the migrations that haven't been yet
    python -m waragents.db seed             load (or reload) the bundled maps, trees and tutorials
    python -m waragents.db import FOLDER    copy a JSON catalogue folder (the old storage) in
    python -m waragents.db stats            count the analytics stats of games that don't have them
    python -m waragents.db status           the migrations, and how many of everything there are

Every command uses WARAGENTS_DATABASE_URL (or a python/.env file), or --database-url.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import Database, DatabaseNotReady, database_url
from .migrate import applied, available, migrate, require_current


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m waragents.db", description="Look after the WarAgents database")
    parser.add_argument("--database-url", help="the database to use (default: WARAGENTS_DATABASE_URL)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="apply the migrations, load the bundled content, count stats")
    commands.add_parser("migrate", help="apply the migrations that haven't been yet")
    seed_command = commands.add_parser("seed", help="load the bundled maps, trees and tutorials")
    seed_command.add_argument("--content", type=Path, help="the content folder (default: python/content)")
    import_command = commands.add_parser("import", help="copy a JSON catalogue folder into the database")
    import_command.add_argument("folder", type=Path)
    commands.add_parser("stats", help="count the analytics stats of games that don't have them, by replaying them")
    commands.add_parser("status", help="show the migrations and how many of everything there are")
    args = parser.parse_args(argv)

    try:
        db = Database(args.database_url or database_url())
    except DatabaseNotReady as e:
        sys.exit(str(e))
    try:
        run(db, args)
    except DatabaseNotReady as e:
        sys.exit(str(e))
    finally:
        db.close()


def run(db: Database, args: argparse.Namespace) -> None:
    from ..catalogue import KINDS, Catalogue, CatalogueError
    from ..content import CONTENT_DIR, import_folder, seed

    if args.command in ("setup", "migrate"):
        names = migrate(db)
        print(f"Applied {', '.join(names)}" if names else "The schema is up to date")
    if args.command in ("setup", "seed"):
        require_current(db)
        root = getattr(args, "content", None) or CONTENT_DIR
        try:
            counts = seed(Catalogue(db), root)
        except CatalogueError as e:
            sys.exit("Nothing was loaded:\n  " + "\n  ".join(e.problems))
        print("Loaded " + ", ".join(f"{n} {kind}" for kind, n in counts.items()) + f" from {root}")
    if args.command == "import":
        require_current(db)
        if not args.folder.is_dir():
            sys.exit(f"There's no folder {args.folder}")
        report = import_folder(Catalogue(db), args.folder)
        for kind, outcome in report.items():
            print(f"{kind:10} {outcome['added']} added, {outcome['skipped']} already there"
                  + (f", {len(outcome['failed'])} failed" if outcome["failed"] else ""))
            for failure in outcome["failed"]:
                print(f"    {failure['id']}: {failure['problem']}")
    if args.command in ("setup", "import", "stats"):
        from ..analytics import backfill

        require_current(db)
        outcome = backfill(Catalogue(db))
        if outcome["counted"] or args.command == "stats":
            print(f"Counted the stats of {outcome['counted']} game(s) by replaying them")
        for game_id in outcome["mismatched"]:
            print(f"    {game_id}: its replay didn't end the way its result says, so it wasn't counted")
    if args.command == "status":
        done = applied(db)
        for version, path in available():
            print(f"{'applied' if version in done else 'PENDING':8} {path.name}")
        if done:
            catalogue = Catalogue(db)
            print(", ".join(f"{catalogue.count(kind)} {kind}" for kind in KINDS))


if __name__ == "__main__":
    main()
