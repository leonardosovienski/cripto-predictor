"""Microestrutura (trading/microstructure.py) — book, walk-the-book, impacto, coletor mockado."""

import asyncio
from datetime import UTC, datetime

import pytest

from GarimpoInvestimentos.trading.contracts import Instrument, OrderSide
from GarimpoInvestimentos.trading.microstructure import (
    BinanceOrderBookCollector,
    OrderBookLevel,
    OrderBookSnapshot,
    simulate_market_fill,
    sqrt_impact_bps,
)

T0 = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
BTC_SPOT = Instrument("BTCUSDT", "binance_spot")


def _book(bids=None, asks=None):
    bids = bids or [(59_990.0, 1.0), (59_980.0, 2.0), (59_970.0, 5.0)]
    asks = asks or [(60_010.0, 1.0), (60_020.0, 2.0), (60_030.0, 5.0)]
    return OrderBookSnapshot(
        instrument=BTC_SPOT,
        timestamp=T0,
        bids=tuple(OrderBookLevel(p, q) for p, q in bids),
        asks=tuple(OrderBookLevel(p, q) for p, q in asks),
    )


# --- OrderBookSnapshot ----------------------------------------------------------


def test_snapshot_mid_and_spread():
    book = _book()
    assert book.best_bid == 59_990.0
    assert book.best_ask == 60_010.0
    assert book.mid_price == pytest.approx(60_000.0)
    assert book.spread_bps == pytest.approx((60_010 - 59_990) / 60_000 * 10_000)


def test_snapshot_rejects_crossed_book():
    with pytest.raises(ValueError, match="cruzado"):
        _book(bids=[(60_050.0, 1.0)], asks=[(60_010.0, 1.0)])


def test_snapshot_rejects_bids_out_of_order():
    with pytest.raises(ValueError, match="decrescente"):
        _book(bids=[(59_980.0, 1.0), (59_990.0, 1.0)])


def test_snapshot_rejects_asks_out_of_order():
    with pytest.raises(ValueError, match="crescente"):
        _book(asks=[(60_020.0, 1.0), (60_010.0, 1.0)])


def test_snapshot_rejects_empty_side():
    with pytest.raises(ValueError, match="ao menos 1 nível"):
        OrderBookSnapshot(BTC_SPOT, T0, bids=(), asks=(OrderBookLevel(60_010.0, 1.0),))


def test_order_book_level_rejects_nonpositive():
    with pytest.raises(ValueError):
        OrderBookLevel(0.0, 1.0)
    with pytest.raises(ValueError):
        OrderBookLevel(60_000.0, 0.0)


# --- simulate_market_fill (walk the book) ----------------------------------------


def test_fill_within_first_level_has_no_slippage_beyond_spread():
    book = _book()
    result = simulate_market_fill(book, OrderSide.BUY, 0.5)
    assert result.fully_filled
    assert result.vwap_price == pytest.approx(60_010.0)  # só o primeiro nível
    assert result.levels_consumed == 1


def test_fill_crossing_multiple_levels_computes_vwap():
    book = _book()
    result = simulate_market_fill(book, OrderSide.BUY, 2.5)  # 1.0@60010 + 1.5@60020
    assert result.fully_filled
    expected_notional = 1.0 * 60_010.0 + 1.5 * 60_020.0
    assert result.vwap_price == pytest.approx(expected_notional / 2.5)
    assert result.levels_consumed == 2


def test_fill_exceeding_book_depth_is_partial_not_interpolated():
    book = _book()  # profundidade total do ask = 1+2+5 = 8
    result = simulate_market_fill(book, OrderSide.BUY, 100.0)
    assert not result.fully_filled
    assert result.filled_qty == pytest.approx(8.0)
    assert result.levels_consumed == 3


def test_sell_consumes_bids_not_asks():
    book = _book()
    result = simulate_market_fill(book, OrderSide.SELL, 0.5)
    assert result.vwap_price == pytest.approx(59_990.0)


def test_slippage_is_positive_cost_for_both_sides():
    """Convenção: slippage_bps é custo relativo ao mid, sempre positivo pra
    quem cruza o spread — comprar acima do mid e vender abaixo do mid são os
    dois um custo, não sinais opostos."""
    book = _book()
    buy = simulate_market_fill(book, OrderSide.BUY, 2.5)
    sell = simulate_market_fill(book, OrderSide.SELL, 2.5)
    assert buy.slippage_bps > 0
    assert sell.slippage_bps > 0


def test_simulate_market_fill_rejects_nonpositive_qty():
    with pytest.raises(ValueError, match="qty"):
        simulate_market_fill(_book(), OrderSide.BUY, 0.0)


# --- sqrt_impact_bps --------------------------------------------------------------


def test_sqrt_impact_bps_zero_participation_is_zero():
    assert sqrt_impact_bps(0.0, 100.0) == 0.0


def test_sqrt_impact_bps_scales_with_sqrt_participation():
    low = sqrt_impact_bps(0.01, 100.0)
    high = sqrt_impact_bps(0.04, 100.0)
    assert high == pytest.approx(2 * low)  # sqrt(0.04)/sqrt(0.01) = 2


@pytest.mark.parametrize("kwargs", [{"participation_rate": -0.1}, {"participation_rate": 1.1}])
def test_sqrt_impact_bps_rejects_participation_out_of_bounds(kwargs):
    with pytest.raises(ValueError, match="participation_rate"):
        sqrt_impact_bps(volatility_bps=100.0, **kwargs)


def test_sqrt_impact_bps_rejects_negative_volatility():
    with pytest.raises(ValueError, match="volatility_bps"):
        sqrt_impact_bps(0.1, -1.0)


# --- BinanceOrderBookCollector (HTTP mockado) -------------------------------------


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _Client:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def get(self, url, params=None):
        return _Resp(self._payload)


def test_binance_collector_parses_depth_into_snapshot(monkeypatch):
    from GarimpoInvestimentos.trading import microstructure as ms

    payload = {
        "lastUpdateId": 123,
        "bids": [["59990.00", "1.5"], ["59980.00", "2.0"]],
        "asks": [["60010.00", "1.2"], ["60020.00", "3.0"]],
    }
    monkeypatch.setattr(ms, "get_http_client", lambda *a, **k: _Client(payload))
    collector = BinanceOrderBookCollector()
    snapshot = asyncio.run(collector.fetch("BTCUSDT"))

    assert snapshot.instrument.key == "binance_spot:BTCUSDT"
    assert snapshot.best_bid == 59_990.0
    assert snapshot.best_ask == 60_010.0
    assert len(snapshot.bids) == 2 and len(snapshot.asks) == 2


def test_binance_collector_raises_on_unexpected_format(monkeypatch):
    from GarimpoInvestimentos.trading import microstructure as ms

    monkeypatch.setattr(ms, "get_http_client", lambda *a, **k: _Client({"error": "oops"}))
    collector = BinanceOrderBookCollector()
    with pytest.raises(RuntimeError, match="formato inesperado"):
        asyncio.run(collector.fetch("BTCUSDT"))
