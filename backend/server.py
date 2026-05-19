"""Server entrypoint for the study room reservation backend."""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from backend.api import create_handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus study room reservation API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--db", default="study_rooms.sqlite3")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), create_handler(args.db))
    print("Serving study room API on http://{}:{}".format(args.host, args.port))
    server.serve_forever()


if __name__ == "__main__":
    main()

