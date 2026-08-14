"""Execução (trading/execution.py) — máquina de estados, idempotência, reconciliação."""

from datetime import UTC, datetime

import pytest

from GarimpoInvestimentos.trading.contracts import (
    Fill,
    Instrument,
    Liquidity,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    new_id,
)
from GarimpoInvestimentos.trading.execution import (
    OrderBookLedger,
    OrderLifecycleError,
    SimulatedExchangeAdapter,
    accept,
    apply_fill,
    cancel,
    reconcile,
    reject,
)

T0 = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
BTC_PERP = Instrument("BTCUSDT", "binance_futures")


def _new_order(qty=1.0, status=OrderStatus.NEW):
    return Order(
        new_id("o"), new_id("i"), BTC_PERP, OrderSide.BUY, OrderType.MARKET, qty, status, T0
    )


def _fill(order_id, qty, price=60_000.0):
    return Fill(new_id("f"), order_id, qty, price, qty * price * 0.0004, Liquidity.TAKER, T0)


# --- transições de estado -----------------------------------------------------


def test_accept_transitions_new_to_accepted():
    order = _new_order()
    accepted = accept(order)
    assert accepted.status is OrderStatus.ACCEPTED
    assert order.status is OrderStatus.NEW  # original não mutado


def test_accept_rejects_wrong_initial_state():
    order = accept(_new_order())
    with pytest.raises(OrderLifecycleError, match="NEW"):
        accept(order)


def test_apply_fill_partial_then_full():
    order = accept(_new_order(qty=1.0))
    order = apply_fill(order, _fill(order.order_id, 0.4))
    assert order.status is OrderStatus.PARTIALLY_FILLED
    order = apply_fill(order, _fill(order.order_id, 0.6))
    assert order.status is OrderStatus.FILLED
    assert order.remaining_qty == pytest.approx(0.0)


def test_apply_fill_before_accept_raises():
    order = _new_order()
    with pytest.raises(OrderLifecycleError, match="ACCEPTED/PARTIALLY_FILLED"):
        apply_fill(order, _fill(order.order_id, 0.5))


def test_apply_fill_wrong_order_id_raises():
    order = accept(_new_order())
    other_fill = _fill("outra-ordem", 0.5)
    with pytest.raises(OrderLifecycleError, match="pertence à ordem"):
        apply_fill(order, other_fill)


def test_apply_fill_overfill_raises():
    order = accept(_new_order(qty=1.0))
    order = apply_fill(order, _fill(order.order_id, 0.9))
    with pytest.raises(OrderLifecycleError, match="acima de qty"):
        apply_fill(order, _fill(order.order_id, 0.5))


def test_cancel_from_accepted():
    order = accept(_new_order())
    cancelled = cancel(order)
    assert cancelled.status is OrderStatus.CANCELLED


def test_cancel_terminal_state_raises():
    order = accept(_new_order(qty=1.0))
    order = apply_fill(order, _fill(order.order_id, 1.0))
    assert order.status is OrderStatus.FILLED
    with pytest.raises(OrderLifecycleError, match="terminal"):
        cancel(order)


def test_reject_from_new():
    order = reject(_new_order())
    assert order.status is OrderStatus.REJECTED


def test_reject_non_new_raises():
    order = accept(_new_order())
    with pytest.raises(OrderLifecycleError, match="NEW"):
        reject(order)


# --- OrderBookLedger / idempotência --------------------------------------------


def test_ledger_submit_is_idempotent_by_client_order_id():
    ledger = OrderBookLedger()
    order = _new_order()
    first = ledger.submit(order, client_order_id="cli-1")
    duplicate_attempt = _new_order()  # order_id diferente, mesmo client_order_id
    second = ledger.submit(duplicate_attempt, client_order_id="cli-1")
    assert first.order_id == second.order_id  # devolveu a ORIGINAL, não duplicou
    assert first is second


def test_ledger_different_client_order_ids_create_different_orders():
    ledger = OrderBookLedger()
    first = ledger.submit(_new_order(), client_order_id="cli-1")
    second = ledger.submit(_new_order(), client_order_id="cli-2")
    assert first.order_id != second.order_id


def test_ledger_update_and_open_orders():
    ledger = OrderBookLedger()
    order = ledger.submit(_new_order(), client_order_id="cli-1")
    order = accept(order)
    ledger.update(order)
    assert ledger.get(order.order_id).status is OrderStatus.ACCEPTED
    assert len(ledger.open_orders()) == 1

    order = apply_fill(order, _fill(order.order_id, 1.0))
    ledger.update(order)
    assert ledger.open_orders() == ()  # FILLED é terminal, some da lista de abertas


def test_ledger_update_unknown_order_raises():
    ledger = OrderBookLedger()
    with pytest.raises(OrderLifecycleError, match="não está no ledger"):
        ledger.update(_new_order())


# --- reconciliação --------------------------------------------------------------


def test_reconcile_matches_returns_none():
    order = accept(_new_order(qty=1.0))
    fill = _fill(order.order_id, 1.0)
    order = apply_fill(order, fill)
    adapter = SimulatedExchangeAdapter()
    adapter.record_fill(fill)
    assert reconcile(order, adapter) is None


def test_reconcile_divergence_returns_break_not_silent_fix():
    order = accept(_new_order(qty=1.0))
    order = apply_fill(order, _fill(order.order_id, 1.0))
    adapter = SimulatedExchangeAdapter()  # venue não reportou nada — divergência real
    result = reconcile(order, adapter)
    assert result is not None
    assert result.order_id == order.order_id
    assert result.local_filled_qty == pytest.approx(1.0)
    assert result.exchange_filled_qty == pytest.approx(0.0)
    assert result.delta == pytest.approx(1.0)
