"""Contrato econômico (trading/contracts.py) — 100% offline, sem I/O."""

from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.trading.contracts import (
    Direction,
    ExitRule,
    Fill,
    Instrument,
    Liquidity,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    SettlementRecord,
    TradeIntent,
    new_id,
)

T0 = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
BTC_PERP = Instrument("BTCUSDT", "binance_futures")


def _intent(**overrides):
    defaults = dict(
        intent_id=new_id("intent"),
        instrument=BTC_PERP,
        direction=Direction.LONG,
        generated_at=T0,
        entry_window_start=T0,
        entry_window_end=T0 + timedelta(minutes=30),
        holding_period_hours=24.0,
        target_position_fraction=0.1,
        exit_rule=ExitRule.TIME_STOP,
    )
    defaults.update(overrides)
    return TradeIntent(**defaults)


# --- Instrument ---------------------------------------------------------------


def test_instrument_key_combines_venue_and_symbol():
    assert BTC_PERP.key == "binance_futures:BTCUSDT"


@pytest.mark.parametrize("field_name", ["symbol", "venue"])
def test_instrument_rejects_empty_fields(field_name):
    kwargs = {"symbol": "BTCUSDT", "venue": "binance_futures"}
    kwargs[field_name] = "  "
    with pytest.raises(ValueError):
        Instrument(**kwargs)


# --- TradeIntent ----------------------------------------------------------------


def test_trade_intent_valid_constructs():
    intent = _intent()
    assert intent.direction is Direction.LONG
    assert intent.instrument is BTC_PERP


def test_trade_intent_rejects_naive_datetime():
    with pytest.raises(ValueError, match="timezone-aware"):
        _intent(generated_at=datetime(2026, 8, 14, 12, 0))


def test_trade_intent_rejects_entry_before_generated_at_anti_lookahead():
    with pytest.raises(ValueError, match="anti-lookahead"):
        _intent(generated_at=T0, entry_window_start=T0 - timedelta(seconds=1))


def test_trade_intent_rejects_entry_window_end_before_start():
    with pytest.raises(ValueError, match="entry_window_end"):
        _intent(entry_window_start=T0, entry_window_end=T0 - timedelta(seconds=1))


def test_trade_intent_rejects_nonpositive_holding_period():
    with pytest.raises(ValueError, match="holding_period_hours"):
        _intent(holding_period_hours=0)


@pytest.mark.parametrize("fraction", [-0.1, 1.1])
def test_trade_intent_rejects_fraction_out_of_bounds(fraction):
    with pytest.raises(ValueError, match="target_position_fraction"):
        _intent(target_position_fraction=fraction)


def test_trade_intent_price_stop_requires_stop_loss_pct():
    with pytest.raises(ValueError, match="stop_loss_pct"):
        _intent(exit_rule=ExitRule.PRICE_STOP)


def test_trade_intent_take_profit_requires_take_profit_pct():
    with pytest.raises(ValueError, match="take_profit_pct"):
        _intent(exit_rule=ExitRule.TAKE_PROFIT)


def test_trade_intent_accepts_price_stop_with_stop_loss_pct():
    intent = _intent(exit_rule=ExitRule.PRICE_STOP, stop_loss_pct=0.02)
    assert intent.stop_loss_pct == 0.02


def test_trade_intent_rejects_nonpositive_slippage_limit():
    with pytest.raises(ValueError, match="slippage_limit_bps"):
        _intent(slippage_limit_bps=0)


# --- Order / Fill ---------------------------------------------------------------


def test_order_avg_fill_price_and_remaining_qty():
    order = Order(
        order_id=new_id("order"),
        intent_id=new_id("intent"),
        instrument=BTC_PERP,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=1.0,
        status=OrderStatus.PARTIALLY_FILLED,
        created_at=T0,
        fills=(
            Fill(new_id("fill"), "o1", 0.4, 60_000.0, 2.4, Liquidity.TAKER, T0),
            Fill(new_id("fill"), "o1", 0.3, 60_100.0, 1.8, Liquidity.TAKER, T0),
        ),
    )
    assert order.filled_qty == pytest.approx(0.7)
    assert order.remaining_qty == pytest.approx(0.3)
    expected_avg = (0.4 * 60_000.0 + 0.3 * 60_100.0) / 0.7
    assert order.avg_fill_price == pytest.approx(expected_avg)


