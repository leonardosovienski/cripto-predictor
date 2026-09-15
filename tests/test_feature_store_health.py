import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta

from GarimpoInvestimentos.feature_store_health import StoreState, inspect_feature_store

NOW = datetime(2026, 8, 1, tzinfo=UTC)


def _db(path, timestamp=None):
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE features_aligned (ts TEXT)")
    if timestamp:
        connection.execute("INSERT INTO features_aligned VALUES (?)", (timestamp,))
    connection.commit()
    connection.close()


def test_empty_feature_store(tmp_path):
    path = tmp_path / "empty.db"
    _db(path)
    assert inspect_feature_store(path, now=NOW, max_age=timedelta(days=2)).state == StoreState.EMPTY


def test_corrupt_feature_store(tmp_path):
    path = tmp_path / "corrupt.db"
    path.write_bytes(b"not sqlite")
    assert (
        inspect_feature_store(path, now=NOW, max_age=timedelta(days=2)).state == StoreState.CORRUPT
    )


def test_stale_feature_store(tmp_path):
    path = tmp_path / "stale.db"
    _db(path, "2026-07-01T00:00:00+00:00")
    assert inspect_feature_store(path, now=NOW, max_age=timedelta(days=2)).state == StoreState.STALE


def test_future_observation_cannot_hide_behind_larger_timestamp_text(tmp_path):
    path = tmp_path / "mixed-offsets.db"
    _db(path, "2026-07-31T23:30:00-02:00")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("INSERT INTO features_aligned VALUES (?)", (NOW.isoformat(),))
    health = inspect_feature_store(path, now=NOW, max_age=timedelta(days=2))
    assert health.state == StoreState.CORRUPT
    assert health.latest_timestamp == datetime(2026, 8, 1, 1, 30, tzinfo=UTC)


def test_freshness_uses_latest_instant_across_offsets(tmp_path):
    path = tmp_path / "fresh-offset.db"
    _db(path, "2026-07-29T23:30:00-02:00")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "INSERT INTO features_aligned VALUES (?)", ("2026-07-30T00:30:00+03:00",)
        )
    health = inspect_feature_store(path, now=NOW, max_age=timedelta(days=2))
    assert health.state == StoreState.READY
    assert health.latest_timestamp == datetime(2026, 7, 30, 1, 30, tzinfo=UTC)


def test_malformed_timestamp_cannot_hide_behind_valid_observation(tmp_path):
    path = tmp_path / "malformed.db"
    _db(path, NOW.isoformat())
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("INSERT INTO features_aligned VALUES ('!invalid')")
    assert (
        inspect_feature_store(path, now=NOW, max_age=timedelta(days=2)).state == StoreState.CORRUPT
    )
