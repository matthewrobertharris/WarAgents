"""Run the web app: python -m waragents.web [--host HOST] [--port PORT] [--reload]"""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WarAgents web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart when code changes")
    args = parser.parse_args()
    print(f"WarAgents running at http://{args.host}:{args.port}")
    uvicorn.run("waragents.web.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
