"""CLI entrypoint: `loaded-dicewriter serve`."""

from __future__ import annotations

import argparse
import sys

import uvicorn

from loaded_dicewriter.settings import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loaded-dicewriter")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Start the local server (loopback by default)")
    serve.add_argument("--host", default=None, help="Bind host (default from config: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=None, help="Bind port (default: 8765)")
    serve.add_argument("--reload", action="store_true", help="Dev auto-reload")

    args = parser.parse_args(argv)
    settings = get_settings()

    if args.command == "serve":
        host = args.host or settings.server.host
        port = args.port or settings.server.port
        uvicorn.run(
            "loaded_dicewriter.app:app",
            host=host,
            port=port,
            reload=args.reload,
            factory=False,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
