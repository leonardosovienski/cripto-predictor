from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.trading.contracts import Instrument
from GarimpoInvestimentos.trading.costs import simulate_spot_long_round_trip
from GarimpoInvestimentos.trading.microstructure import OrderBookLevel, OrderBookSnapshot

T0 = datetime(2026, 8, 17, 12, tzinfo=UTC)
INSTRUMENT = Instrument("BTCUSDT", "binance_spot", "crypto_spot")


def _book(ts, bid, ask, qty=1.0, instrument=INSTRUMENT):
    return OrderBookSnapshot(
        instrument=instrument,
        timestamp=ts,
        bids=(OrderBookLevel(bid, qty),),
        asks=(OrderBookLevel(ask, qty),),
    )


def test_round_trip_is_net_of_walk_book_fees_and_latency():
    result = simulate_spot_long_round_trip(
        qty=0.5,
        entry_book=_book(T0, 99, 101),
        exit_book=_book(T0 + timedelta(hours=4), 109, 111),
        taker_fee_bps=10,
        latency_penalty_bps_per_leg=5,
    )
    assert result.executable
    assert result.gross_pnl == pytest.approx(4.0)
    assert result.fees == pytest.approx((50.5 + 54.5) * 0.001)
    assert result.latency_cost == pytest.approx((50.5 + 54.5) * 0.0005)
    assert result.net_pnl == pytest.approx(4.0 - result.fees - result.latency_cost)


def test_insufficient_depth_is_not_executable():
    result = simulate_spot_long_round_trip(
        qty=2.0,
        entry_book=_book(T0, 99, 101, qty=1.0),
        exit_book=_book(T0 + timedelta(hours=4), 109, 111, qty=1.0),
        taker_fee_bps=10,
    )
    assert not result.executable
    assert result.reason == "insufficient_observed_depth"
    assert result.net_pnl is None


def test_round_trip_rejects_cross_venue_or_noncausal_books():
    other = Instrument("BTCUSDT", "binance_futures")
    with pytest.raises(ValueError, match="mesmo instrumento"):
        simulate_spot_long_round_trip(
            qty=1,
            entry_book=_book(T0, 99, 101),
            exit_book=_book(T0 + timedelta(hours=4), 109, 111, instrument=other),
            taker_fee_bps=10,
        )
    with pytest.raises(ValueError, match="posterior"):
        simulate_spot_long_round_trip(
            qty=1,
            entry_book=_book(T0, 99, 101),
            exit_book=_book(T0, 109, 111),
            taker_fee_bps=10,
        )


@pytest.mark.parametrize("fee,latency", [(-1, 0), (0, -1)])
def test_round_trip_rejects_negative_costs(fee, latency):
    with pytest.raises(ValueError, match="negativas"):
        simulate_spot_long_round_trip(
            qty=1,
            entry_book=_book(T0, 99, 101),
            exit_book=_book(T0 + timedelta(hours=4), 109, 111),
            taker_fee_bps=fee,
            latency_penalty_bps_per_leg=latency,
        )
