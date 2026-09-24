"""Métricas de previsão probabilística por quantis.

- Perda quantílica (pinball): ρ_τ(y, q) = (y − q)·(τ − 1{y < q}). Koenker & Bassett (1978),
  "Regression Quantiles", Econometrica 46(1).
- CRPS como integral da perda quantílica: CRPS(F, y) = 2 ∫₀¹ ρ_τ(y, F⁻¹(τ)) dτ. Gneiting &
  Raftery (2007), "Strictly Proper Scoring Rules, Prediction, and Estimation", JASA 102(477);
  Laio & Tamea (2007), HESS 11. `crps_from_quantiles` = 2·média de ρ_τ nos K níveis dados:
  aproximação da integral; com os 9 níveis 0,1..0,9 as caudas além de 0,1/0,9 ficam de fora.
- CRPS fechado da normal: σ[z(2Φ(z) − 1) + 2φ(z) − 1/√π], z = (y − μ)/σ (Gneiting & Raftery,
  2007). Serve de conferência numérica da aproximação.
- WQL (Ansari et al. 2024, "Chronos: Learning the Language of Time Series", TMLR):
  Σ_t Σ_τ 2·ρ_τ / (K · Σ_t |y_t|).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from statistics import NormalDist


def pinball_loss(y: float, q: float, tau: float) -> float:
    if not 0.0 < tau < 1.0:
        raise ValueError("tau precisa estar em (0, 1)")
    return (y - q) * (tau - (1.0 if y < q else 0.0))


def _check(quantiles: Mapping[float, float]) -> list[tuple[float, float]]:
    items = sorted(quantiles.items())
    if not items:
        raise ValueError("previsão sem quantis")
    if any(not math.isfinite(q) for _, q in items):
        raise ValueError("quantil não finito")
    if any(b[1] < a[1] for a, b in zip(items, items[1:], strict=False)):
        raise ValueError("quantis cruzados (não monotônicos)")
    return items


def mean_quantile_loss(y: float, quantiles: Mapping[float, float]) -> float:
    items = _check(quantiles)
    return sum(pinball_loss(y, q, tau) for tau, q in items) / len(items)


def crps_from_quantiles(y: float, quantiles: Mapping[float, float]) -> float:
    return 2.0 * mean_quantile_loss(y, quantiles)


def weighted_quantile_loss(
    ys: Sequence[float], forecasts: Sequence[Mapping[float, float]]
) -> float:
    if len(ys) != len(forecasts) or not ys:
        raise ValueError("alvos e previsões precisam ter o mesmo tamanho, > 0")
    scale = sum(abs(y) for y in ys)
    if scale == 0:
        return float("nan")
    k = len(forecasts[0])
    total = sum(
        2.0 * pinball_loss(y, q, tau)
        for y, f in zip(ys, forecasts, strict=True)
        for tau, q in _check(f)
    )
    return total / (k * scale)


def crps_gaussian(y: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        raise ValueError("sigma precisa ser > 0")
    nd = NormalDist()
    z = (y - mu) / sigma
    return sigma * (z * (2.0 * nd.cdf(z) - 1.0) + 2.0 * nd.pdf(z) - 1.0 / math.sqrt(math.pi))
