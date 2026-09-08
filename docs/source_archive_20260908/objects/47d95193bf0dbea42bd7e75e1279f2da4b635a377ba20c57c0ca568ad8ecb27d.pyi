import pathlib
import sqlite3

def connect(db_path: pathlib.Path | str, busy_timeout_ms: int = ...) -> sqlite3.Connection: ...
def run_migrations(conn: sqlite3.Connection, migrations: list[tuple[str, str]]) -> None: ...


