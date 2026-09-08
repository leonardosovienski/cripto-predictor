"""Portfólio — risco agregado sobre um conjunto de Position (trading/contracts.py).

Parte do override de governança 2026-08-14 (docs/HYPOTHESES.md). Hoje cada posição é
avaliada ISOLADAMENTE no backtest (Spearman por ativo, PSR por símbolo) — nada agrega
risco entre posições. Este módulo fecha essa lacuna como matemática pura, sem
depender de nenhum sinal ter edge validado: beta a um benchmark, correlação,
concentração (HHI), exposição por venue/chave arbitrária, leverage agregado,
vol targeting, drawdown centralizado, distância de liquidação (aproximada) e
reconciliação de saldo.

Todas as funções são puras (recebem dado, devolvem número/dataclass) — quem
alimenta com preço/saldo real é responsabilidade de quem chama; nada aqui faz
rede ou lê a Feature Store diretamente.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from statistics import StatisticsError
from statistics import correlation as _correlation
from statistics import covariance as _covariance
from statistics import variance as _variance

from GarimpoInvestimentos.trading.contracts import Direction, Position


def _require_paired_series(a: list[float], b: list[float], label: str) -> None:
    if len(a) != len(b):
        raise ValueError(f"{label}: séries precisam ter o mesmo tamanho")
    if len(a) < 2:
        raise ValueError(f"{label}: precisa de ao menos 2 observações")


def beta(asset_returns: list[float], benchmark_returns: list[float]) -> float:
    """Beta OLS simples: Cov(ativo, benchmark) / Var(benchmark)."""
    _require_paired_series(asset_returns, benchmark_returns, "beta")
    var = _variance(benchmark_returns)
    if var == 0:
        raise ValueError("beta: variância do benchmark é zero")
    return _covariance(asset_returns, benchmark_returns) / var


def correlation(series_a: list[float], series_b: list[float]) -> float:
    """Correlação de Pearson (statistics.correlation da stdlib, Python 3.10+)."""
    _require_paired_series(series_a, series_b, "correlation")
    try:
        return _correlation(series_a, series_b)
    except StatisticsError as exc:
        raise ValueError(f"correlation: {exc}") from exc


def correlation_matrix(returns_by_asset: dict[str, list[float]]) -> dict[tuple[str, str], float]:
    """Matriz completa (simétrica, diagonal=1.0) como dict {(ativo_a, ativo_b): rho}."""
    assets = sorted(returns_by_asset)
    out: dict[tuple[str, str], float] = {}
    for i, a in enumerate(assets):
        for b in assets[i:]:
            rho = 1.0 if a == b else correlation(returns_by_asset[a], returns_by_asset[b])
            out[(a, b)] = rho
            out[(b, a)] = rho
    return out


def concentration_hhi(notionals_by_key: dict[str, float]) -> float:
    """Índice Herfindahl-Hirschman: soma dos quadrados das participações.
    1/N = perfeitamente diversificado entre N chaves iguais; 1.0 = tudo numa só."""
    total = sum(abs(v) for v in notionals_by_key.values())
    if total <= 0:
        raise ValueError("concentration_hhi: soma dos notionais deve ser > 0")
    return sum((abs(v) / total) ** 2 for v in notionals_by_key.values())


def exposure_by(
    positions: Iterable[Position],
    mark_prices: dict[str, float],
    key_fn: Callable[[Position], str],
) -> dict[str, float]:
    """Agrega notional ASSINADO (LONG positivo, SHORT negativo) por uma chave
    arbitrária — venue, stablecoin de settlement etc., via `key_fn(position)`."""
    out: dict[str, float] = {}
    for pos in positions:
        mark = mark_prices.get(pos.instrument.key)
        if mark is None:
            raise ValueError(f"exposure_by: falta mark price para {pos.instrument.key}")
        sign = 1.0 if pos.direction is Direction.LONG else -1.0
        key = key_fn(pos)
        out[key] = out.get(key, 0.0) + sign * pos.notional(mark)
    return out


def exchange_exposure(
    positions: Iterable[Position], mark_prices: dict[str, float]
) -> dict[str, float]:
    return exposure_by(positions, mark_prices, lambda p: p.instrument.venue)


def aggregate_leverage(
    positions: Iterable[Position], mark_prices: dict[str, float], equity: float
) -> float:
    """Leverage bruta agregada: soma dos notionais absolutos / equity. Não
    distingue direção (um LONG e um SHORT do mesmo tamanho ainda somam leverage
    bruta — é o risco operacional/de margem, não o risco direcional líquido)."""
    if equity <= 0:
        raise ValueError("aggregate_leverage: equity deve ser > 0")
    gross_notional = 0.0
    for pos in positions:
        mark = mark_prices.get(pos.instrument.key)
        if mark is None:
            raise ValueError(f"aggregate_leverage: falta mark price para {pos.instrument.key}")
        gross_notional += pos.notional(mark)
    return gross_notional / equity


def volatility_target_size(target_vol: float, asset_vol: float, capital: float) -> float:
    """Tamanho de posição (em unidades de capital) pra atingir uma vol-alvo dado a
    vol realizada do ativo — fração = min(target_vol/asset_vol, 1.0), capada em
    1x o capital (alavancagem explícita acima disso é decisão separada, fora
    deste cálculo)."""
    if target_vol < 0 or asset_vol < 0:
        raise ValueError("volatility_target_size: vols não podem ser negativas")
    if asset_vol == 0:
        raise ValueError("volatility_target_size: asset_vol zero — indefinido")
    if capital <= 0:
        raise ValueError("volatility_target_size: capital deve ser > 0")
    fraction = min(target_vol / asset_vol, 1.0)
    return fraction * capital


@dataclass
class DrawdownTracker:
    """Rastreia drawdown a partir de uma série de patrimônio (equity) chamada
    incrementalmente — pico corrente, drawdown atual, drawdown máximo. Estado
    mutável de propósito: é um tracker, não um valor imutável."""

    _peak: float | None = field(default=None, repr=False)
    _current_drawdown: float = field(default=0.0, repr=False)
    _max_drawdown: float = field(default=0.0, repr=False)

    def update(self, equity: float) -> float:
        if equity <= 0:
            raise ValueError("DrawdownTracker.update: equity deve ser > 0")
        if self._peak is None or equity > self._peak:
            self._peak = equity
        self._current_drawdown = (self._peak - equity) / self._peak
        self._max_drawdown = max(self._max_drawdown, self._current_drawdown)
        return self._current_drawdown

    @property
    def current_drawdown(self) -> float:
        return self._current_drawdown

    @property
    def max_drawdown(self) -> float:
        return self._max_drawdown


def liquidation_distance_pct(
    direction: Direction, leverage: float, maintenance_margin_rate: float
) -> float:
    """Distância percentual aproximada do preço de entrada até a liquidação sob
    alavancagem isolada: margin_fraction (1/leverage) menos a margem de
    manutenção — mesma magnitude pra LONG e SHORT neste modelo simplificado
    (direção fica explícita no retorno só pra deixar claro de que lado o preço
    se move). Aproximação didática: ignora funding acumulado, fees de
    liquidação e o modelo exato varia por exchange — NUNCA substitui o cálculo
    oficial do venue antes de operar de verdade."""
    if leverage <= 0:
        raise ValueError("liquidation_distance_pct: leverage deve ser > 0")
    if not (0 <= maintenance_margin_rate < 1):
        raise ValueError("liquidation_distance_pct: maintenance_margin_rate deve estar em [0, 1)")
    margin_fraction = 1.0 / leverage
    if margin_fraction <= maintenance_margin_rate:
        raise ValueError(
            "liquidation_distance_pct: margem inicial <= margem de manutenção — "
            "posição já estaria liquidável"
        )
    _ = direction  # reservado para modelos futuros com custo assimétrico por lado
    return margin_fraction - maintenance_margin_rate


@dataclass(frozen=True)
class BalanceReconciliationBreak:
    venue: str
    local_balance: float
    reported_balance: float

    @property
    def delta(self) -> float:
        return self.local_balance - self.reported_balance


def reconcile_balance(
    venue: str, local_balance: float, reported_balance: float, *, tolerance: float = 1e-6
) -> BalanceReconciliationBreak | None:
    """`None` se bater dentro da tolerância; `BalanceReconciliationBreak` se
    divergir — NUNCA ajusta o saldo local sozinho pra "resolver" a divergência,
    mesmo princípio de `trading.execution.reconcile`."""
    if abs(local_balance - reported_balance) <= tolerance:
        return None
    return BalanceReconciliationBreak(venue, local_balance, reported_balance)
