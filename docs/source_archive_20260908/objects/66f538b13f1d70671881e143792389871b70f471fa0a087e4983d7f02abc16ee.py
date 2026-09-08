"""Martj42Provider — resultados históricos de seleções (dataset martj42, CSV).

Lê o CSV (date,home_team,away_team,home_score,away_score,tournament,...) e emite
MatchObservation com home_id/away_id JÁ canônicos (via EntityMapper). Registros com
entidade não-mapeada são PULADOS e registrados — nunca se inventa um time (ADR-013).
Sem rede: parser sobre linhas/CSV, testável com fixtures. As demais fontes (Sofascore,
FBref, odds, clima) seguem o mesmo contrato MatchDataProvider — ver stubs em
providers/football_stubs.py.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

from GarimpoInvestimentos.dpl.entity_mapper import EntityMapper
from GarimpoInvestimentos.dpl.events import MatchDataProvider, MatchObservation


class Martj42Provider(MatchDataProvider):
    name = "martj42"

    def __init__(self, mapper: EntityMapper, *, publish_lag_hours: int = 3):
        self._mapper = mapper
        self._lag = timedelta(hours=publish_lag_hours)
        self.unmapped: list[tuple[str, str]] = []  # (source_name, raw) p/ curadoria

    def parse_csv(self, text: str) -> list[MatchObservation]:
        out: list[MatchObservation] = []
        for row in csv.DictReader(io.StringIO(text)):
            home_id = self._mapper.resolve("martj42", row["home_team"], "team")
            away_id = self._mapper.resolve("martj42", row["away_team"], "team")
            if home_id is None:
                self.unmapped.append(("martj42", row["home_team"]))
            if away_id is None:
                self.unmapped.append(("martj42", row["away_team"]))
            if home_id is None or away_id is None:
                continue  # bloqueia registro com entidade fantasma
            kickoff = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=UTC)
            out.append(
                MatchObservation(
                    source="martj42",
                    match_id=f"{row['date']}_{home_id}_{away_id}",
                    kickoff=kickoff,
                    home_id=home_id,
                    away_id=away_id,
                    published_at=kickoff + self._lag,  # resultado público após o jogo
                    payload={
                        "home_score": _int(row.get("home_score")),
                        "away_score": _int(row.get("away_score")),
                        "tournament": row.get("tournament"),
                    },
                )
            )
        return out

    async def fetch_matches(self, limit: int = 100) -> list[MatchObservation]:
        raise NotImplementedError(
            "martj42: carregue via parse_csv(text). fetch_matches (rede) é stub."
        )


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
