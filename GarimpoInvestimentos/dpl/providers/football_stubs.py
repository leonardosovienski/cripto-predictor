"""Stubs das fontes de futebol que dependem de rede/scraping (Fase 5 — desenho).

Todas seguem o contrato MatchDataProvider e canonicalizam via EntityMapper. A
implementação real (HTTP/scraping) fica para quando wc-predictor-v2 sair do PARKED;
os contratos abaixo fixam a forma esperada e mantêm o domínio plugável. Cada uma
emitiria MatchObservation (estatísticas/odds/escalações/clima) com published_at
correto: pré-jogo (odds, escalação provável, clima previsto) < kickoff; pós-jogo
(estatísticas finais) > kickoff.
"""
from __future__ import annotations

from GarimpoInvestimentos.dpl.entity_mapper import EntityMapper
from GarimpoInvestimentos.dpl.events import MatchDataProvider, MatchObservation


class _NetworkMatchProvider(MatchDataProvider):
    """Base dos providers de rede: guarda o mapper; fetch real a implementar."""

    def __init__(self, mapper: EntityMapper):
        self._mapper = mapper

    async def fetch_matches(self, limit: int = 100) -> list[MatchObservation]:
        raise NotImplementedError(
            f"{self.name}: provider de rede — implementar quando wc-predictor-v2 "
            "sair do PARKED (Fase 5).")


class SofascoreProvider(_NetworkMatchProvider):
    """Estatísticas detalhadas, escalações, odds (pré e pós-jogo)."""
    name = "sofascore"


class FBrefProvider(_NetworkMatchProvider):
    """Estatísticas avançadas (xG, posse, passes) — tipicamente pós-jogo."""
    name = "fbref"


class OddsProvider(_NetworkMatchProvider):
    """Odds de casas de apostas — pré-jogo (published_at < kickoff)."""
    name = "odds"


class WeatherProvider(_NetworkMatchProvider):
    """Clima previsto para o estádio — pré-jogo."""
    name = "weather"
