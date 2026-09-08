"""Execução — máquina de estados do ciclo de vida da ordem.

ordem -> aceita -> fill parcial -> fill completo -> cancelamento -> reconciliação

Parte do override de governança 2026-08-14 (docs/HYPOTHESES.md). Motor puro (sem
I/O, sem rede) que aplica transições de estado sobre os tipos de trading/contracts.py
— cada transição retorna uma NOVA `Order` (imutável), nunca muta a existente.

Conectar isto a um venue real (Binance etc.) é trabalho FUTURO, deliberadamente fora
de escopo aqui: `ExchangeAdapter` é um Protocol: a única implementação fornecida é
`SimulatedExchangeAdapter`, em memória, para paper trading e testes — nunca fala com
um venue de verdade.

Idempotência: `OrderBookLedger.submit` recebe um `client_order_id`; submeter o MESMO
duas vezes devolve a ordem já criada em vez de duplicar — mesmo princípio de chave de
idempotência do predictor_ops (nunca reprocessa em silêncio).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from GarimpoInvestimentos.trading.contracts import Fill, Order, OrderStatus

_TERMINAL_STATES = frozenset(
    {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.RECONCILED,
        OrderStatus.EXPIRED,
    }
)


class OrderLifecycleError(RuntimeError):
    """Transição de estado inválida — nunca deve mutar silenciosamente."""


def submit(order: Order, *, submitted_at: datetime) -> Order:
    if order.status is not OrderStatus.NEW:
        raise OrderLifecycleError(
            f"Order {order.order_id}: submit() exige status=NEW, tinha {order.status}"
        )
    return replace(order, status=OrderStatus.SUBMITTING, submitted_at=submitted_at)


def accept(order: Order, *, accepted_at: datetime | None = None) -> Order:
    if order.status not in (OrderStatus.NEW, OrderStatus.SUBMITTING):
        raise OrderLifecycleError(
            f"Order {order.order_id}: accept() exige NEW/SUBMITTING, tinha {order.status}"
        )
    return replace(order, status=OrderStatus.ACCEPTED, accepted_at=accepted_at)


def apply_fill(order: Order, fill: Fill) -> Order:
    if order.status not in (OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED):
        raise OrderLifecycleError(
            f"Order {order.order_id}: apply_fill() exige ACCEPTED/PARTIALLY_FILLED, "
            f"tinha {order.status}"
        )
    if fill.order_id != order.order_id:
        raise OrderLifecycleError(
            f"Fill {fill.fill_id} pertence à ordem {fill.order_id}, não a {order.order_id}"
        )
    new_fills = (*order.fills, fill)
    filled_qty = sum(f.qty for f in new_fills)
    if filled_qty > order.qty + 1e-9:
        raise OrderLifecycleError(
            f"Order {order.order_id}: fill levaria a quantidade preenchida ({filled_qty}) "
            f"acima de qty ({order.qty})"
        )
    status = OrderStatus.FILLED if filled_qty >= order.qty - 1e-9 else OrderStatus.PARTIALLY_FILLED
    return replace(order, status=status, fills=new_fills)


def cancel(
    order: Order, *, cancelled_at: datetime | None = None, reason: str | None = None
) -> Order:
    if order.status in _TERMINAL_STATES:
        raise OrderLifecycleError(
            f"Order {order.order_id}: cancel() em estado terminal ({order.status})"
        )
    return replace(
        order, status=OrderStatus.CANCELLED, terminal_at=cancelled_at, status_reason=reason
    )


def reject(
    order: Order, *, rejected_at: datetime | None = None, reason: str | None = None
) -> Order:
    if order.status not in (OrderStatus.NEW, OrderStatus.SUBMITTING):
        raise OrderLifecycleError(
            f"Order {order.order_id}: reject() exige NEW/SUBMITTING, tinha {order.status}"
        )
    return replace(
        order, status=OrderStatus.REJECTED, terminal_at=rejected_at, status_reason=reason
    )


def mark_unknown(order: Order, *, reason: str) -> Order:
    """Marca resultado indeterminado sem assumir sucesso ou falha do venue."""
    if order.status in _TERMINAL_STATES:
        raise OrderLifecycleError(
            f"Order {order.order_id}: mark_unknown() em estado terminal ({order.status})"
        )
    if not reason.strip():
        raise ValueError("mark_unknown: reason não pode ser vazio")
    return replace(order, status=OrderStatus.UNKNOWN, status_reason=reason)


def begin_reconciliation(order: Order) -> Order:
    if order.status is not OrderStatus.UNKNOWN:
        raise OrderLifecycleError(
            f"Order {order.order_id}: begin_reconciliation() exige UNKNOWN, tinha {order.status}"
        )
    return replace(order, status=OrderStatus.RECONCILING)


def mark_reconciled(order: Order, *, reconciled_at: datetime, reason: str | None = None) -> Order:
    if order.status is not OrderStatus.RECONCILING:
        raise OrderLifecycleError(
            f"Order {order.order_id}: mark_reconciled() exige RECONCILING, tinha {order.status}"
        )
    return replace(
        order,
        status=OrderStatus.RECONCILED,
        terminal_at=reconciled_at,
        last_reconciled_at=reconciled_at,
        status_reason=reason,
    )


def expire(order: Order, *, expired_at: datetime, reason: str = "entry_window_expired") -> Order:
    if order.status in _TERMINAL_STATES or order.status in (
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
    ):
        raise OrderLifecycleError(f"Order {order.order_id}: expire() inválido em {order.status}")
    return replace(order, status=OrderStatus.EXPIRED, terminal_at=expired_at, status_reason=reason)


class ExchangeAdapter(Protocol):
    """Fronteira com um venue real. Implementações reais (Binance etc.) são
    trabalho FUTURO — aqui só existe `SimulatedExchangeAdapter`."""

    def reported_fills(self, order_id: str) -> tuple[Fill, ...]: ...


class SimulatedExchangeAdapter:
    """Adapter em memória — paper trading e testes. NUNCA fala com um venue real."""

    def __init__(self) -> None:
        self._fills_by_order: dict[str, tuple[Fill, ...]] = {}

    def record_fill(self, fill: Fill) -> None:
        existing = self._fills_by_order.get(fill.order_id, ())
        self._fills_by_order[fill.order_id] = (*existing, fill)

    def reported_fills(self, order_id: str) -> tuple[Fill, ...]:
        return self._fills_by_order.get(order_id, ())


@dataclass(frozen=True)
class ReconciliationBreak:
    order_id: str
    local_filled_qty: float
    exchange_filled_qty: float

    @property
    def delta(self) -> float:
        return self.local_filled_qty - self.exchange_filled_qty


def reconcile(
    order: Order, adapter: ExchangeAdapter, *, tolerance: float = 1e-9
) -> ReconciliationBreak | None:
    """Compara o estado local (`order.fills`) contra o que o venue reporta. `None`
    se bater dentro da tolerância; `ReconciliationBreak` se divergir — NUNCA
    silencia uma divergência ajustando o estado local sozinho."""
    exchange_fills = adapter.reported_fills(order.order_id)
    exchange_qty = sum(f.qty for f in exchange_fills)
    local_qty = order.filled_qty
    if abs(local_qty - exchange_qty) <= tolerance:
        return None
    return ReconciliationBreak(order.order_id, local_qty, exchange_qty)


class OrderBookLedger:
    """Ledger de ordens em memória, com idempotência por `client_order_id`."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._client_order_ids: dict[str, str] = {}

    def submit(self, order: Order, *, client_order_id: str) -> Order:
        existing_order_id = self._client_order_ids.get(client_order_id)
        if existing_order_id is not None:
            return self._orders[existing_order_id]
        self._orders[order.order_id] = order
        self._client_order_ids[client_order_id] = order.order_id
        return order

    def get(self, order_id: str) -> Order:
        return self._orders[order_id]

    def update(self, order: Order) -> None:
        if order.order_id not in self._orders:
            raise OrderLifecycleError(f"Order {order.order_id}: não está no ledger")
        self._orders[order.order_id] = order

    def open_orders(self) -> tuple[Order, ...]:
        return tuple(o for o in self._orders.values() if o.status not in _TERMINAL_STATES)
