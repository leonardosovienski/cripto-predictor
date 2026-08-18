import asyncio
import json
import zlib
from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.trading.binance_spot_collector import (
    BboObservation,
    BinanceSpotCollector,
    DepthObservation,
    DepthSynchronizer,
    TradeObservation,
    parse_stream_message,
)
from GarimpoInvestimentos.trading.contracts import Instrument
from GarimpoInvestimentos.trading.microstructure import (
    CollectedOrderBook,
    DepthSequenceGap,
    DepthUpdate,
    OrderBookLevel,
    OrderBookSnapshot,
)
from GarimpoInvestimentos.trading.microstructure_quality import daily_scorecards, watchdog
from GarimpoInvestimentos.trading.store import TradingStore

T0 = datetime(2026, 8, 18, 12, tzinfo=UTC)
I = Instrument("BTCUSDT", "binance_spot", "crypto_spot")


def snapshot(last=10):
    book = OrderBookSnapshot(I, T0, (OrderBookLevel(99, 2),), (OrderBookLevel(101, 2),))
    return CollectedOrderBook(book, last, T0, T0, T0)


def depth(first=11, final=11, received=T0, bids=((99.0, 1.0),), asks=()):
    return DepthObservation(DepthUpdate(I, first, final, T0, bids, asks), received, "session")


def test_snapshot_buffer_bridge_and_old_discard():
    sync = DepthSynchronizer(I)
    sync.buffer(depth(9, 10))
    sync.buffer(depth(10, 11, bids=((98.0, 3.0),)))
    book = sync.install_snapshot(snapshot())
    assert book.last_update_id == 11
    assert book.snapshot().bids[-1].price == 98


def test_first_applicable_gap_invalidates_book():
    sync = DepthSynchronizer(I)
    sync.buffer(depth(12, 12))
    with pytest.raises(DepthSequenceGap):
        sync.install_snapshot(snapshot())
    assert sync.book is None


def test_live_gap_invalidates_and_buffer_overflow_is_explicit():
    sync = DepthSynchronizer(I, max_events=1)
    sync.install_snapshot(snapshot())
    with pytest.raises(DepthSequenceGap):
        sync.apply(depth(12, 12))
    assert sync.book is None
    sync.buffer(depth())
    with pytest.raises(BufferError):
        sync.buffer(depth(12, 12, received=T0 + timedelta(milliseconds=1)))


def test_instrument_and_timestamp_divergence():
    sync = DepthSynchronizer(I)
    other = Instrument("ETHUSDT", "binance_spot", "crypto_spot")
    with pytest.raises(ValueError, match="divergente"):
        sync.buffer(DepthObservation(DepthUpdate(other, 1, 1, T0, (), ()), T0, "s"))
    sync.buffer(depth(received=T0 + timedelta(seconds=1)))
    with pytest.raises(ValueError, match="fora de ordem"):
        sync.buffer(depth(12, 12, received=T0))


def test_parse_documented_trade_bookticker_and_depth_payloads():
    trade = {
        "e": "trade",
        "E": 1672515782136,
        "s": "BTCUSDT",
        "t": 12345,
        "p": "0.001",
        "q": "100",
        "T": 1672515782136,
        "m": True,
    }
    bbo = {
        "u": 400900217,
        "s": "BTCUSDT",
        "b": "25.35190000",
        "B": "31.21000000",
        "a": "25.36520000",
        "A": "40.66000000",
    }
    dep = {
        "e": "depthUpdate",
        "E": 1672515782136,
        "s": "BTCUSDT",
        "U": 157,
        "u": 160,
        "b": [["0.0024", "10"]],
        "a": [["0.0026", "100"]],
    }
    assert isinstance(
        parse_stream_message(json.dumps(trade), received_at=T0, session_id="s"), TradeObservation
    )
    assert isinstance(parse_stream_message(bbo, received_at=T0, session_id="s"), BboObservation)
    assert isinstance(parse_stream_message(dep, received_at=T0, session_id="s"), DepthObservation)


def test_persistence_idempotency_conflict_restart_watchdog_and_scorecard(tmp_path):
    path = tmp_path / "micro.db"
    trade = TradeObservation(I, 1, 100, 2, True, T0, T0, T0, "s")
    with TradingStore(path) as store:
        assert store.append_trade(trade)
        assert not store.append_trade(trade)
        with pytest.raises(ValueError, match="hash conflitante"):
            store.append_trade(TradeObservation(I, 1, 101, 2, True, T0, T0, T0, "s"))
    with TradingStore(path) as store:
        rows = store.quality_rows(T0 - timedelta(seconds=1), T0 + timedelta(seconds=1))
        assert len(rows) == 1 and rows[0]["scientific_state"] == "COLLECTION_ONLY"
        findings = watchdog(store, now=T0 + timedelta(minutes=1), stale_seconds=1)
        assert any(x.reason.startswith("stale") for x in findings)
        cards = daily_scorecards(store, T0.date())
        assert len(cards) == 8
        assert all(x["status"] in {"DEGRADED", "OBSERVED_NOT_PROMOTED"} for x in cards)


