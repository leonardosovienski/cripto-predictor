"""Daily, metric-isolated quality evaluation for COLLECTION_ONLY observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from statistics import median

from predictor_core.contracts import SignalPoint
from predictor_core.data.source_quality import (
    SourceQualityScorecard,
    SourceQualityState,
    SourceQualityThresholds,
    source_quality_scorecard,
)
from predictor_core.obs import emit_event

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.dpl.derivatives import SOURCE
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.governance import (
    ObservationMetric,
    ObservationPlan,
    load_observation_plan,
)

LOG = logging.getLogger(__name__)
DEFAULT_AUDIT_LOG = FEATURE_STORE_DB.parent / "observation_scorecards.jsonl"


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        return math.inf
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def _thresholds(metric: ObservationMetric) -> SourceQualityThresholds:
    return SourceQualityThresholds(
        minimum_coverage=metric.min_daily_coverage,
        maximum_median_freshness_seconds=metric.latency_p50_max_ms / 1000,
        maximum_p99_freshness_seconds=metric.latency_p99_max_ms / 1000,
        maximum_gap_count=metric.max_consecutive_gaps,
        maximum_gap_seconds=metric.max_consecutive_gaps * metric.cadence_seconds,
        maximum_revision_rate=0.01,
        minimum_availability=metric.min_daily_coverage,
        maximum_causality_failure_rate=0,
        maximum_integrity_failure_rate=0,
    )


def _append_audit(path: Path, payload: dict) -> bool:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            existing = json.loads(line)
            if existing["audit_key"] == payload["audit_key"]:
                if existing["payload_hash"] != digest:
                    raise ValueError("immutable JSONL scorecard exists with other content")
                return False
    record = {"audit_key": payload["audit_key"], "payload_hash": digest, "payload": payload}
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _instrument_scorecards(
    points: list[SignalPoint],
    *,
    instruments: tuple[str, ...],
    window_start: datetime,
    window_end: datetime,
    metric: ObservationMetric,
    successful_requests: int,
    total_requests: int,
) -> dict[str, SourceQualityScorecard]:
    limits = _thresholds(metric)
    return {
        instrument: source_quality_scorecard(
            [point for point in points if point.instrument == instrument],
            source=SOURCE,
            window_start=window_start,
            window_end=window_end,
            cadence_seconds=metric.cadence_seconds,
            thresholds=limits,
            successful_requests=successful_requests,
            total_requests=total_requests,
        )
        for instrument in instruments
    }


def evaluate_daily_metric(
    store: FeatureStore,
    *,
    plan: ObservationPlan,
    metric_name: str,
    day: date,
    audit_path: Path,
    instruments: tuple[str, ...] = ("BTCUSDT", "ETHUSDT"),
    successful_requests: int = 1,
    total_requests: int = 1,
    calculated_at: datetime | None = None,
) -> dict:
    metric = plan.metric(metric_name)
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    points = store.read_enriched_signals_window(
        source=SOURCE, metrics=metric.signal_metrics, window_start=start, window_end=end
    )
    # One OI representation is the logical cadence series; both remain audited for integrity.
    logical_metric = metric.signal_metrics[0]
    logical_points = [point for point in points if point.metric == logical_metric]
    cards = _instrument_scorecards(
        logical_points,
        instruments=instruments,
        window_start=start,
        window_end=end,
        metric=metric,
        successful_requests=successful_requests,
        total_requests=total_requests,
    )
    latencies = [
        (point.ingested_at - point.published_at).total_seconds() * 1000
        for point in logical_points
        if point.ingested_at is not None
    ]
    states = {card.state for card in cards.values()}
    state = (
        SourceQualityState.QUARANTINED
        if SourceQualityState.QUARANTINED in states
        else SourceQualityState.DEGRADED
        if SourceQualityState.DEGRADED in states
        else SourceQualityState.HEALTHY
    )
    violations = sorted({item for card in cards.values() for item in card.violations})
    p95 = _quantile(latencies, 0.95)
    if p95 > metric.latency_p95_max_ms:
        violations.append("freshness_p95")
        if state is SourceQualityState.HEALTHY:
            state = SourceQualityState.DEGRADED
    payload = {
        "schema_version": "collection-observation-scorecard/1",
        "plan_id": plan.plan_id,
        "source": SOURCE,
        "metric": metric.metric,
        "signal_metrics": list(metric.signal_metrics),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "calculated_at": (calculated_at or datetime.now(UTC)).isoformat(),
        "scientific_state": "COLLECTION_ONLY",
        "state": state.value,
        "violations": sorted(set(violations)),
        "observed_logical_points": len(logical_points),
        "observed_physical_points": len(points),
        "latency_ms": {
            "p50": median(latencies) if latencies else None,
            "p95": p95 if latencies else None,
            "p99": _quantile(latencies, 0.99) if latencies else None,
        },
        "divergence": 0.0,
        "per_instrument": _json_safe({name: card.to_dict() for name, card in cards.items()}),
    }
    payload["audit_key"] = f"{plan.plan_id}:{SOURCE}:{metric.metric}:{day.isoformat()}"
    store.write_observation_scorecard(payload, calculated_at=calculated_at or datetime.now(UTC))
    _append_audit(audit_path, payload)
    emit_event(
        "v3_cripto",
        "observation.daily_scorecard",
        metrics={
            "observed_points": len(logical_points),
            "latency_p95_ms": p95 if math.isfinite(p95) else 0.0,
        },
        metadata={
            "plan_id": plan.plan_id,
            "source": SOURCE,
            "metric": metric.metric,
            "state": state.value,
            "latency_observations": len(latencies),
            "scientific_state": "COLLECTION_ONLY",
        },
    )
    if state is not SourceQualityState.HEALTHY:
        emit_event(
            "v3_cripto",
            "observation.quality_alert",
            metrics={"violation_count": len(payload["violations"])},
            metadata={
                "plan_id": plan.plan_id,
                "source": SOURCE,
                "metric": metric.metric,
                "state": state.value,
                "violations": payload["violations"],
                "scientific_state": "COLLECTION_ONLY",
            },
        )
        LOG.warning("quality alert source=%s metric=%s state=%s", SOURCE, metric.metric, state)
    return payload


def run_daily(*, db_path: Path, day: date, audit_path: Path = DEFAULT_AUDIT_LOG) -> list[dict]:
    plan = load_observation_plan()
    with FeatureStore(db_path) as store:
        return [
            evaluate_daily_metric(
                store, plan=plan, metric_name=metric.metric, day=day, audit_path=audit_path
            )
            for metric in plan.metrics_under_observation
        ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate COLLECTION_ONLY daily scorecards")
    parser.add_argument(
        "--date", type=date.fromisoformat, default=(datetime.now(UTC) - timedelta(days=1)).date()
    )
    parser.add_argument("--db", type=Path, default=FEATURE_STORE_DB)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args(argv)
    run_daily(db_path=args.db, day=args.date, audit_path=args.audit_log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["evaluate_daily_metric", "run_daily"]
