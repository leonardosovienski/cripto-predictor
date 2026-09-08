from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.trading.contracts import (
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from GarimpoInvestimentos.trading.microstructure import (
    OrderBookLevel,
    OrderBookSnapshot,
)
from GarimpoInvestimentos.trading.store import TradingStore

T0 = datetime(2026, 8, 17, 12, tzinfo=UTC)


def _order(status: OrderStatus = OrderStatus.NEW) -> Order:
    return Order(
        order_id="order-1",
        intent_id="intent-1",
        instrument=Instrument("BTCUSDT", "binance_spot", "crypto_spot"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=0.01,
        status=status,
        created_at=T0,
    )


def _book() -> OrderBookSnapshot:
    return OrderBookSnapshot(
        instrument=Instrument("BTCUSDT", "binance_spot", "crypto_spot"),
        timestamp=T0,
        bids=(OrderBookLevel(59_990, 1.0),),
        asks=(OrderBookLevel(60_010, 1.0),),
    )


def test_order_events_are_append_only_idempotent_and_collection_only(tmp_path):
    with TradingStore(tmp_path / "trading.db") as store:
        assert store.append_order_event(
            event_id="evt-1",
            order=_order(),
            event_at=T0,
            received_at=T0 + timedelta(milliseconds=5),
            ingested_at=T0 + timedelta(milliseconds=10),
        )
        assert not store.append_order_event(
            event_id="evt-1",
            order=_order(),
            event_at=T0,
            received_at=T0 + timedelta(milliseconds=5),
            ingested_at=T0 + timedelta(milliseconds=10),
        )
        events = store.order_events("order-1")
        assert len(events) == 1
        assert events[0].scientific_state == "COLLECTION_ONLY"
        assert len(events[0].payload_hash) == 64


def test_duplicate_order_event_with_other_content_is_rejected(tmp_path):
    with TradingStore(tmp_path / "trading.db") as store:
        kwargs = dict(
            event_id="evt-1",
            event_at=T0,
            received_at=T0,
            ingested_at=T0,
        )
        store.append_order_event(order=_order(), **kwargs)
        with pytest.raises(ValueError, match="conteúdo diferente"):
            store.append_order_event(order=_order(OrderStatus.ACCEPTED), **kwargs)


def test_temporal_order_is_enforced(tmp_path):
    with TradingStore(tmp_path / "trading.db") as store:
        with pytest.raises(ValueError, match="event_at <= received_at"):
            store.append_order_event(
                event_id="evt-1",
                order=_order(),
                event_at=T0,
                received_at=T0 - timedelta(milliseconds=1),
                ingested_at=T0,
            )


def test_order_book_is_hashed_idempotent_and_preserves_sequence(tmp_path):
    with TradingStore(tmp_path / "trading.db") as store:
        assert store.append_order_book(
            snapshot_id="book-1",
            snapshot=_book(),
            received_at=T0,
            ingested_at=T0,
            sequence_id=42,
        )
        assert not store.append_order_book(
            snapshot_id="book-1",
            snapshot=_book(),
            received_at=T0,
            ingested_at=T0,
            sequence_id=42,
        )
