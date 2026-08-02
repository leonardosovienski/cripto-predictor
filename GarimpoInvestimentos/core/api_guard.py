"""Orçamento determinístico antes das bordas de rede da Fase 1.

Não tenta substituir o rate-limit do provedor. A finalidade é impedir que o
orquestrador inicie uma nova unidade lógica de trabalho depois do teto declarado.
"""

from collections import defaultdict
from dataclasses import dataclass

from predictor_core.obs import emit_event

from GarimpoInvestimentos.config import settings


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    reason: str


_COUNTS: dict[tuple[str, str], int] = defaultdict(int)
# Auditoria hostil 2026-07-17: API_GUARD_ENABLED tem default False (padrão de
# instalação nova), e o ramo "disabled" abaixo não emitia log nem evento
# algum — se ninguém setasse a env var, o orçamento nunca protegeu nada
# desde o início, e não havia como saber isso sem ler o .env ou o
# código-fonte. Este flag garante UM evento por processo (não um por
# chamada — allow() roda por ativo/provider, seria ruído) avisando que o
# guard está inativo.
_disabled_notice_emitted = False


def allow(stage: str, key: str, limit: int) -> GuardDecision:
    """Consome uma unidade somente se ela puder iniciar dentro do orçamento."""
    if not settings.API_GUARD_ENABLED or limit <= 0:
        global _disabled_notice_emitted
        if not _disabled_notice_emitted:
            emit_event(
                "previsao_cripto",
                "api_guard_disabled",
                metrics={},
                metadata={
                    "reason": "API_GUARD_ENABLED is false or limit<=0",
                    "stage": stage,
                    "key": key,
                },
            )
            _disabled_notice_emitted = True
        return GuardDecision(True, "disabled")
    counter = (stage, key)
    if _COUNTS[counter] >= limit:
        return GuardDecision(False, f"budget_exhausted:{stage}:{key}")
    _COUNTS[counter] += 1
    return GuardDecision(True, "allowed")


def reset_for_test() -> None:
    _COUNTS.clear()
    global _disabled_notice_emitted
    _disabled_notice_emitted = False
