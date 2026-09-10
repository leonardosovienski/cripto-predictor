from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from scripts import carry_forward_registration as registration
from scripts.audit_market_calendar import DAY_MS, classify
from scripts.research_io import Ledger, encoded, sha, strict_json


def example():
    return (
        {
            "missing_days_total": 2,
            "results": [
                {"symbol": "ABCUSDT", "start_ms": DAY_MS, "end_ms": 2 * DAY_MS, "expected_days": 2}
            ],
        },
        {
            "events": [
                {
                    "symbol": "ABCUSDT",
                    "halt_utc": "1970-01-01T04:00:00+00:00",
                    "resume_utc": "1970-01-03T12:00:00+00:00",
                    "sources": [{"url": "https://example.com/announcement"}],
                }
            ]
        },
    )


def test_calendar_does_not_explain_a_day_that_contains_trading():
    gaps, events = example()
    result = classify(gaps, events)
    assert result["explained_nontrading_days"] == 1
    assert result["unexplained_days"] == 1
    assert result["candles_created"] == 0
    assert result["historical_signal_eligible"] is False
    assert result["results"][0]["explained_nontrading_days"] == ["1970-01-02"]


def test_calendar_keeps_unknown_symbols_unexplained():
    gaps, events = example()
    events["events"][0]["symbol"] = "OTHER"
    assert classify(gaps, events)["unexplained_days"] == 2


@pytest.mark.parametrize("fault", ["overlap", "off_grid", "count", "naive", "source"])
def test_calendar_rejects_ambiguous_inputs(fault):
    gaps, events = example()
    if fault == "overlap":
        gaps["results"] *= 2
    elif fault == "off_grid":
        gaps["results"][0]["start_ms"] += 1
    elif fault == "count":
        gaps["missing_days_total"] = 3
    elif fault == "naive":
        events["events"][0]["halt_utc"] = "1970-01-01T04:00:00"
    else:
        events["events"][0]["sources"] = []
    with pytest.raises(ValueError):
        classify(gaps, events)


@pytest.fixture
def original(monkeypatch):
    protocol = strict_json((registration.observer.EVIDENCE / "protocol.json").read_bytes())
    monkeypatch.setattr(
        registration.observer, "verify", lambda: (deepcopy(protocol), "original-freeze")
    )
    return protocol


START = datetime(2030, 1, 2, tzinfo=UTC)
CLOCK = START - timedelta(days=2)


def test_registration_preserves_rules_and_uses_separate_empty_directory(tmp_path, original):
    bundle = tmp_path / "new"
    registration.prepare(bundle, START, clock=lambda: CLOCK)
    protocol, _ = registration.load(bundle)
    assert protocol["costs"] == original["costs"]
    assert protocol["capital_usdt"] == original["capital_usdt"]
    assert registration.timestamp(protocol["end"]) - START == timedelta(days=84)
    result = registration.inspect(bundle, clock=lambda: CLOCK)
    assert result["phase"] == "WAITING"
    assert result["entry_observed"] is False
    assert not (bundle / "observations").exists()
    with pytest.raises(FileExistsError):
        registration.prepare(bundle, START, clock=lambda: CLOCK)


def test_registration_refuses_past_or_imminent_entry(tmp_path, original):
    for start in (CLOCK - timedelta(days=1), CLOCK, CLOCK + timedelta(hours=12)):
        with pytest.raises(ValueError):
            registration.prepare(tmp_path / "new", start, clock=lambda: CLOCK)
    assert not (tmp_path / "new").exists()


def test_registration_cannot_rewrite_costs_even_with_rehashed_protocol(tmp_path, original):
    registration.prepare(tmp_path / "new", START, clock=lambda: CLOCK)
    bundle = tmp_path / "new"
    path = bundle / "protocol.json"
    data = strict_json(path.read_bytes())
    data["costs"]["base"]["spot_bps"] = 0
    path.write_bytes(encoded(data))
    manifest_path = bundle / "registration.json"
    manifest = strict_json(manifest_path.read_bytes())
    manifest["protocol_sha256"] = sha(path.read_bytes())
    manifest_path.write_bytes(encoded(manifest))
    with pytest.raises(ValueError, match="Economic rules"):
        registration.load(bundle)


def test_unobserved_new_window_remains_missed(tmp_path, original):
    bundle = tmp_path / "new"
    registration.prepare(bundle, START, clock=lambda: CLOCK)
    result = registration.inspect(bundle, clock=lambda: START + timedelta(hours=2))
    assert result["phase"] == "MISSED_ENTRY"
    assert result["entry_observed"] is False
    assert not (bundle / "observations").exists()


def test_changed_registration_refuses_observation_before_network(tmp_path, original, monkeypatch):
    bundle = tmp_path / "new"
    registration.prepare(bundle, START, clock=lambda: CLOCK)
    path = bundle / "registration.json"
    data = strict_json(path.read_bytes())
    data["launcher_sha256"] = "changed"
    path.write_bytes(encoded(data))
    monkeypatch.setattr(registration.observer, "PublicSource", lambda *_: pytest.fail("network"))
    with pytest.raises(ValueError, match="freeze"):
        registration.observe(bundle, "tick")


@pytest.mark.parametrize("fault", ["source", "future_ledger"])
def test_readonly_status_does_not_certify_corrupt_or_future_observations(tmp_path, original, fault):
    bundle = tmp_path / "new"
    registration.prepare(bundle, START, clock=lambda: CLOCK)
    _, digest = registration.load(bundle)
    data = bundle / "observations"
    data.mkdir()
    payload = {"freeze_sha256": digest}
    at = CLOCK
    if fault == "source":
        payload["sources"] = [{"id": "not-a-valid-source"}]
    else:
        at = CLOCK + timedelta(hours=1)
    ledger = Ledger(data / "ledger.jsonl")
    ledger.append("PREFLIGHT", "diagnostic", payload, at.isoformat())
    with pytest.raises(ValueError):
        registration.inspect(bundle, clock=lambda: CLOCK)
