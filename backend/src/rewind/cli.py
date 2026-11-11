"""Command-line entry point: `rewind serve`, `rewind import-v1`…"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_PORT = 8080


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rewind", description="REWIND — a 90s TV experience")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run the server (API + UI)")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)

    imp = sub.add_parser(
        "import-v1",
        help="import a copy of the v1 data (never modifies v1)",
    )
    imp.add_argument("--tv-data", type=Path, default=Path.home() / "tv_data")
    imp.add_argument("--movies", type=Path, default=Path.home() / "movies")

    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        from rewind.app import create_app

        uvicorn.run(create_app(), host=args.host, port=args.port)
        return 0

    if args.command == "import-v1":
        from rewind.paths import Paths
        from rewind.tools.import_v1 import import_v1

        report = import_v1(args.tv_data, args.movies, Paths.from_env().ensure())
        print(report.summary())
        return 0 if report.ok else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
