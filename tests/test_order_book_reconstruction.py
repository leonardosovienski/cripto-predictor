from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.trading.contracts import Instrument
from GarimpoInvestimentos.trading.microstructure import (
    DepthSequenceGap,
    DepthUpdate,
    LocalOrderBook,
    OrderBookLevel,
    OrderBookSnapshot,
)

T0 = datetime(2026, 8, 17, 12, tzinfo=UTC)
INSTRUMENT = Instrument("BTCUSDT", "binance_spot", "crypto_spot")


def _local() -> LocalOrderBook:
    snapshot = OrderBookSnapshot(
        INSTRUMENT,
        T0,
        (OrderBookLevel(99, 2), OrderBookLevel(98, 3)),
        (OrderBookLevel(101, 2), OrderBookLevel(102, 3)),
    )
    return LocalOrderBook(snapshot, last_update_id=10)


def _update(first=11, final=11, bids=((99.0, 1.0),), asks=((101.0, 0.0),)):
    return DepthUpdate(
        INSTRUMENT,
        first,
        final,
        T0 + timedelta(milliseconds=100),
        bids,
        asks,
    )


def test_diff_depth_updates_and_removes_levels():
    book = _local()
    assert book.apply(_update(asks=((101.0, 0.0), (100.5, 4.0))))
    current = book.snapshot()
    assert book.last_update_id == 11
    assert current.best_bid == 99
    assert current.best_ask == 100.5
    assert current.bids[0].qty == 1


def test_old_duplicate_update_is_idempotently_ignored():
    book = _local()
    assert not book.apply(_update(first=9, final=10))
    assert book.last_update_id == 10


def test_sequence_gap_requires_resnapshot():
    with pytest.raises(DepthSequenceGap, match="esperado 11"):
        _local().apply(_update(first=12, final=12))


def test_update_range_may_bridge_expected_sequence():
    book = _local()
    assert book.apply(_update(first=9, final=12))
    assert book.last_update_id == 12


def test_cross_venue_update_is_rejected():
    other = Instrument("BTCUSDT", "binance_futures")
    update = DepthUpdate(other, 11, 11, T0, ((99.0, 1.0),), ((101.0, 1.0),))
    with pytest.raises(ValueError, match="outro instrumento"):
        _local().apply(update)


def test_invalid_sequence_or_negative_qty_is_rejected():
    with pytest.raises(ValueError, match="sequence"):
        _update(first=12, final=11)
    with pytest.raises(ValueError, match="qty"):
        _update(bids=((99.0, -1.0),))
