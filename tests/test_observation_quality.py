from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from GarimpoInvestimentos.dpl.derivatives import funding_signal_points, oi_signal_points
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.governance import load_observation_plan
from GarimpoInvestimentos.observation_quality import evaluate_daily_metric
from GarimpoInvestimentos.observation_resilience import run_drills
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord
from GarimpoInvestimentos.v3.collectors.oi_collector import OIRecord


def test_daily_scorecards_are_metric_separated_and_idempotent(tmp_path):
    start = datetime(2026, 8, 1, tzinfo=UTC)
    funding = [
        FundingRecord(symbol, int((start + timedelta(hours=8 * n)).timestamp() * 1000), 0.0001, 1)
        for symbol in ("BTCUSDT", "ETHUSDT")
        for n in range(3)
    ]
    oi = [
        OIRecord(symbol, int((start + timedelta(hours=n)).timestamp() * 1000), 1, 100)
        for symbol in ("BTCUSDT", "ETHUSDT")
        for n in range(24)
    ]
    audit = tmp_path / "audit.jsonl"
    calculated = start + timedelta(days=2)
    with FeatureStore(tmp_path / "features.db") as store:
        ingested = start + timedelta(days=1, seconds=10)
        store.write_signals(funding_signal_points(funding, ingested_at=ingested))
        store.write_signals(oi_signal_points(oi, ingested_at=ingested))
        plan = load_observation_plan()
        funding_card = evaluate_daily_metric(
            store,
            plan=plan,
            metric_name="funding_rate",
            day=start.date(),
            audit_path=audit,
            calculated_at=calculated,
        )
        oi_card = evaluate_daily_metric(
            store,
            plan=plan,
            metric_name="open_interest",
            day=start.date(),
            audit_path=audit,
            calculated_at=calculated,
        )
        assert funding_card["metric"] == "funding_rate"
        assert oi_card["metric"] == "open_interest"
        assert oi_card["observed_logical_points"] == 48
        assert store._conn.execute("SELECT count(*) FROM observation_scorecards").fetchone()[0] == 2
        evaluate_daily_metric(
            store,
            plan=plan,
            metric_name="funding_rate",
            day=start.date(),
            audit_path=audit,
            calculated_at=calculated,
        )
        assert len(audit.read_text(encoding="utf-8").splitlines()) == 2


def test_scorecard_is_immutable_for_changed_rerun(tmp_path):
    plan = load_observation_plan()
    with FeatureStore(tmp_path / "features.db") as store:
        evaluate_daily_metric(
            store,
            plan=plan,
            metric_name="funding_rate",
            day=date(2026, 8, 1),
            audit_path=tmp_path / "audit.jsonl",
            calculated_at=datetime(2026, 8, 2, tzinfo=UTC),
        )
        with pytest.raises(ValueError, match="immutable"):
            evaluate_daily_metric(
                store,
                plan=plan,
                metric_name="funding_rate",
                day=date(2026, 8, 1),
                audit_path=tmp_path / "audit.jsonl",
                calculated_at=datetime(2026, 8, 3, tzinfo=UTC),
            )


def test_resilience_drills_pass_and_write_report(tmp_path):
    result = run_drills(tmp_path)
    assert result["passed"] is True
    assert set(result["tests"]) == {"disconnection", "duplicate_response", "revision"}


def test_conflicting_duplicates_inside_one_batch_are_first_valid_wins(tmp_path):
    start = datetime(2026, 8, 1, tzinfo=UTC)
    original = funding_signal_points(
        [FundingRecord("BTCUSDT", int(start.timestamp() * 1000), 0.0001, 1)],
        ingested_at=start + timedelta(seconds=10),
    )[0]
    conflicting = replace(original, value=0.0002, content_hash="f" * 64)
    with FeatureStore(tmp_path / "features.db") as store:
        assert store.write_signals([original, conflicting], require_enriched=True) == 1
        assert store.write_signals([original, conflicting], require_enriched=True) == 0
        persisted = store.read_signals(original.source, original.name)
    assert len(persisted) == 1
    assert persisted[0].content_hash == original.content_hash


def test_degraded_scorecard_emits_dedicated_alert_telemetry(tmp_path, monkeypatch):
    events = []
    monkeypatch.setattr(
        "GarimpoInvestimentos.observation_quality.emit_event",
        lambda domain, event, **payload: events.append((domain, event, payload)),
    )
    with FeatureStore(tmp_path / "features.db") as store:
        evaluate_daily_metric(
            store,
            plan=load_observation_plan(),
            metric_name="funding_rate",
            day=date(2026, 8, 1),
            audit_path=tmp_path / "audit.jsonl",
            calculated_at=datetime(2026, 8, 2, tzinfo=UTC),
        )
    assert [event for _, event, _ in events] == [
        "observation.daily_scorecard",
        "observation.quality_alert",
    ]
    assert events[-1][2]["metadata"]["scientific_state"] == "COLLECTION_ONLY"
