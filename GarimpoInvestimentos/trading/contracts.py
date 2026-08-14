"""Contrato econômico — instrumento, intenção de trade, ordem, fill, posição, settlement.

Parte do override de governança 2026-08-14 (docs/HYPOTHESES.md): o projeto tinha
"score"/`SignalRecord` (v3/signal_engine.py) como resultado final da previsão, mas
nunca uma representação única de POSIÇÃO EXECUTÁVEL — instrumento+venue, direção,
janela de entrada, período de manutenção, tamanho-alvo, regra de saída, stop, limite
de slippage, ordem, fill, posição, settlement. Este módulo é essa representação,
como TIPO — não como decisão de operar. Nada aqui autoriza capital real.

Estilo herdado de predictor_core.data.contracts: dataclasses imutáveis, validação em
__post_init__, UTC obrigatório, falha explícita nunca silenciosa. `TradeIntent` é
deliberadamente estrito quanto a look-ahead: a janela de entrada nunca pode começar
antes do instante em que a intenção foi gerada.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


def ensure_utc(value: datetime, label: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{label} precisa ser timezone-aware (UTC)")
    return value.astimezone(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class Direction(Enum):
    LONG = "long"
    SHORT = "short"


class ExitRule(Enum):
    TIME_STOP = "time_stop"  # sai ao fim do holding_period, independente de preço
    PRICE_STOP = "price_stop"  # sai ao tocar stop_loss_pct
    TAKE_PROFIT = "take_profit"  # sai ao tocar take_profit_pct
    SIGNAL_REVERSAL = "signal_reversal"  # sai quando o motor gera sinal oposto


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Liquidity(Enum):
    MAKER = "maker"
    TAKER = "taker"


@dataclass(frozen=True)
class Instrument:
    """Um instrumento negociável num venue específico — nunca um símbolo genérico
    sem venue: o mesmo BTCUSDT em spot e em perp são instrumentos diferentes."""

    symbol: str
    venue: str
    asset_class: str = "crypto_perp"

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("Instrument.symbol não pode ser vazio")
        if not self.venue.strip():
            raise ValueError("Instrument.venue não pode ser vazio")

    @property
    def key(self) -> str:
        return f"{self.venue}:{self.symbol}"


@dataclass(frozen=True)
class TradeIntent:
    """A unidade que faltava: não é um score, é 'o que eu pretendo fazer, com que
    regras de entrada/saída, se este sinal virasse execução'. Um TradeIntent NÃO é
    uma ordem — vira ordem só quando (e se) uma decisão explícita de operar
    acontece; até lá é objeto de simulação/auditoria, rastreável até o sinal que
    o originou via `source_signal_id`."""

    intent_id: str
    instrument: Instrument
    direction: Direction
    generated_at: datetime
    entry_window_start: datetime
    entry_window_end: datetime
    holding_period_hours: float
    target_position_fraction: float  # fração do capital em [0, 1]; sinal vem de `direction`
    exit_rule: ExitRule
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    slippage_limit_bps: float = 50.0
    source_signal_id: str = ""

    def __post_init__(self) -> None:
        generated = ensure_utc(self.generated_at, "TradeIntent.generated_at")
        entry_start = ensure_utc(self.entry_window_start, "TradeIntent.entry_window_start")
        entry_end = ensure_utc(self.entry_window_end, "TradeIntent.entry_window_end")
        if entry_start < generated:
            raise ValueError(
                "TradeIntent: entry_window_start anterior a generated_at — violaria "
                "anti-lookahead (a janela de entrada não pode começar antes de a "
                "intenção ter sido gerada)"
            )
        if entry_end < entry_start:
            raise ValueError("TradeIntent: entry_window_end anterior a entry_window_start")
        if self.holding_period_hours <= 0:
            raise ValueError("TradeIntent.holding_period_hours deve ser > 0")
        if not (0 <= self.target_position_fraction <= 1):
            raise ValueError("TradeIntent.target_position_fraction deve estar em [0, 1]")
        if self.slippage_limit_bps <= 0:
            raise ValueError("TradeIntent.slippage_limit_bps deve ser > 0")
        if self.exit_rule is ExitRule.PRICE_STOP and self.stop_loss_pct is None:
            raise ValueError("TradeIntent: exit_rule=PRICE_STOP exige stop_loss_pct")
        if self.exit_rule is ExitRule.TAKE_PROFIT and self.take_profit_pct is None:
            raise ValueError("TradeIntent: exit_rule=TAKE_PROFIT exige take_profit_pct")
        if self.stop_loss_pct is not None and not (0 < self.stop_loss_pct < 1):
            raise ValueError("TradeIntent.stop_loss_pct deve estar em (0, 1)")
        if self.take_profit_pct is not None and self.take_profit_pct <= 0:
            raise ValueError("TradeIntent.take_profit_pct deve ser > 0")
        object.__setattr__(self, "generated_at", generated)
        object.__setattr__(self, "entry_window_start", entry_start)
        object.__setattr__(self, "entry_window_end", entry_end)


@dataclass(frozen=True)
class Fill:
    fill_id: str
    order_id: str
    qty: float
    price: float
    fee: float
    liquidity: Liquidity
    filled_at: datetime

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("Fill.qty deve ser > 0")
        if self.price <= 0:
            raise ValueError("Fill.price deve ser > 0")
        if self.fee < 0:
            raise ValueError("Fill.fee não pode ser negativo")
        object.__setattr__(self, "filled_at", ensure_utc(self.filled_at, "Fill.filled_at"))


@dataclass(frozen=True)
class Order:
    """Estado é imutável neste objeto — transições (accept/fill/cancel) vivem em
    trading/execution.py e retornam uma NOVA instância, nunca mutam esta."""

    order_id: str
    intent_id: str
    instrument: Instrument
    side: OrderSide
    order_type: OrderType
    qty: float
    status: OrderStatus
    created_at: datetime
    limit_price: float | None = None
    fills: tuple[Fill, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("Order.qty deve ser > 0")
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Order: order_type=LIMIT exige limit_price")
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("Order.limit_price deve ser > 0")
        filled_qty = sum(f.qty for f in self.fills)
        if filled_qty > self.qty + 1e-9:
            raise ValueError(
                f"Order {self.order_id}: soma dos fills ({filled_qty}) excede qty ({self.qty})"
            )
        object.__setattr__(self, "created_at", ensure_utc(self.created_at, "Order.created_at"))

    @property
    def filled_qty(self) -> float:
        return sum(f.qty for f in self.fills)

    @property
    def remaining_qty(self) -> float:
        return round(self.qty - self.filled_qty, 12)

    @property
    def avg_fill_price(self) -> float | None:
        if not self.fills:
            return None
        notional = sum(f.qty * f.price for f in self.fills)
        return notional / self.filled_qty


@dataclass(frozen=True)
class Position:
    instrument: Instrument
    direction: Direction
    qty: float
    avg_entry_price: float
    opened_at: datetime
    intent_id: str = ""

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("Position.qty deve ser > 0")
        if self.avg_entry_price <= 0:
            raise ValueError("Position.avg_entry_price deve ser > 0")
        object.__setattr__(self, "opened_at", ensure_utc(self.opened_at, "Position.opened_at"))

    def notional(self, mark_price: float) -> float:
        return self.qty * mark_price

    def unrealized_pnl(self, mark_price: float) -> float:
        sign = 1.0 if self.direction is Direction.LONG else -1.0
        return sign * self.qty * (mark_price - self.avg_entry_price)


@dataclass(frozen=True)
class SettlementRecord:
    """O fim da vida de uma posição — realizado, não mark-to-market."""

    settlement_id: str
    intent_id: str
    instrument: Instrument
    direction: Direction
    qty: float
    entry_price: float
    exit_price: float
    opened_at: datetime
    closed_at: datetime
    fees_paid: float
    exit_reason: ExitRule

    def __post_init__(self) -> None:
        opened = ensure_utc(self.opened_at, "SettlementRecord.opened_at")
        closed = ensure_utc(self.closed_at, "SettlementRecord.closed_at")
        if closed < opened:
            raise ValueError("SettlementRecord: closed_at anterior a opened_at")
        if self.qty <= 0:
            raise ValueError("SettlementRecord.qty deve ser > 0")
        if self.entry_price <= 0 or self.exit_price <= 0:
            raise ValueError("SettlementRecord: entry_price/exit_price devem ser > 0")
        if self.fees_paid < 0:
            raise ValueError("SettlementRecord.fees_paid não pode ser negativo")
        object.__setattr__(self, "opened_at", opened)
        object.__setattr__(self, "closed_at", closed)

    @property
    def holding_period_hours(self) -> float:
        return (self.closed_at - self.opened_at).total_seconds() / 3600.0

    @property
    def realized_pnl(self) -> float:
        sign = 1.0 if self.direction is Direction.LONG else -1.0
        gross = sign * self.qty * (self.exit_price - self.entry_price)
        return gross - self.fees_paid
