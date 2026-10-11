"""Run the web app: python -m waragents.web [--host HOST] [--port PORT] [--reload] [--catalogue DIR]"""

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WarAgents web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart when code changes")
    parser.add_argument("--catalogue", help="folder for maps, trees, players and games "
                                            "(default: python/catalogue)")
    args = parser.parse_args()
    if args.catalogue:
        # An environment variable rather than an argument, so the reloader's child process sees it.
        os.environ["WARAGENTS_CATALOGUE"] = args.catalogue

    from .app import app

    print(f"WarAgents running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, use_reloader=args.reload, threaded=True)


if __name__ == "__main__":
    main()
