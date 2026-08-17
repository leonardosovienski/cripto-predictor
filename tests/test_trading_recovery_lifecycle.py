from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.trading.contracts import (
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from GarimpoInvestimentos.trading.execution import (
    OrderLifecycleError,
    accept,
    begin_reconciliation,
    expire,
    mark_reconciled,
    mark_unknown,
    submit,
)

T0 = datetime(2026, 8, 17, 12, tzinfo=UTC)


def _order() -> Order:
    return Order(
        order_id="o-1",
        intent_id="i-1",
        instrument=Instrument("BTCUSDT", "binance_spot", "crypto_spot"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=0.01,
        status=OrderStatus.NEW,
        created_at=T0,
    )


def test_submit_accept_records_latency_timestamps():
    submitted = submit(_order(), submitted_at=T0 + timedelta(milliseconds=2))
    accepted = accept(submitted, accepted_at=T0 + timedelta(milliseconds=7))
    assert submitted.status is OrderStatus.SUBMITTING
    assert accepted.status is OrderStatus.ACCEPTED
    assert accepted.submitted_at == T0 + timedelta(milliseconds=2)
    assert accepted.accepted_at == T0 + timedelta(milliseconds=7)


def test_unknown_must_reconcile_explicitly():
    unknown = mark_unknown(_order(), reason="venue_timeout")
    reconciling = begin_reconciliation(unknown)
    reconciled = mark_reconciled(
        reconciling, reconciled_at=T0 + timedelta(seconds=2), reason="not_found_at_venue"
    )
    assert reconciled.status is OrderStatus.RECONCILED
    assert reconciled.last_reconciled_at == T0 + timedelta(seconds=2)


def test_unknown_rejects_empty_reason():
    with pytest.raises(ValueError, match="reason"):
        mark_unknown(_order(), reason=" ")


def test_reconciliation_cannot_start_from_known_state():
    with pytest.raises(OrderLifecycleError, match="UNKNOWN"):
        begin_reconciliation(_order())


def test_expiry_is_terminal():
    expired = expire(_order(), expired_at=T0 + timedelta(minutes=5))
    assert expired.status is OrderStatus.EXPIRED
    with pytest.raises(OrderLifecycleError, match="terminal"):
        mark_unknown(expired, reason="timeout")


def test_order_timestamps_cannot_precede_creation():
    with pytest.raises(ValueError, match="anterior a created_at"):
        submit(_order(), submitted_at=T0 - timedelta(microseconds=1))