def test_order_avg_fill_price_none_without_fills():
    order = Order(
        new_id("o"),
        new_id("i"),
        BTC_PERP,
        OrderSide.BUY,
        OrderType.MARKET,
        1.0,
        OrderStatus.NEW,
        T0,
    )
    assert order.avg_fill_price is None


def test_order_rejects_fills_exceeding_qty():
    with pytest.raises(ValueError, match="excede qty"):
        Order(
            new_id("o"),
            new_id("i"),
            BTC_PERP,
            OrderSide.BUY,
            OrderType.MARKET,
            1.0,
            OrderStatus.FILLED,
            T0,
            fills=(Fill(new_id("f"), "o1", 1.5, 60_000.0, 3.0, Liquidity.TAKER, T0),),
        )


def test_limit_order_requires_limit_price():
    with pytest.raises(ValueError, match="limit_price"):
        Order(
            new_id("o"),
            new_id("i"),
            BTC_PERP,
            OrderSide.BUY,
            OrderType.LIMIT,
            1.0,
            OrderStatus.NEW,
            T0,
        )


def test_fill_rejects_nonpositive_qty_and_price():
    with pytest.raises(ValueError, match="qty"):
        Fill(new_id("f"), "o1", 0.0, 60_000.0, 1.0, Liquidity.TAKER, T0)
    with pytest.raises(ValueError, match="price"):
        Fill(new_id("f"), "o1", 1.0, 0.0, 1.0, Liquidity.TAKER, T0)


# --- Position --------------------------------------------------------------------


def test_position_unrealized_pnl_long_and_short():
    long_pos = Position(BTC_PERP, Direction.LONG, 1.0, 60_000.0, T0)
    short_pos = Position(BTC_PERP, Direction.SHORT, 1.0, 60_000.0, T0)
    assert long_pos.unrealized_pnl(61_000.0) == pytest.approx(1000.0)
    assert short_pos.unrealized_pnl(61_000.0) == pytest.approx(-1000.0)


def test_position_notional():
    pos = Position(BTC_PERP, Direction.LONG, 0.5, 60_000.0, T0)
    assert pos.notional(62_000.0) == pytest.approx(31_000.0)


def test_position_rejects_nonpositive_qty():
    with pytest.raises(ValueError, match="qty"):
        Position(BTC_PERP, Direction.LONG, 0.0, 60_000.0, T0)


# --- SettlementRecord --------------------------------------------------------------


def test_settlement_record_realized_pnl_and_holding_period():
    record = SettlementRecord(
        settlement_id=new_id("stl"),
        intent_id=new_id("intent"),
        instrument=BTC_PERP,
        direction=Direction.LONG,
        qty=1.0,
        entry_price=60_000.0,
        exit_price=61_000.0,
        opened_at=T0,
        closed_at=T0 + timedelta(hours=24),
        fees_paid=12.0,
        exit_reason=ExitRule.TIME_STOP,
    )
    assert record.holding_period_hours == pytest.approx(24.0)
    assert record.realized_pnl == pytest.approx(1000.0 - 12.0)


def test_settlement_record_short_realized_pnl_sign():
    record = SettlementRecord(
        new_id("stl"),
        new_id("intent"),
        BTC_PERP,
        Direction.SHORT,
        1.0,
        60_000.0,
        59_000.0,
        T0,
        T0 + timedelta(hours=1),
        5.0,
        ExitRule.SIGNAL_REVERSAL,
    )
    assert record.realized_pnl == pytest.approx(1000.0 - 5.0)


def test_settlement_record_rejects_closed_before_opened():
    with pytest.raises(ValueError, match="closed_at"):
        SettlementRecord(
            new_id("stl"),
            new_id("intent"),
            BTC_PERP,
            Direction.LONG,
            1.0,
            60_000.0,
            61_000.0,
            T0,
            T0 - timedelta(hours=1),
            0.0,
            ExitRule.TIME_STOP,
        )
