"""Run the web app, or manage accounts.

    python -m waragents.web [--host HOST] [--port PORT] [--reload] [--catalogue DIR]
    python -m waragents.web set-password PLAYER [--admin | --not-admin] [--catalogue DIR]
"""

import argparse
import getpass
import os
import sys


def serve(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Run the WarAgents web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart when code changes")
    parser.add_argument("--catalogue", help="folder for maps, trees, players and games "
                                            "(default: python/catalogue)")
    args = parser.parse_args(argv)
    if args.catalogue:
        # An environment variable rather than an argument, so the reloader's child process sees it.
        os.environ["WARAGENTS_CATALOGUE"] = args.catalogue

    from .app import app

    print(f"WarAgents running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, use_reloader=args.reload, threaded=True)


def set_password(argv: list[str]) -> None:
    """Give a player a password, for players made before accounts had them (or a forgotten one)."""
    parser = argparse.ArgumentParser(prog="python -m waragents.web set-password",
                                     description="Set a player's password")
    parser.add_argument("player", help="the player's id (their username)")
    admin = parser.add_mutually_exclusive_group()
    admin.add_argument("--admin", action="store_true", default=None, help="make them an admin")
    admin.add_argument("--not-admin", dest="admin", action="store_false", help="stop them being an admin")
    parser.add_argument("--catalogue", help="the catalogue folder (default: python/catalogue)")
    args = parser.parse_args(argv)

    from ..catalogue import Catalogue, CatalogueError, NotFound
    from .app import DEFAULT_CATALOGUE
    from .auth import MIN_PASSWORD
    from .auth import set_password as save

    catalogue = Catalogue(args.catalogue or os.environ.get("WARAGENTS_CATALOGUE") or DEFAULT_CATALOGUE)
    if not catalogue.exists("players", args.player):
        sys.exit(f"There's no player '{args.player}'")
    password = getpass.getpass(f"New password for {args.player}: ")
    if len(password) < MIN_PASSWORD:
        sys.exit(f"Passwords need at least {MIN_PASSWORD} characters")
    if getpass.getpass("Again: ") != password:
        sys.exit("The passwords don't match")
    try:
        save(catalogue, args.player, password, args.admin)
    except (CatalogueError, NotFound) as e:
        sys.exit(str(e))
    print(f"Password set for {args.player}")


def main() -> None:
    try:
        import flask  # noqa: F401
    except ImportError:
        sys.exit(f"Flask isn't installed for this Python ({sys.executable}).\n"
                 "Activate the project's virtual environment first (.venv\\Scripts\\activate, or "
                 "source .venv/bin/activate on macOS/Linux), or install it with: pip install -e .")
    argv = sys.argv[1:]
    if argv[:1] == ["set-password"]:
        set_password(argv[1:])
    else:
        serve(argv)


if __name__ == "__main__":
    main()
