from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path


class StoreState(StrEnum):
    READY = "READY"
    EMPTY = "EMPTY"
    CORRUPT = "CORRUPT"
    STALE = "STALE"
    MISSING = "MISSING"


@dataclass(frozen=True)
class StoreHealth:
    state: StoreState
    latest_timestamp: datetime | None = None


def inspect_feature_store(path: Path, *, now: datetime, max_age: timedelta) -> StoreHealth:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not path.exists():
        return StoreHealth(StoreState.MISSING)
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                return StoreHealth(StoreState.CORRUPT)
            row = connection.execute("SELECT max(ts) FROM features_aligned").fetchone()
        finally:
            connection.close()
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return StoreHealth(StoreState.CORRUPT)
    if row is None or row[0] is None:
        return StoreHealth(StoreState.EMPTY)
    latest = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
    if latest.tzinfo is None:
        return StoreHealth(StoreState.CORRUPT)
    latest = latest.astimezone(UTC)
    state = StoreState.STALE if now.astimezone(UTC) - latest > max_age else StoreState.READY
    return StoreHealth(state, latest)
