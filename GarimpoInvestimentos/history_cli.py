"""Explicit history access; reading never loads credentials or migrates a database."""

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 1000:
        parser.error("limit must be between 1 and 1000")
    with closing(sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY ts DESC,ativo LIMIT ?", (args.limit,)
        )
        print(json.dumps([dict(row) for row in rows], ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
