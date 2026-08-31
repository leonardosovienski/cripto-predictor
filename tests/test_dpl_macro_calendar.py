"""Calendário macro (B1/H7): loader + dummy de janela de evento — 100% offline."""

import json
from datetime import UTC, date, datetime

import pytest

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.macro_calendar import (
    DEFAULT_CALENDAR_PATH,
    MacroEvent,
    load_macro_calendar,
    macro_event_signal_points,
    persist_macro_signals,
)

T0 = datetime(2026, 8, 1, tzinfo=UTC)


def _write_calendar(tmp_path, events: list[dict]):
    p = tmp_path / "calendar.json"
    p.write_text(
        json.dumps({"schema_version": "macro-calendar/1", "events": events}), encoding="utf-8"
    )
    return p


# --- calendário shipado -------------------------------------------------------


def test_shipped_calendar_has_complete_sourced_2026_dates():
    """Datas de release oficiais e versionadas; nenhuma inferência/interpolação."""
    assert DEFAULT_CALENDAR_PATH.exists()
    events = load_macro_calendar()
    assert len(events) == 33
    assert events == sorted(events, key=lambda e: e.event_date)  # cronológico, sem duplicata
    assert len({(e.event_type, e.event_date) for e in events}) == 33
    assert {e.event_date.year for e in events} == {2026}
    assert {kind: sum(e.event_type == kind for e in events) for kind in ("FOMC", "CPI", "PPI")} == {
        "FOMC": 8,
        "CPI": 12,
        "PPI": 13,
    }


# --- load_macro_calendar ------------------------------------------------------


def test_load_macro_calendar_parses_valid_events(tmp_path):
    p = _write_calendar(
        tmp_path,
        [{"event_type": "fomc", "date": "2026-08-05"}, {"event_type": "CPI", "date": "2026-08-12"}],
    )
    events = load_macro_calendar(p)
    assert events == [
        MacroEvent("FOMC", date(2026, 8, 5)),
        MacroEvent("CPI", date(2026, 8, 12)),
    ]


def test_load_macro_calendar_rejects_unknown_schema(tmp_path):
    p = tmp_path / "calendar.json"
    p.write_text(json.dumps({"schema_version": "other/1", "events": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_macro_calendar(p)


def test_load_macro_calendar_rejects_malformed_date(tmp_path):
    p = _write_calendar(tmp_path, [{"event_type": "FOMC", "date": "not-a-date"}])
    with pytest.raises(ValueError, match="malformado"):
        load_macro_calendar(p)


def test_load_macro_calendar_rejects_missing_event_type(tmp_path):
    p = tmp_path / "calendar.json"
    p.write_text(
        json.dumps({"schema_version": "macro-calendar/1", "events": [{"date": "2026-08-05"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="malformado"):
        load_macro_calendar(p)


# --- macro_event_signal_points ------------------------------------------------


def test_dummy_is_one_inside_window_and_zero_outside():
    events = [MacroEvent("FOMC", date(2026, 8, 10))]
    day_range = [date(2026, 8, d) for d in (8, 9, 10, 11, 12, 15)]
    ingested_at = datetime(2026, 8, 16, tzinfo=UTC)  # coleta roda depois de todo o range
    points = macro_event_signal_points(events, day_range, ingested_at=ingested_at, window_days=1)
    values = {p.timestamp.date(): p.value for p in points}
    assert values[date(2026, 8, 9)] == 1.0  # -1 dia
    assert values[date(2026, 8, 10)] == 1.0  # dia do evento
    assert values[date(2026, 8, 11)] == 1.0  # +1 dia
    assert values[date(2026, 8, 8)] == 0.0  # fora da janela
    assert values[date(2026, 8, 12)] == 0.0
    assert values[date(2026, 8, 15)] == 0.0


def test_one_signal_name_per_event_type_present():
    events = [MacroEvent("FOMC", date(2026, 8, 10)), MacroEvent("CPI", date(2026, 8, 13))]
    day_range = [date(2026, 8, 10)]
    ingested_at = datetime(2026, 8, 14, tzinfo=UTC)
    points = macro_event_signal_points(events, day_range, ingested_at=ingested_at, window_days=0)
    names = {p.name for p in points}
    assert names == {"macro:fomc_window", "macro:cpi_window"}


def test_no_events_produces_no_points():
    assert macro_event_signal_points([], [date(2026, 8, 10)], ingested_at=T0) == []


def test_published_at_equals_timestamp_conservatively():
    events = [MacroEvent("FOMC", date(2026, 8, 10))]
    ingested_at = datetime(2026, 8, 14, tzinfo=UTC)
    points = macro_event_signal_points(events, [date(2026, 8, 10)], ingested_at=ingested_at)
    assert all(p.published_at == p.timestamp for p in points)


def test_negative_window_days_rejected():
    with pytest.raises(ValueError, match="window_days"):
        macro_event_signal_points(
            [MacroEvent("FOMC", date(2026, 8, 10))],
            [date(2026, 8, 10)],
            ingested_at=datetime(2026, 8, 14, tzinfo=UTC),
            window_days=-1,
        )


# --- persist_macro_signals (Feature Store real, tmp) --------------------------


def test_persist_macro_signals_writes_and_reads_back(tmp_path):
    events = [MacroEvent("FOMC", date(2026, 8, 10))]
    day_range = [date(2026, 8, d) for d in (9, 10, 11)]
    ingested_at = datetime(2026, 8, 12, tzinfo=UTC)
    with FeatureStore(tmp_path / "fs.db") as store:
        n = persist_macro_signals(
            store, events=events, day_range=day_range, ingested_at=ingested_at
        )
        assert n == 3
        points = store.read_signals("macro_calendar", "macro:fomc_window")
        assert len(points) == 3
        assert all(p.value == 1.0 for p in points)  # todo o range está na janela de 1 dia
