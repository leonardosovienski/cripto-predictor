"""Calendário macro (FOMC/CPI/PPI) → SignalPoint de dummy de janela de evento.

Parte do backlog B1 (docs/HYPOTHESES.md, H7): calendário de eventos macro como
contexto exógeno, ortogonal a tudo que já foi testado no projeto (nenhum sinal
atual olha agenda macro). Fonte: um JSON local versionado, sem rede — datas de
reunião do FOMC e de divulgação de CPI/PPI são anunciadas pelo Fed/BLS com meses
de antecedência, então conhecê-las hoje para um evento futuro NÃO é look-ahead.

O arquivo padrão (macro_calendar.json) traz os calendários FOMC, CPI e PPI de
2026, verificados nas fontes primárias em 2026-08-31. Ver `source_note` dentro do
próprio JSON para a proveniência completa. Datas CPI/PPI representam o dia da
divulgação, não o mês de referência:
  - FOMC (re-verificação/anos futuros): https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
  - CPI/PPI: https://www.bls.gov/schedule/news_release/cpi.htm / .../ppi.htm
Datas não confirmadas na fonte primária não entram no arquivo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.signals import SignalPoint

_SCHEMA_VERSION = "macro-calendar/1"
DEFAULT_CALENDAR_PATH = Path(__file__).resolve().parent.parent / "macro_calendar.json"
SOURCE = "macro_calendar"


@dataclass(frozen=True)
class MacroEvent:
    event_type: str  # "FOMC" | "CPI" | "PPI" | ...
    event_date: date


def load_macro_calendar(path: Path | None = None) -> list[MacroEvent]:
    """Lê o calendário versionado. Levanta ValueError em schema desconhecido ou
    data malformada — falha alto, nunca ignora silenciosamente um evento inválido."""
    p = path or DEFAULT_CALENDAR_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError(f"{p}: schema_version inesperado ({raw.get('schema_version')!r})")
    events = []
    for item in raw.get("events", []):
        try:
            event_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
            event_type = str(item["event_type"]).strip().upper()
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{p}: evento malformado {item!r}") from exc
        if not event_type:
            raise ValueError(f"{p}: evento sem event_type {item!r}")
        events.append(MacroEvent(event_type=event_type, event_date=event_date))
    return events


def macro_event_signal_points(
    events: list[MacroEvent],
    day_range: list[date],
    *,
    ingested_at: datetime,
    window_days: int = 1,
) -> list[SignalPoint]:
    """Dummy 1.0/0.0 por (dia, tipo de evento): 1.0 se `day` está a até
    `window_days` dias (antes OU depois, inclusive) de um evento daquele tipo no
    calendário, senão 0.0. Um sinal por tipo de evento presente — não inventa
    tipos sem nenhuma data no calendário.

    published_at = timestamp: conservador de propósito. A data do evento já é
    pública com meses de antecedência (o piso real seria bem mais cedo), então
    usar o próprio dia como published_at nunca introduz look-ahead — só é mais
    cauteloso do que precisaria ser."""
    if window_days < 0:
        raise ValueError("window_days não pode ser negativo")
    event_types = sorted({e.event_type for e in events})
    points: list[SignalPoint] = []
    for event_type in event_types:
        event_dates = [e.event_date for e in events if e.event_type == event_type]
        for day in day_range:
            in_window = any(abs((day - ed).days) <= window_days for ed in event_dates)
            ts = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
            points.append(
                SignalPoint(
                    name=f"macro:{event_type.lower()}_window",
                    timestamp=ts,
                    value=1.0 if in_window else 0.0,
                    source=SOURCE,
                    published_at=ts,
                    ingested_at=ingested_at,
                    metric=f"{event_type.lower()}_window_dummy",
                    unit="dummy",
                )
            )
    return points


def persist_macro_signals(
    store: FeatureStore,
    *,
    events: list[MacroEvent],
    day_range: list[date],
    ingested_at: datetime,
    window_days: int = 1,
) -> int:
    points = macro_event_signal_points(
        events, day_range, ingested_at=ingested_at, window_days=window_days
    )
    return store.write_signals(points, scientific_state="COLLECTION_ONLY")


__all__ = [
    "DEFAULT_CALENDAR_PATH",
    "SOURCE",
    "MacroEvent",
    "load_macro_calendar",
    "macro_event_signal_points",
    "persist_macro_signals",
]
