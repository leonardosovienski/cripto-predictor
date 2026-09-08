"""Prefiltro determinístico e auditável para controlar custo de inferência.

O filtro não calcula nem altera o score: apenas decide se um ativo recebe chamada de
LLM. Ele usa somente features já presentes na Feature Store, portanto não introduz
rede nem look-ahead. Ainda assim muda a população do experimento e é opt-in.
"""

from dataclasses import dataclass

from GarimpoInvestimentos.analyzers.score_engine import technical_direction
from GarimpoInvestimentos.config import settings


@dataclass(frozen=True)
class PrefilterDecision:
    selected: bool
    reason: str


def decide(hard_data: dict) -> PrefilterDecision:
    """Aplica regras fixas de liquidez + momentum + direção técnica.

    A direção pode ser bull ou bear: o filtro busca movimento mensurável, não
    somente alta. Sem os campos necessários, a decisão é excluir com razão
    explícita, nunca inventar um valor.
    """
    if not settings.LLM_PREFILTER_ENABLED:
        return PrefilterDecision(True, "disabled")
    volume = hard_data.get("volume_usd")
    if not isinstance(volume, (int, float)) or volume < settings.LLM_PREFILTER_MIN_VOLUME_USD:
        return PrefilterDecision(False, "low_or_missing_volume")
    change_7d = hard_data.get("change_7d")
    if not isinstance(change_7d, (int, float)):
        return PrefilterDecision(False, "missing_change_7d")
    if abs(change_7d) < settings.LLM_PREFILTER_MIN_ABS_CHANGE_7D:
        return PrefilterDecision(False, "weak_7d_momentum")
    direction = technical_direction(hard_data.get("indicadores", {}))
    if direction not in {"bull", "bear"}:
        return PrefilterDecision(False, "neutral_or_missing_technical_direction")
    return PrefilterDecision(True, f"technical_{direction}")
