"""Macro covariates with explicit observed publication timestamps.

Daily observations are not daily releases. A business-day lag is available only
as an explicitly named historical assumption and cannot prove causal availability.
Missing values require a measured coverage check before any model fit.
"""

from __future__ import annotations

import csv
import math
from bisect import insort
from datetime import UTC, date, datetime
from pathlib import Path

from GarimpoInvestimentos.dpl.business_days import published_at
from GarimpoInvestimentos.dpl.macro_calendar import MacroEvent, load_macro_calendar
from GarimpoInvestimentos.trading.contracts import ensure_utc
from GarimpoInvestimentos.v3.feature_builder import FeatureVector


def _ts_to_date(timestamp_exchange_ms: int) -> date:
    return datetime.fromtimestamp(timestamp_exchange_ms / 1000, tz=UTC).date()


def build_macro_event_dummy(
    feature_vectors: list[FeatureVector],
    *,
    calendar_path: Path | None = None,
    window_days: int = 1,
    events: list[MacroEvent] | None = None,
    calendar_available_at: datetime | None = None,
    assume_calendar_known: bool = False,
) -> list[float]:
    """1.0 se o dia do ponto está a até `window_days` dias (antes OU depois,
    inclusive) de QUALQUER evento macro no calendário; 0.0 caso contrário.
    Combina FOMC/CPI/PPI com OR — o RegimeEngine recebe uma covariável escalar
    por ponto, não uma por tipo de evento.

    `events`: injeção direta para teste (evita reler o JSON); se omitido, carrega
    de `calendar_path` (ou do arquivo padrão do projeto).
    """
    if isinstance(window_days, bool) or not isinstance(window_days, int) or window_days < 0:
        raise ValueError("window_days não pode ser negativo")
    if not assume_calendar_known:
        if calendar_available_at is None:
            raise ValueError("Calendario exige calendar_available_at documentado para sua versao")
        known = ensure_utc(calendar_available_at, "calendar_available_at")
        if any(fv.timestamp_exchange_ms < int(known.timestamp() * 1000) for fv in feature_vectors):
            raise ValueError("Calendario nao estava documentado no instante de todas as features")
    ev = events if events is not None else load_macro_calendar(calendar_path)
    if not assume_calendar_known:
        years = {event.event_date.year for event in ev}
        if not ev or any(
            _ts_to_date(fv.timestamp_exchange_ms).year not in years for fv in feature_vectors
        ):
            raise ValueError("Calendario sem cobertura para os anos das features")
    event_dates = [e.event_date for e in ev]
    out = []
    for fv in feature_vectors:
        day = _ts_to_date(fv.timestamp_exchange_ms)
        in_window = any(abs((day - ed).days) <= window_days for ed in event_dates)
        out.append(1.0 if in_window else 0.0)
    return out


def _aligned_dxy(
    feature_vectors: list[FeatureVector],
    closes: dict[date, float],
    *,
    available_at: dict[date, datetime] | None,
    publish_lag_days: int,
    assume_business_day_lag: bool,
) -> list[float | None]:
    if (
        isinstance(publish_lag_days, bool)
        or not isinstance(publish_lag_days, int)
        or publish_lag_days < 0
    ):
        raise ValueError("publish_lag_days nao pode ser negativo ou fracionario")
    if any(not math.isfinite(value) or value <= 0 for value in closes.values()):
        raise ValueError("DXY exige valores positivos finitos")
    if available_at is None:
        if not assume_business_day_lag:
            raise ValueError(
                "DXY exige available_at documentado por vintage; lag presumido nao prova publicacao"
            )
        available_at = {
            day: datetime.combine(
                published_at(day, publish_lag_days), datetime.min.time(), tzinfo=UTC
            )
            for day in closes
        }
    if set(closes) - set(available_at):
        raise ValueError("DXY sem data de disponibilidade para todas as observacoes")
    events = []
    for day in closes:
        stamp = ensure_utc(available_at[day], "available_at")
        if stamp.date() < day:
            raise ValueError("DXY publicado antes da referencia")
        events.append((int(stamp.timestamp() * 1000), day))
    events.sort()
    usable: list[date] = []
    cursor = 0
    out: list[float | None] = [None] * len(feature_vectors)
    for index, fv in sorted(
        enumerate(feature_vectors), key=lambda pair: pair[1].timestamp_exchange_ms
    ):
        while cursor < len(events) and events[cursor][0] <= fv.timestamp_exchange_ms:
            insort(usable, events[cursor][1])
            cursor += 1
        if len(usable) >= 2:
            out[index] = (closes[usable[-1]] / closes[usable[-2]] - 1) * 100.0
    return out


