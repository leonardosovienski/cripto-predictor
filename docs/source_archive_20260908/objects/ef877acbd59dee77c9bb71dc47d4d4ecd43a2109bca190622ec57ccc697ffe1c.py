"""Read-only portfolio risk report. It never authorizes capital or emits a verdict."""

from __future__ import annotations

from dataclasses import dataclass

from GarimpoInvestimentos.trading.contracts import Position
from GarimpoInvestimentos.trading.portfolio import (
    aggregate_leverage,
    concentration_hhi,
    correlation_matrix,
    exchange_exposure,
)


@dataclass(frozen=True)
class PortfolioReport:
    n_positions: int
    gross_notional: float
    gross_leverage: float
    concentration_hhi: float
    exposure_by_venue: dict[str, float]
    max_pairwise_correlation: tuple[str, str, float] | None
    avisos: tuple[str, ...]
    nota: str


def build_portfolio_report(
    positions: list[Position],
    mark_prices: dict[str, float],
    *,
    equity: float,
    returns_by_asset: dict[str, list[float]] | None = None,
) -> PortfolioReport:
    if equity <= 0:
        raise ValueError("equity deve ser > 0")
    exposure = exchange_exposure(positions, mark_prices)
    notionals: dict[str, float] = {}
    for position in positions:
        mark = mark_prices.get(position.instrument.key)
        if mark is None:
            raise ValueError(f"falta mark price para {position.instrument.key}")
        notionals[position.instrument.key] = position.notional(mark)
    gross = sum(abs(v) for v in notionals.values())
    leverage = aggregate_leverage(positions, mark_prices, equity)
    hhi = concentration_hhi(notionals) if notionals else 0.0
    max_pair = None
    avisos: list[str] = []
    if returns_by_asset and len(returns_by_asset) >= 2:
        matrix = correlation_matrix(returns_by_asset)
        pairs = [(a, b, rho) for (a, b), rho in matrix.items() if a < b]
        if pairs:
            max_pair = max(pairs, key=lambda item: abs(item[2]))
            if abs(max_pair[2]) >= 0.8:
                avisos.append(f"correlacao alta: {max_pair[0]}/{max_pair[1]}={max_pair[2]:.3f}")
    if leverage > 1.0:
        avisos.append(f"leverage bruta acima de 1x: {leverage:.3f}")
    nota = "Relatorio descritivo; nao e gate. capital_authorized=false."
    return PortfolioReport(
        len(positions), gross, leverage, hhi, exposure, max_pair, tuple(avisos), nota
    )


def render(report: PortfolioReport) -> str:
    lines = [
        f"Posicoes: {report.n_positions}",
        f"Notional bruto: {report.gross_notional:.2f}",
        f"Leverage bruta: {report.gross_leverage:.4f}",
        f"HHI: {report.concentration_hhi:.4f}",
        report.nota,
    ]
    lines.extend(f"AVISO: {warning}" for warning in report.avisos)
    return "\n".join(lines)
