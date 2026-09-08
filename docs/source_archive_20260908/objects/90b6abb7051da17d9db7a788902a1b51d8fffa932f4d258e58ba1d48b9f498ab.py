"""Eventos discretos (Fase 5 — futebol) — contrato e alinhamento event-asof.

O Alignment Engine das Fases 0-4 é series-asof (grade temporal contínua, forward fill).
Futebol é evento discreto: a grade são as PARTIDAS, e a regra anti-vazamento é "só
informação pública ANTES do kickoff". Este módulo adiciona esse 2º modo SEM tocar o
engine de séries (ver ADR-012). Continua desenho/piloto — o domínio wc-predictor-v2
segue PARKED; o código aqui é testável offline.
"""

from __future__ import annotations

import abc
import bisect
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from GarimpoInvestimentos.dpl.signals import SignalPoint

NaN = float("nan")


@dataclass(frozen=True, eq=False)
class MatchObservation:
    """Observação ligada a uma partida. `published_at` < kickoff = pré-jogo (pode
    alimentar a previsão); > kickoff = pós-jogo (só alimenta partidas futuras)."""

    source: str
    match_id: str
    kickoff: datetime
    home_id: str  # canonical_id (via EntityMapper)
    away_id: str
    published_at: datetime
    payload: dict = field(default_factory=dict)


class MatchDataProvider(abc.ABC):
    """Contrato de uma fonte de partidas/estatísticas. Implementações canonicalizam
    entidades via EntityMapper antes de emitir; registros não-mapeados são pulados."""

    name: str = "abstract_match"

    @abc.abstractmethod
    async def fetch_matches(self, limit: int = 100) -> list[MatchObservation]:
        """Retorna observações de partidas, com home_id/away_id já canônicos."""


class EventAlignmentEngine:
    """Alinha features pré-jogo a cada partida por as-of em published_at < kickoff."""

    def align(
        self,
        matches: list[MatchObservation],
        signals: dict[str, list[SignalPoint]] | None = None,
        max_staleness: dict[str, timedelta] | None = None,
        inclusive: bool = False,
    ) -> list[dict]:
        """Para cada partida (ordenada por kickoff), monta {match_id, kickoff, home_id,
        away_id, <signal>: valor|NaN}. Um sinal só entra se foi público antes do
        kickoff (anti-vazamento). `inclusive=False` → estritamente ANTES (recomendado).
        """
        signals = signals or {}
        max_staleness = max_staleness or {}
        prepared = {}
        for name, series in signals.items():
            s = sorted(series, key=lambda x: x.published_at)
            prepared[name] = (s, [x.published_at for x in s])

        rows = []
        for m in sorted(matches, key=lambda x: x.kickoff):
            row = {
                "match_id": m.match_id,
                "kickoff": m.kickoff,
                "home_id": m.home_id,
                "away_id": m.away_id,
            }
            for name, (s_sorted, pub_keys) in prepared.items():
                row[name] = self._asof(
                    s_sorted, pub_keys, m.kickoff, max_staleness.get(name), inclusive
                )
            rows.append(row)
        return rows

    @staticmethod
    def _asof(s_sorted, pub_keys, kickoff, max_staleness, inclusive):
        # nº de sinais publicados antes (ou até) o kickoff
        idx = (
            bisect.bisect_right(pub_keys, kickoff)
            if inclusive
            else bisect.bisect_left(pub_keys, kickoff)
        )
        if idx == 0:
            return NaN
        sig = s_sorted[idx - 1]
        if not inclusive and sig.published_at == kickoff:
            return NaN  # publicado exatamente no kickoff não conta (anti-vazamento)
        if max_staleness is not None and (kickoff - sig.timestamp) > max_staleness:
            return NaN
        return sig.value