def build_dxy_return(
    feature_vectors: list[FeatureVector],
    dxy_daily_closes: dict[date, float],
    *,
    available_at: dict[date, datetime] | None = None,
    publish_lag_days: int = 1,
    assume_business_day_lag: bool = False,
) -> list[float]:
    """As-of DXY return. Zero imputation is exposed separately by dxy_coverage.

    A supplied timestamp must describe the availability of that exact value/vintage.
    Explicit lag assumptions are for reproduction, not a historical availability claim.
    """
    values = _aligned_dxy(
        feature_vectors,
        dxy_daily_closes,
        available_at=available_at,
        publish_lag_days=publish_lag_days,
        assume_business_day_lag=assume_business_day_lag,
    )
    return [0.0 if value is None else value for value in values]


def dxy_coverage(
    feature_vectors: list[FeatureVector],
    dxy_daily_closes: dict[date, float],
    *,
    available_at: dict[date, datetime] | None = None,
    publish_lag_days: int = 1,
    assume_business_day_lag: bool = False,
) -> tuple[int, int]:
    values = _aligned_dxy(
        feature_vectors,
        dxy_daily_closes,
        available_at=available_at,
        publish_lag_days=publish_lag_days,
        assume_business_day_lag=assume_business_day_lag,
    )
    return sum(value is None for value in values), len(values)


def _load_dxy_csv(path: Path) -> tuple[dict[date, float], dict[date, datetime]]:
    closes: dict[date, float] = {}
    available: dict[date, datetime] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if fields not in (
            ["date", "close"],
            ["date", "close", "published_at"],
            ["observation_date", "DTWEXBGS"],
        ):
            raise ValueError(f"{path}: cabecalho invalido")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}: linha malformada")
            raw_close = row[fields[1]]
            if fields[0] == "observation_date" and raw_close == ".":
                continue
            try:
                day = date.fromisoformat(row[fields[0]])
                close = float(raw_close)
                if not math.isfinite(close) or close <= 0:
                    raise ValueError("close nao positivo/finito")
                stamp = (
                    ensure_utc(datetime.fromisoformat(row["published_at"]), "published_at")
                    if "published_at" in row
                    else None
                )
            except ValueError as exc:
                raise ValueError(f"{path}: linha inválida") from exc
            if day in closes and (closes[day] != close or available.get(day) != stamp):
                raise ValueError(f"{path}: observacoes conflitantes; use uma tabela por vintage")
            closes[day] = close
            if stamp is not None:
                if stamp.date() < day:
                    raise ValueError("publicacao anterior a referencia")
                available[day] = stamp
    if not closes:
        raise ValueError(f"{path}: nenhum dado valido")
    return closes, available


def load_dxy_daily_closes(path: Path) -> dict[date, float]:
    return _load_dxy_csv(path)[0]


def load_dxy_availability(path: Path) -> dict[date, datetime]:
    closes, available = _load_dxy_csv(path)
    if closes.keys() != available.keys():
        raise ValueError("Historico DXY exige coluna published_at documentada para cada vintage")
    return available


__all__ = [
    "build_dxy_return",
    "dxy_coverage",
    "build_macro_event_dummy",
    "load_dxy_daily_closes",
    "load_dxy_availability",
]
