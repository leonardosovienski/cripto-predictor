"""Deduplicação ANTES do backtest (Prompt 4, item 6).

Compara uma candidata nova com os fatores existentes, só no período de DESENVOLVIMENTO, pelo
Spearman do core. Se |ρ| com algum fator >= limiar, a candidata é REJECTED_REDUNDANT e não gasta
backtest nem holdout. O filtro só controla redundância; não prova equivalência econômica.

O limiar é argumento obrigatório, sem default: ele tem de vir da política versionada ou do
pré-registro, e a origem vai registrada no resultado. A política v1 não tem esse limiar; o
0,99 do Prompt 4 precisa ser aprovado numa v2 antes de virar regra.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from predictor_core.measurement.stats import spearman


class DedupError(ValueError):
    """Séries incomparáveis: sem deduplicação, não há backtest."""


def redundancy_check(
    candidate_id: str,
    candidate: Sequence[float],
    factors: Mapping[str, Sequence[float]],
    *,
    development_period: tuple[str, str],
    threshold: float,
    threshold_source: str,
) -> dict:
    if not factors:
        raise DedupError("sem fatores existentes para comparar")
    if not 0.0 < threshold <= 1.0 or not threshold_source:
        raise DedupError("limiar em (0, 1] com origem declarada é obrigatório")
    similarities = {}
    for name, values in factors.items():
        if len(values) != len(candidate):
            raise DedupError(f"fator {name} não está alinhado com a candidata")
        if any(not math.isfinite(x) for x in (*values, *candidate)):
            raise DedupError("séries com valor não finito")
        rho = spearman(list(candidate), list(values))
        if rho is None:
            raise DedupError(f"Spearman indefinido contra {name}")
        similarities[name] = rho
    closest = max(similarities, key=lambda k: abs(similarities[k]))
    value = similarities[closest]
    return {
        "candidate": candidate_id,
        "closest_factor": closest,
        "metric": "spearman_rho (predictor_core)",
        "value": value,
        "abs_value": abs(value),
        "development_period": list(development_period),
        "threshold": threshold,
        "threshold_source": threshold_source,
        "status": "REJECTED_REDUNDANT" if abs(value) >= threshold else "NOT_REDUNDANT",
        "all_similarities": similarities,
    }
