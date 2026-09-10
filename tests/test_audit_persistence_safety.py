import hashlib
import zlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.dpl.derivatives import funding_signal_points
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.signals import SignalPoint
from GarimpoInvestimentos.feature_store_health import StoreState, inspect_feature_store
from GarimpoInvestimentos.trading.binance_spot_collector import TradeObservation
from GarimpoInvestimentos.trading.contracts import Instrument
from GarimpoInvestimentos.trading.store import TradingStore, _from_micros, _micros
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord

T = datetime(2026, 9, 10, tzinfo=UTC)
I = Instrument("BTCUSDT", "binance_spot", "crypto_spot")


def test_signal_batch_conflict_is_atomic(tmp_path):
    signal = SignalPoint("x", T, 1.0, "s", T, vintage=T)
    with FeatureStore(tmp_path / "db") as store:
        with pytest.raises(ValueError):
            store.write_signals([signal, replace(signal, value=2.0)])
        assert store.read_signals("s", "x") == []


def test_signal_without_content_hash_cannot_overwrite_same_vintage(tmp_path):
    signal = SignalPoint("x", T, 1.0, "s", T, vintage=T)
    with FeatureStore(tmp_path / "db") as store:
        store.write_signals([signal])
        with pytest.raises(ValueError):
            store.write_signals([replace(signal, value=2.0)])
        assert store.read_signals("s", "x")[0].value == 1.0


def test_old_history_can_be_recorded_as_receipt_without_backdating(tmp_path):
    old = T - timedelta(days=90)
    points = funding_signal_points(
        [FundingRecord("BTCUSDT", int(old.timestamp() * 1000), 0.0001, 100)], ingested_at=T
    )
    with FeatureStore(tmp_path / "db") as store:
        assert store.write_signals(points) == 1
        saved = store.read_signals("binance-futures", "BTCUSDT:funding_rate")[0]
        assert saved.published_at == T
        assert saved.timestamp == old


def test_feature_store_health_future_time_is_not_ready(tmp_path):
    path = tmp_path / "db"
    with FeatureStore(path) as store:
        store.write_features("BTC", "1d", [{"ts": T + timedelta(days=1), "x": 1.0}])
    assert inspect_feature_store(path, now=T, max_age=timedelta(days=2)).state is StoreState.CORRUPT


def test_microsecond_roundtrip_does_not_use_float_epoch():
    stamp = datetime(2250, 1, 1, 0, 0, 0, 1, tzinfo=UTC)
    assert datetime.fromisoformat(_from_micros(_micros(stamp))) == stamp


def _legacy_row(store, trade, *, price=100):
    store.append_trade(trade)
    dense = store._conn.execute(
        "SELECT * FROM microstructure_events_v3 WHERE observation_id=?", (str(trade.trade_id),)
    ).fetchone()
    # Obtain exact identity from actual row (the ID includes session/event details).
    if dense is None:
        dense = store._conn.execute(
            "SELECT * FROM microstructure_events_v3 ORDER BY received_us DESC LIMIT 1"
        ).fetchone()
    payload = zlib.decompress(dense["payload_zlib"]).decode()
    fields = (
        "kind",
        "observation_id",
        "venue",
        "symbol",
        "sequence_id",
        "event_at",
        "received_at",
        "ingested_at",
        "session_id",
        "collector_version",
        "payload_hash",
        "payload_json",
        "quality_flags",
        "scientific_state",
    )
    row = (
        "trade",
        dense["observation_id"],
        "binance_spot",
        "BTCUSDT",
        trade.trade_id,
        T.isoformat(),
        T.isoformat(),
        T.isoformat(),
        "s",
        "binance_spot_microstructure_v1",
        hashlib.sha256(payload.encode()).hexdigest(),
        payload,
        "[]",
        "COLLECTION_ONLY",
    )
    store._conn.execute(
        "INSERT INTO microstructure_events ("
        + ",".join(fields)
        + ") VALUES ("
        + ",".join("?" for _ in fields)
        + ")",
        row,
    )
    store._conn.commit()
    return row


def test_store_compaction_conflicting_metadata_keeps_source(tmp_path):
    with TradingStore(tmp_path / "db") as store:
        trade = TradeObservation(I, 1, 100, 1, True, T, T, T, "s")
        _legacy_row(store, trade)
        store.compact_microstructure_v1()
        # Dense row exists; change legacy metadata without changing payload/hash.
        store._conn.execute("UPDATE microstructure_events_v2 SET collector_version='conflicting'")
        store._conn.commit()
        with pytest.raises(ValueError, match="metadados"):
            store.compact_microstructure_v2(batch_size=1)
        assert (
            store._conn.execute("SELECT COUNT(*) FROM microstructure_events_v2").fetchone()[0] == 1
        )


def test_latest_store_does_not_decode_entire_history(tmp_path, monkeypatch):
    with TradingStore(tmp_path / "db") as store:
        for index in range(10):
            stamp = T + timedelta(seconds=index)
            store.append_trade(TradeObservation(I, index, 100, 1, True, stamp, stamp, stamp, "s"))
        calls = []
        original = zlib.decompress
        monkeypatch.setattr(zlib, "decompress", lambda value: (calls.append(1), original(value))[1])
        latest = store.latest_microstructure()
        assert len(latest) == 1
        assert len(calls) == 1


def test_export_untrusted_text_cannot_become_formula(tmp_path, monkeypatch):
    pytest.importorskip("openpyxl")
    from openpyxl import load_workbook

    from GarimpoInvestimentos.output import reporter

    monkeypatch.setattr(reporter, "OUTPUT_DIR", tmp_path)
    reporter.export_results(
        [
            {
                "ativo": "BTC",
                "resumo": "=1+1",
                "sentimento": "@SUM(1,2)",
                "data": "2026-09-10",
                "score": 60,
                "price_usd": 100,
            }
        ]
    )
    files = list(tmp_path.glob("*.xlsx"))
    wb = load_workbook(files[0], data_only=False)
    assert wb.active["D2"].data_type == "s"
    assert wb.active["D2"].value == "'=1+1"
    wb.close()
    assert "'=1+1" in next(tmp_path.glob("*.csv")).read_text(encoding="utf-8-sig")
