"""Orçamento determinístico antes das bordas de rede da Fase 1.

Não tenta substituir o rate-limit do provedor. A finalidade é impedir que o
orquestrador inicie uma nova unidade lógica de trabalho depois do teto declarado.
"""
from collections import defaultdict
from dataclasses import dataclass

from GarimpoInvestimentos.config import settings


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    reason: str


_COUNTS: dict[tuple[str, str], int] = defaultdict(int)


def allow(stage: str, key: str, limit: int) -> GuardDecision:
    """Consome uma unidade somente se ela puder iniciar dentro do orçamento."""
    if not settings.API_GUARD_ENABLED or limit <= 0:
        return GuardDecision(True, "disabled")
    counter = (stage, key)
    if _COUNTS[counter] >= limit:
        return GuardDecision(False, f"budget_exhausted:{stage}:{key}")
    _COUNTS[counter] += 1
    return GuardDecision(True, "allowed")


def reset_for_test() -> None:
    _COUNTS.clear()
