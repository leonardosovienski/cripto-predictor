"""Fail-closed weekly and maturity reporting for observation plans."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from statistics import fmean

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.dpl.derivatives import SOURCE
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.governance import (
    ObservationPlan,
    load_acquisition_charter,
    load_observation_plan,
)


def _write_once(path: Path, payload: dict) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != encoded:
        raise ValueError(f"immutable report already exists with other content: {path}")
    path.write_text(encoded, encoding="utf-8")


def _coverages(cards: list[dict]) -> list[float]:
    return [
        instrument["coverage"] for card in cards for instrument in card["per_instrument"].values()
    ]


def weekly_report(
    store: FeatureStore, *, plan: ObservationPlan, week_start: date, output_dir: Path
) -> dict:
    start = datetime.combine(week_start, time.min, tzinfo=UTC)
    end = start + timedelta(days=7)
    metrics = {}
    for config in plan.metrics_under_observation:
        cards = store.read_observation_scorecards(
            plan_id=plan.plan_id,
            source=SOURCE,
            metric=config.metric,
            window_start=start,
            window_end=end,
        )
        coverage = _coverages(cards)
        metrics[config.metric] = {
            "daily_scorecards": len(cards),
            "coverage_mean": fmean(coverage) if coverage else None,
            "coverage_min": min(coverage) if coverage else None,
            "coverage_max": max(coverage) if coverage else None,
            "degraded_events": sum(card["state"] == "DEGRADED" for card in cards),
            "quarantined_events": sum(card["state"] == "QUARANTINED" for card in cards),
            "weekly_coverage_passed": bool(coverage)
            and fmean(coverage) >= config.min_weekly_coverage,
        }
    payload = {
        "schema_version": "collection-observation-weekly/1",
        "plan_id": plan.plan_id,
        "scientific_state": "COLLECTION_ONLY",
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "metrics": metrics,
    }
    _write_once(output_dir / f"weekly-{week_start.isoformat()}.json", payload)
    return payload


def maturity_report(
    store: FeatureStore,
    *,
    plan: ObservationPlan,
    as_of: datetime,
    desired: bool,
    output_dir: Path,
    db_path: Path,
) -> dict:
    start = datetime.fromisoformat(plan.created_at.replace("Z", "+00:00"))
    duration_days = (as_of - start).total_seconds() / 86400
    charter = load_acquisition_charter()
    metrics = {}
    all_passed = True
    for config in plan.metrics_under_observation:
        cards = store.read_observation_scorecards(
            plan_id=plan.plan_id,
            source=SOURCE,
            metric=config.metric,
            window_start=start,
            window_end=as_of,
        )
        coverages = _coverages(cards)
        logical_points = sum(card["observed_logical_points"] for card in cards)
        required_days = (
            config.min_duration_days.desired if desired else config.min_duration_days.initial
        )
        criteria = {
            "duration": duration_days >= required_days,
            "minimum_points": logical_points >= config.min_points,
            "daily_coverage": bool(coverages) and min(coverages) >= config.min_daily_coverage,
            "degraded_limit": sum(card["state"] == "DEGRADED" for card in cards)
            <= config.max_allowed_degraded_events_per_month,
            "unexplained_quarantines": sum(card["state"] == "QUARANTINED" for card in cards)
            <= config.max_unexplained_quarantines,
            "scheduled_tests": False,  # promoted only by an reviewed attachment, never inferred
            "human_approval": False,  # approval is a separate signed governance record
        }
        passed = all(criteria.values())
        all_passed &= passed
        metrics[config.metric] = {
            "passed": passed,
            "criteria": criteria,
            "duration_days": duration_days,
            "logical_points": logical_points,
            "daily_scorecards": len(cards),
            "coverage": {
                "mean": fmean(coverages) if coverages else None,
                "min": min(coverages) if coverages else None,
                "max": max(coverages) if coverages else None,
            },
            "degraded_events": sum(card["state"] == "DEGRADED" for card in cards),
            "quarantined_events": sum(card["state"] == "QUARANTINED" for card in cards),
        }
    storage_bytes = db_path.stat().st_size if db_path.exists() else 0
    storage_budget = float(charter.resource_budget.storage_gb_month) * 1_000_000_000
    resources = {
        "storage_bytes": storage_bytes,
        "storage_within_charter": storage_bytes <= storage_budget,
        "traffic_mb": None,
        "cost_within_charter": False,
        "reason": "traffic measurement unavailable; criterion fails closed",
    }
    all_passed &= resources["cost_within_charter"]
    payload = {
        "schema_version": "collection-observation-maturity/1",
        "plan_id": plan.plan_id,
        "scientific_state": "COLLECTION_ONLY",
        "stage": "desired" if desired else "initial",
        "as_of": as_of.isoformat(),
        "passed": all_passed,
        "capital_authorized": False,
        "metrics": metrics,
        "resources": resources,
        "decision": "AWAITING_EVIDENCE_OR_APPROVAL" if not all_passed else "READY_FOR_HUMAN_REVIEW",
    }
    _write_once(output_dir / f"maturity-{'90d' if desired else '30d'}-{as_of.date()}.json", payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate observation reports")
    parser.add_argument("kind", choices=("weekly", "maturity-initial", "maturity-final"))
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(UTC).date())
    parser.add_argument("--db", type=Path, default=FEATURE_STORE_DB)
    parser.add_argument("--output-dir", type=Path, default=Path("observation_reports"))
    args = parser.parse_args(argv)
    plan = load_observation_plan()
    with FeatureStore(args.db) as store:
        if args.kind == "weekly":
            weekly_report(store, plan=plan, week_start=args.date, output_dir=args.output_dir)
        else:
            maturity_report(
                store,
                plan=plan,
                as_of=datetime.combine(args.date, time.max, tzinfo=UTC),
                desired=args.kind == "maturity-final",
                output_dir=args.output_dir,
                db_path=args.db,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["maturity_report", "weekly_report"]
