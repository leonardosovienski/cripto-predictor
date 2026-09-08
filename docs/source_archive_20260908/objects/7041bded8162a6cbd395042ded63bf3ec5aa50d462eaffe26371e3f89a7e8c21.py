"""Custos canônicos para o baseline Binance Spot sem short ou leverage."""

from __future__ import annotations

from dataclasses import dataclass

from GarimpoInvestimentos.trading.contracts import OrderSide
from GarimpoInvestimentos.trading.microstructure import (
    OrderBookSnapshot,
    SimulatedFill,
    simulate_market_fill,
)


@dataclass(frozen=True)
class SpotRoundTripResult:
    executable: bool
    requested_qty: float
    entry: SimulatedFill
    exit: SimulatedFill
    gross_pnl: float | None
    fees: float | None
    latency_cost: float | None
    net_pnl: float | None
    reason: str | None = None


def simulate_spot_long_round_trip(
    *,
    qty: float,
    entry_book: OrderBookSnapshot,
    exit_book: OrderBookSnapshot,
    taker_fee_bps: float,
    latency_penalty_bps_per_leg: float = 0.0,
) -> SpotRoundTripResult:
    """Compra no book de entrada e vende no book de saída.

    Spread e profundidade já entram nos VWAPs do walk-the-book. Fee e penalidade
    de latência são separadas para não contar spread duas vezes. Se qualquer
    perna não preencher integralmente na profundidade observada, o trade é
    classificado como não executável; liquidez ausente nunca é inventada.
    """
    if qty <= 0:
        raise ValueError("qty deve ser > 0")
    if taker_fee_bps < 0 or latency_penalty_bps_per_leg < 0:
        raise ValueError("fees e penalidade de latência não podem ser negativas")
    if entry_book.instrument != exit_book.instrument:
        raise ValueError("entry e exit books devem ser do mesmo instrumento/venue")
    if exit_book.timestamp <= entry_book.timestamp:
        raise ValueError("exit_book deve ser posterior ao entry_book")

    entry = simulate_market_fill(entry_book, OrderSide.BUY, qty)
    exit_fill = simulate_market_fill(exit_book, OrderSide.SELL, qty)
    if not entry.fully_filled or not exit_fill.fully_filled:
        return SpotRoundTripResult(
            executable=False,
            requested_qty=qty,
            entry=entry,
            exit=exit_fill,
            gross_pnl=None,
            fees=None,
            latency_cost=None,
            net_pnl=None,
            reason="insufficient_observed_depth",
        )

    assert entry.vwap_price is not None and exit_fill.vwap_price is not None
    entry_notional = qty * entry.vwap_price
    exit_notional = qty * exit_fill.vwap_price
    gross_pnl = exit_notional - entry_notional
    fees = (entry_notional + exit_notional) * taker_fee_bps / 10_000
    latency_cost = (entry_notional + exit_notional) * latency_penalty_bps_per_leg / 10_000
    return SpotRoundTripResult(
        executable=True,
        requested_qty=qty,
        entry=entry,
        exit=exit_fill,
        gross_pnl=gross_pnl,
        fees=fees,
        latency_cost=latency_cost,
        net_pnl=gross_pnl - fees - latency_cost,
    )