def test_zero_quantity_removes_level_and_crossed_book_fails():
    sync = DepthSynchronizer(I)
    sync.install_snapshot(snapshot())
    sync.apply(depth(asks=((101.0, 0.0), (102.0, 1.0))))
    assert sync.book.snapshot().best_ask == 102
    with pytest.raises(DepthSequenceGap):
        sync.apply(depth(12, 12, bids=((103.0, 1.0),)))


def test_gap_triggers_resnapshot(tmp_path):
    calls = 0

    async def fetcher(symbol):
        nonlocal calls
        calls += 1
        assert symbol == "BTCUSDT"
        return snapshot(last=20 if calls > 1 else 10)

    payload = {
        "e": "depthUpdate",
        "E": int(T0.timestamp() * 1000),
        "s": "BTCUSDT",
        "U": 12,
        "u": 12,
        "b": [["99", "1"]],
        "a": [],
    }

    async def scenario():
        with TradingStore(tmp_path / "gap.db") as store:
            collector = BinanceSpotCollector(store, ("BTCUSDT",), snapshot_fetcher=fetcher)
            await collector.resnapshot("BTCUSDT")
            await collector.handle(json.dumps(payload), received_at=T0)
            assert calls == 2
            assert collector.synchronizers["BTCUSDT"].book.last_update_id == 20

    asyncio.run(scenario())


def test_collector_has_no_order_or_paper_trading_imports():
    from GarimpoInvestimentos.trading import binance_spot_collector

    source = open(binance_spot_collector.__file__, encoding="utf-8").read()
    assert "paper_trader" not in source
    assert "TradeIntent" not in source
    assert "ExchangeAdapter" not in source


def test_heartbeat_is_rate_limited(tmp_path, monkeypatch):
    ticks = iter((10.0, 11.0, 15.0))
    monkeypatch.setattr("GarimpoInvestimentos.trading.store.time.monotonic", lambda: next(ticks))
    with TradingStore(tmp_path / "heartbeat.db") as store:
        assert store.heartbeat(min_interval_seconds=5)
        assert not store.heartbeat(min_interval_seconds=5)
        assert store.heartbeat(min_interval_seconds=5)
        count = store._conn.execute(
            "SELECT COUNT(*) FROM collector_health WHERE metric='heartbeat'"
        ).fetchone()[0]
        assert count == 2


def test_new_events_use_compressed_storage_and_v1_migration_is_lossless(tmp_path):
    path = tmp_path / "compressed.db"
    trade = TradeObservation(I, 77, 100, 2, True, T0, T0, T0, "s")
    with TradingStore(path) as store:
        assert store.append_trade(trade)
        assert store._conn.execute("SELECT COUNT(*) FROM microstructure_events").fetchone()[0] == 0
        blob = store._conn.execute("SELECT payload_zlib FROM microstructure_events_v3").fetchone()[
            0
        ]
        assert isinstance(blob, bytes)
        assert store.quality_rows(T0 - timedelta(seconds=1), T0 + timedelta(seconds=1))[0][
            "payload_json"
        ]

        # Simulate one legacy row and prove it survives the additive migration.
        row = store._conn.execute("SELECT * FROM microstructure_events_v3").fetchone()
        payload = zlib.decompress(row["payload_zlib"]).decode()
        store._conn.execute(
            """INSERT INTO microstructure_events
            (kind,observation_id,venue,symbol,sequence_id,event_at,received_at,ingested_at,
             session_id,collector_version,payload_hash,payload_json,quality_flags,scientific_state)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "trade",
                "legacy-78",
                "binance_spot",
                "BTCUSDT",
                78,
                T0.isoformat(),
                T0.isoformat(),
                T0.isoformat(),
                "legacy-session",
                "binance_spot_microstructure_v1",
                row["payload_hash_blob"].hex(),
                payload,
                "[]",
                "COLLECTION_ONLY",
            ),
        )
        store._conn.commit()
        result = store.compact_microstructure_v1(batch_size=1)
        assert result == {"v1_before": 1, "processed": 1, "v1_after": 0}
        assert store.compact_microstructure_v2(batch_size=1) == {
            "v2_before": 1,
            "processed": 1,
            "v2_after": 0,
        }
        rows = store.quality_rows(T0 - timedelta(seconds=1), T0 + timedelta(seconds=1))
        assert len(rows) == 2
        assert {item["payload_hash"] for item in rows} == {row["payload_hash_blob"].hex()}


def test_snapshots_with_same_sequence_and_different_request_are_distinct(tmp_path):
    with TradingStore(tmp_path / "snapshots.db") as store:
        first = snapshot(last=10)
        second = CollectedOrderBook(
            first.snapshot,
            first.last_update_id,
            first.requested_at + timedelta(microseconds=1),
            first.received_at + timedelta(microseconds=1),
            first.ingested_at + timedelta(microseconds=1),
        )
        assert store.append_collected_snapshot(first, session_id="s")
        assert store.append_collected_snapshot(second, session_id="s")
        assert (
            store._conn.execute(
                "SELECT COUNT(*) FROM microstructure_events_v3 WHERE kind_code=4"
            ).fetchone()[0]
            == 2
        )
