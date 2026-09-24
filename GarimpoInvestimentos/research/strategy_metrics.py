"""Métricas de estratégia sobre P&L LÍQUIDO, com referência de cada fórmula.

Base única de Sharpe (`SHARPE_BASIS`): Sharpe POR DECISÃO, média / desvio amostral, sem
anualizar (`predictor_core.measurement.stats.sharpe` com `periods_per_year=1`) — a mesma
base dos baselines do Prompt 3a (`backtest_v3._series_metrics`), para que candidato e
baselines sejam comparáveis. O V[SR] do DSR tem de vir de Sharpes de tentativas NESSA
base. O PSR do core usa internamente o desvio populacional; a diferença é o fator
√(n/(n−1)), de ordem 1/(2n), e fica declarada aqui.

- PSR: Bailey & López de Prado (2012), "The Sharpe Ratio Efficient Frontier",
  Journal of Risk 15(2). PSR(SR*) = Φ((SR − SR*)·√(T−1) / √(1 − γ3·SR + (γ4−1)/4·SR²)),
  γ3 = assimetria, γ4 = curtose NÃO-excesso. Implementação: `predictor_core` (PSR sobre
  a série) e `psr_from_moments` (mesma fórmula a partir dos momentos, para conferência).
- DSR: Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", Journal of Portfolio
  Management 40(5). DSR = PSR(SR0), SR0 = √V[SR]·((1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(N·e))),
  γ = Euler–Mascheroni. SR0 vem de `predictor_core.measurement.trials.expected_max_sharpe`;
  V[SR] vem de `trial_sharpe_variance` (só tentativas com `sharpe_basis` igual).
- PBO: Bailey, Borwein, López de Prado & Zhu (2017), "The Probability of Backtest
  Overfitting", Journal of Computational Finance 20(4). CSCV em
  `GarimpoInvestimentos.analyzers.pbo` (arquivo protegido; reutilizado, não copiado).
- Max drawdown: max_t (pico_t − equity_t)/pico_t sobre a equity composta
  ∏(1 + r), começando em 1 — `predictor_core.measurement.stats.max_drawdown`.
- Turnover: média por período de |p_t − p_{t−1}|, com p_{−1} = 0 e a liquidação final
  contada; com `round_trip=True` (cada decisão do V3 abre e fecha no horizonte) cada
  período negocia 2·|p_t|.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from statistics import NormalDist
from typing import Any

from predictor_core.measurement.stats import max_drawdown as _core_max_drawdown
from predictor_core.measurement.stats import probabilistic_sharpe_ratio
from predictor_core.measurement.stats import sharpe as _core_sharpe
from predictor_core.measurement.trials import DeflationNotEstimableError, expected_max_sharpe

from GarimpoInvestimentos.analyzers.pbo import PBOResult, probability_of_backtest_overfitting

SHARPE_BASIS = "per_decision_unannualized_sample_std"


def per_decision_sharpe(returns: Sequence[float]) -> float:
    return _core_sharpe(list(returns), periods_per_year=1)


def scenario_label(multiplier: int) -> str:
    return "N" if multiplier == 1 else f"{multiplier}N"


def max_drawdown(net_returns: Sequence[float]) -> float:
    equity, level = [1.0], 1.0
    for r in net_returns:
        level *= 1.0 + r
        equity.append(level)
    return _core_max_drawdown(equity)


def turnover(positions: Sequence[float], *, round_trip: bool = False) -> float:
    if not positions:
        return float("nan")
    if round_trip:
        return sum(2.0 * abs(p) for p in positions) / len(positions)
    traded, previous = 0.0, 0.0
    for p in positions:
        traded += abs(p - previous)
        previous = p
    return (traded + abs(previous)) / len(positions)


def psr(returns: Sequence[float], benchmark_sharpe: float = 0.0) -> float:
    return probabilistic_sharpe_ratio(list(returns), benchmark_sharpe=benchmark_sharpe)


def psr_from_moments(
    sharpe: float, *, skew: float, kurtosis: float, n: int, benchmark_sharpe: float = 0.0
) -> float:
    if n < 3:
        return float("nan")
    variance = (1.0 - skew * sharpe + ((kurtosis - 1.0) / 4.0) * sharpe**2) / (n - 1)
    if variance <= 0:
        return float("nan")
    return NormalDist().cdf((sharpe - benchmark_sharpe) / math.sqrt(variance))


def deflated_sharpe(returns: Sequence[float], *, n_trials: int, var_trials_sr: float) -> dict:
    """DSR com N e V[SR] explícitos. Sem desconto possível → erro, nunca PSR disfarçado."""
    if isinstance(n_trials, bool) or not isinstance(n_trials, int) or n_trials < 2:
        raise DeflationNotEstimableError(f"N de tentativas inválido para deflação: {n_trials!r}")
    if not (isinstance(var_trials_sr, float | int) and math.isfinite(var_trials_sr)):
        raise DeflationNotEstimableError("V[SR] das tentativas ausente ou não finito")
    if var_trials_sr <= 0:
        raise DeflationNotEstimableError("V[SR] <= 0: sem desconto, o DSR seria o PSR puro")
    sr0 = expected_max_sharpe(n_trials, var_trials_sr)
    return {"n_trials": n_trials, "sr0": sr0, "dsr": psr(returns, sr0)}


def trial_sharpe_variance(
    trials: Sequence[Mapping[str, Any]], *, sharpe_basis: str = SHARPE_BASIS
) -> float:
    """V[SR] das tentativas, só com Sharpes comprovadamente na mesma base.

    Mesma regra de `analyzers.trials.registry_deflated_sharpe_ratio`: Sharpe finito sem
    `params.sharpe_basis` igual à base pedida torna o V[SR] não estimável.
    """
    sharpes = []
    for trial in trials:
        value = trial.get("sharpe")
        if not isinstance(value, int | float) or isinstance(value, bool):
            continue
        if not math.isfinite(value):
            continue
        if (trial.get("params") or {}).get("sharpe_basis") != sharpe_basis:
            raise DeflationNotEstimableError(
                f"base de Sharpe não comprovada para {trial.get('name')!r}; "
                f"esperado {sharpe_basis!r}"
            )
        sharpes.append(float(value))
    if len(sharpes) < 2:
        raise DeflationNotEstimableError(f"V[SR] exige >= 2 Sharpes na base {sharpe_basis!r}")
    return statistics.variance(sharpes)


def n_trials_scenarios(
    n_lower_bound: int, *, multipliers: Sequence[int], n_upper: int | None
) -> dict[str, int]:
    """N, 2N, 5N… (multiplicadores da política) e N_upper, quando estimado."""
    scenarios = {scenario_label(m): n_lower_bound * m for m in multipliers}
    if n_upper is not None:
        scenarios["N_upper"] = n_upper
    return scenarios


def dsr_sensitivity(
    returns: Sequence[float], *, scenarios: Mapping[str, int], var_trials_sr: float
) -> dict:
    """DSR em cada cenário de N; o pior caso (menor DSR) é o que decide."""
    by_n = {
        label: deflated_sharpe(returns, n_trials=n, var_trials_sr=var_trials_sr)
        for label, n in scenarios.items()
    }
    worst = min(by_n, key=lambda label: by_n[label]["dsr"])
    return {"by_n": by_n, "worst_label": worst, "worst_dsr": by_n[worst]["dsr"]}


def pbo_cscv(returns_by_config: Mapping[str, Sequence[float]], *, n_splits: int) -> PBOResult:
    return probability_of_backtest_overfitting(dict(returns_by_config), n_splits=n_splits)


def strategy_metrics(
    net_returns: Sequence[float], positions: Sequence[float], *, round_trip: bool
) -> dict:
    return {
        "sharpe_basis": SHARPE_BASIS,
        "net_sharpe": per_decision_sharpe(net_returns),
        "max_drawdown": max_drawdown(net_returns),
        "turnover": turnover(positions, round_trip=round_trip),
        "psr": psr(net_returns),
        "n_observations": len(net_returns),
    }
