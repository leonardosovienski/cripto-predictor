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
    if max_age < timedelta(0):
        raise ValueError("max_age must not be negative")
    if not path.exists():
        return StoreHealth(StoreState.MISSING)
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                return StoreHealth(StoreState.CORRUPT)
            # ISO timestamps with different offsets do not sort chronologically
            # as text. Compare actual instants, preserving the fail-closed policy
            # for malformed or timezone-naive observations.
            latest = None
            for (raw_timestamp,) in connection.execute(
                "SELECT DISTINCT ts FROM features_aligned WHERE ts IS NOT NULL"
            ):
                try:
                    timestamp = datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
                except ValueError:
                    return StoreHealth(StoreState.CORRUPT)
                if timestamp.tzinfo is None:
                    return StoreHealth(StoreState.CORRUPT)
                timestamp = timestamp.astimezone(UTC)
                if latest is None or timestamp > latest:
                    latest = timestamp
        finally:
            connection.close()
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        return StoreHealth(StoreState.CORRUPT)
    if latest is None:
        return StoreHealth(StoreState.EMPTY)
    if latest > now.astimezone(UTC):
        return StoreHealth(StoreState.CORRUPT, latest)
    state = StoreState.STALE if now.astimezone(UTC) - latest > max_age else StoreState.READY
    return StoreHealth(state, latest)
