import sqlite3

import pytest

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.pipeline_results import summarize_outcomes


def test_read_only_store_does_not_create_or_migrate(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        FeatureStore(path, read_only=True)
    assert not path.exists()
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE marker(value)")
    before = path.read_bytes()
    with FeatureStore(path, read_only=True) as store:
        assert store._conn.execute("SELECT name FROM sqlite_master").fetchall()[0][0] == "marker"
        with pytest.raises(sqlite3.OperationalError):
            store._conn.execute("CREATE TABLE forbidden(value)")
    assert path.read_bytes() == before


def test_source_failure_is_not_no_opportunity():
    assert summarize_outcomes({"a": "SOURCE_UNAVAILABLE"})["run_status"] == "FAILED"
    assert summarize_outcomes({"a": "FILTERED"})["run_status"] == "SUCCEEDED"
    assert summarize_outcomes({"a": "SUCCEEDED", "b": "FAILED"})["run_status"] == "PARTIAL"
