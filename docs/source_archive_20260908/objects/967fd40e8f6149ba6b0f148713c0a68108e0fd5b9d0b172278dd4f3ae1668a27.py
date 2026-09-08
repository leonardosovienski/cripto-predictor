"""Isolated resilience drills; never touches the production Feature Store."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from GarimpoInvestimentos.dpl.derivatives import SOURCE, funding_signal_points
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.governance import load_observation_plan
from GarimpoInvestimentos.observation_quality import evaluate_daily_metric
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord


def run_drills(output_dir: Path) -> dict:
    """Run deterministic disconnection, duplicate and revision drills in a temp DB."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = load_observation_plan()
    day = datetime(2026, 8, 1, tzinfo=UTC)
    times = [day + timedelta(hours=8 * index) for index in range(3)]
    records = [
        FundingRecord("BTCUSDT", int(stamp.timestamp() * 1000), 0.0001 + index / 1e6, 100000)
        for index, stamp in enumerate(times)
        if index != 1  # controlled 8-hour disconnection
    ]
    report: dict = {
        "schema_version": "collection-resilience-report/1",
        "plan_id": plan.plan_id,
        "scientific_state": "COLLECTION_ONLY",
        "executed_at": datetime.now(UTC).isoformat(),
        "tests": {},
    }
    with tempfile.TemporaryDirectory(prefix="cripto-observation-drill-") as temporary:
        db = Path(temporary) / "drill.db"
        audit = Path(temporary) / "audit.jsonl"
        with FeatureStore(db) as store:
            points = funding_signal_points(records, ingested_at=day + timedelta(days=1))
            store.write_signals(points, require_enriched=True)
            score = evaluate_daily_metric(
                store,
                plan=plan,
                metric_name="funding_rate",
                day=day.date(),
                audit_path=audit,
                instruments=("BTCUSDT",),
                calculated_at=day + timedelta(days=2),
            )
            report["tests"]["disconnection"] = {
                "passed": (
                    score["state"] == "DEGRADED"
                    and score["per_instrument"]["BTCUSDT"]["gap_count"] == 1
                ),
                "state": score["state"],
                "violations": score["violations"],
                "gap_count": score["per_instrument"]["BTCUSDT"]["gap_count"],
            }

            original = points[0]
            conflicting = replace(original, value=0.123, content_hash="f" * 64)
            rejected = False
            try:
                store.write_signals([conflicting], require_enriched=True)
            except ValueError:
                rejected = True
            persisted = store.read_signals(SOURCE, original.name)
            report["tests"]["duplicate_response"] = {
                "passed": rejected and len(persisted) == 2,
                "conflict_rejected": rejected,
            }

        revision_db = Path(temporary) / "revision.db"
        with FeatureStore(revision_db) as revision_store:
            revision_store.write_signals(points, require_enriched=True)
            assert original.vintage is not None
            assert original.ingested_at is not None
            revised = replace(
                original,
                value=original.value + 0.00001,
                vintage=original.vintage + timedelta(minutes=5),
                ingested_at=original.ingested_at + timedelta(minutes=5),
                content_hash="e" * 64,
            )
            revision_store.write_signals([revised], require_enriched=True)
            revised_score = evaluate_daily_metric(
                revision_store,
                plan=plan,
                metric_name="funding_rate",
                day=day.date(),
                audit_path=Path(temporary) / "revision.jsonl",
                instruments=("BTCUSDT",),
                calculated_at=day + timedelta(days=2, seconds=1),
            )
            revision_count = revised_score["per_instrument"]["BTCUSDT"]["revision_count"]
            report["tests"]["revision"] = {
                "passed": revision_count == 1,
                "revision_count": revision_count,
            }
    report["passed"] = all(item["passed"] for item in report["tests"].values())
    target = output_dir / f"{plan.plan_id}-resilience.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run isolated COLLECTION_ONLY resilience drills")
    parser.add_argument("--output-dir", type=Path, default=Path("observation_reports"))
    args = parser.parse_args(argv)
    return 0 if run_drills(args.output_dir)["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run_drills"]
