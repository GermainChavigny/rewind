"""Command-line entry point: `rewind serve`, `rewind import-v1`…"""

from __future__ import annotations

import argparse
import logging
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
    imp.add_argument("--app", type=Path, default=Path.home() / "app_tv")
    imp.add_argument("--xinitrc", type=Path, default=Path.home() / ".xinitrc")
    imp.add_argument(
        "--overwrite-config",
        action="store_true",
        help="regenerate config.toml from v1 even if it already exists",
    )

    get = sub.add_parser("config-get", help="print a config value, e.g. display.mode")
    get.add_argument("key")

    args = parser.parse_args(argv)

    if args.command == "config-get":
        from rewind.config import ConfigStore
        from rewind.paths import Paths

        value: object = ConfigStore(Paths.from_env().config / "config.toml").get()
        for part in args.key.split("."):
            value = getattr(value, part, None)
        print("" if value is None else value)
        return 0

    if args.command == "serve":
        import uvicorn

        from rewind.app import create_app

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        uvicorn.run(create_app(), host=args.host, port=args.port)
        return 0

    if args.command == "import-v1":
        from rewind.paths import Paths
        from rewind.tools.import_v1 import import_v1
        from rewind.tools.migrate_v1 import migrate_v1

        paths = Paths.from_env().ensure()
        report = import_v1(args.tv_data, args.movies, paths, args.app, args.xinitrc)
        print(report.summary())
        if not report.ok:
            return 1
        print(migrate_v1(paths, overwrite_config=args.overwrite_config).summary())
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
