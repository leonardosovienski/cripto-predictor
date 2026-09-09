import asyncio
import sqlite3
from datetime import UTC, datetime

import pytest

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.snapshots import EVALUATION_CONTRACT, market_payload, serving_context
from tests.test_review_data_contracts import point


def snapshot(store, *, day=1, collected=None):
    p = point(day)
    data = market_payload(
        [p],
        [{"ts": p.timestamp, "price_usd": p.close}],
        {},
        collected_at=collected or p.published_at,
    )
    return store.write_market_snapshot(data)


def test_stale_market_cannot_consume_news_or_llm_budget(tmp_path):
    with FeatureStore(tmp_path / "store.db") as store:
        snapshot(store)
        with pytest.raises(ValueError, match="stale"):
            serving_context(store, "bitcoin", now=datetime(2026, 9, 9, tzinfo=UTC))


def test_snapshot_source_is_exact_and_recent_not_latest_raw_source(tmp_path):
    with FeatureStore(tmp_path / "store.db") as store:
        digest = snapshot(store)
        now = datetime(2026, 1, 3, 1, tzinfo=UTC)
        result = serving_context(store, "bitcoin", now=now)
        assert result["source"] == "binance"
        assert result["snapshot_id"] == digest
        assert result["normalized_candles"][0]["close"] == 100
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            store._conn.execute("UPDATE market_snapshots SET payload_json='{}'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            store._conn.execute("DELETE FROM market_snapshots")


def test_prediction_inputs_survive_restart_and_reject_conflict_atomically(tmp_path):
    db = tmp_path / "store.db"
    row = {
        "ativo": "BITCOIN",
        "ts": "2026-01-03 12:00:00",
        "score": 75,
        "price_usd": 100,
        "divergencia": 0,
        "fonte": "dpl:fallback",
        "input_snapshot": {"news_titles": ["original"], "evaluation_contract": EVALUATION_CONTRACT},
    }
    with FeatureStore(db) as store:
        store.write_predictions([row])
        store.write_predictions([row])
        with pytest.raises(ValueError, match="identity conflict"):
            store.write_predictions([row | {"input_snapshot": {"news_titles": ["revision"]}}])
        with pytest.raises(ValueError, match="cannot be replaced"):
            store.write_predictions([row | {"score": 99}])
    with FeatureStore(db) as store:
        assert store.read_prediction_input(row["ativo"], row["ts"])["news_titles"] == ["original"]
        assert store.read_predictions()[0]["score"] == 75
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            store._conn.execute("DELETE FROM prediction_inputs")


def test_failure_in_prediction_input_insert_rolls_back_prediction(tmp_path):
    with FeatureStore(tmp_path / "store.db") as store:
        store._conn.execute(
            "CREATE TRIGGER reject_input BEFORE INSERT ON prediction_inputs BEGIN SELECT RAISE(ABORT, 'injected storage failure'); END;"
        )
        with pytest.raises(sqlite3.IntegrityError):
            store.write_predictions(
                [
                    {
                        "ativo": "BITCOIN",
                        "ts": "2026-01-03 12:00:00",
                        "score": 75,
                        "divergencia": 0,
                        "fonte": "dpl:fallback",
                        "input_snapshot": {"x": 1},
                    }
                ]
            )
        assert store.read_predictions() == []


def test_new_evaluation_does_not_count_move_before_prediction(tmp_path, monkeypatch):
    from GarimpoInvestimentos.analyzers import backtest
    from GarimpoInvestimentos.core import history

    db = tmp_path / "store.db"
    with FeatureStore(db) as store:
        # Context close was 100. At next daily close and seven days later the
        # price is 200: future return is zero, not the legacy spurious +100%.
        store.write_raw([point(2, 200), point(9, 200)])
        store.write_predictions(
            [
                {
                    "ativo": "BITCOIN",
                    "ts": "2026-01-03 12:00:00",
                    "score": 75,
                    "price_usd": 100,
                    "divergencia": 0,
                    "fonte": "dpl:fallback",
                    "input_snapshot": {
                        "evaluation_contract": EVALUATION_CONTRACT,
                        "market_source": "binance",
                    },
                }
            ]
        )
    monkeypatch.setattr(backtest, "FEATURE_STORE_DB", db)
    monkeypatch.setattr(history, "HIST_CSV", str(tmp_path / "absent.csv"))

    async def forbidden(*args):
        raise AssertionError("new evaluation must not change provider or call network")

    monkeypatch.setattr(backtest, "_realized_price", forbidden)
    result = asyncio.run(backtest.enrich_with_realized_prices(backtest._load_rows()))[0]
    assert result["context_price"] == 100
    assert result["pred_price"] == 200
    assert result["var_d7_pct"] == 0
    assert result["var_d1_pct"] is None


def test_legacy_without_inputs_is_explicitly_excluded_by_default(tmp_path, monkeypatch):
    from GarimpoInvestimentos.analyzers import backtest
    from GarimpoInvestimentos.core import history

    db = tmp_path / "store.db"
    with FeatureStore(db) as store:
        store.write_predictions(
            [
                {
                    "ativo": "BITCOIN",
                    "ts": "2026-01-03 12:00:00",
                    "score": 75,
                    "price_usd": 100,
                    "divergencia": 0,
                    "fonte": "direct",
                }
            ]
        )
    monkeypatch.setattr(backtest, "FEATURE_STORE_DB", db)
    monkeypatch.setattr(history, "HIST_CSV", str(tmp_path / "absent.csv"))
    assert backtest._load_rows() == []
    assert len(backtest._load_rows(include_legacy=True)) == 1
