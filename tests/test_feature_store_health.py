import sqlite3
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
