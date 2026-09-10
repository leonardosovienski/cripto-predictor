"""Domain wiring for predictor-core source quality scorecards."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import UTC, datetime
from statistics import median

from predictor_core.contracts import SignalPoint
from predictor_core.data.source_quality import (
    SourceQualityScorecard,
    SourceQualityState,
    SourceQualityThresholds,
    source_quality_scorecard,
)
from predictor_core.obs import emit_event

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.governance import load_acquisition_charter


def audited_source_quality_scorecard(points, **kwargs) -> SourceQualityScorecard:
    """Audit one cadence series; observed receipt must not imply zero source age."""
    cadence = kwargs["cadence_seconds"]
    start, end = kwargs["window_start"], kwargs["window_end"]
    if not math.isfinite(cadence) or cadence <= 0:
        raise ValueError("cadence_seconds must be positive and finite")
    success, total = kwargs["successful_requests"], kwargs["total_requests"]
    if (
        any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (success, total))
        or success > total
    ):
        raise ValueError("invalid request counts")
    selected = [
        p
        for p in points
        if p.source == kwargs["source"] and p.event_at is not None and start <= p.event_at < end
    ]
    if len({(p.instrument, p.metric) for p in selected}) > 1:
        raise ValueError("scorecard requires one instrument and metric")
    result = source_quality_scorecard(points, **kwargs)
    limits = kwargs["thresholds"]
    violations = set(result.violations)
    # Multiple observations in a slot cannot compensate for a missing slot.
    bins = {int((p.event_at - start).total_seconds() // cadence) for p in selected}
    coverage = min(1.0, len(bins) / result.expected_points)
    if coverage < limits.minimum_coverage:
        violations.add("coverage")
    latencies = []
    for point in selected:
        reference = (
            point.event_at if "available_at_receipt" in point.quality_flags else point.published_at
        )
        if point.ingested_at is not None:
            latencies.append((point.ingested_at - reference).total_seconds())
    freshness_median = median(latencies) if latencies else math.inf
    freshness_p99 = (
        sorted(latencies)[math.ceil(0.99 * len(latencies)) - 1] if latencies else math.inf
    )
    if freshness_median > limits.maximum_median_freshness_seconds:
        violations.add("freshness_median")
    if freshness_p99 > limits.maximum_p99_freshness_seconds:
        violations.add("freshness_p99")
    state = result.state
    if any(v < 0 for v in latencies):
        violations.add("negative_latency")
        state = SourceQualityState.QUARANTINED
    if violations and state is SourceQualityState.HEALTHY:
        state = SourceQualityState.DEGRADED
    return replace(
        result,
        coverage=coverage,
        freshness_median_seconds=freshness_median,
        freshness_p99_seconds=freshness_p99,
        violations=tuple(sorted(violations)),
        state=state,
    )


def calculate_and_persist_scorecard(
    store: FeatureStore,
    points: list[SignalPoint],
    *,
    source: str,
    window_start: datetime,
    window_end: datetime,
    cadence_seconds: float,
    successful_requests: int,
    total_requests: int,
    calculated_at: datetime | None = None,
) -> SourceQualityScorecard:
    if not points:
        raise ValueError("cannot score an empty source series")
    charter = load_acquisition_charter()
    thresholds = SourceQualityThresholds(**dict(charter.quality_thresholds))
    result = audited_source_quality_scorecard(
        points,
        source=source,
        window_start=window_start,
        window_end=window_end,
        cadence_seconds=cadence_seconds,
        thresholds=thresholds,
        successful_requests=successful_requests,
        total_requests=total_requests,
    )
    payload = result.to_dict()
    stamp = calculated_at or datetime.now(UTC)
    store.write_quality_scorecard(payload, calculated_at=stamp)
    emit_event(
        "v3_cripto",
        "source.quality_scorecard",
        metrics={
            "coverage": result.coverage,
            "freshness_p99_seconds": result.freshness_p99_seconds,
            "availability": result.availability,
            "integrity_failure_rate": result.integrity_failure_rate,
        },
        metadata={
            "source": source,
            "state": result.state.value,
            "violations": list(result.violations),
            "scientific_state": "COLLECTION_ONLY",
        },
    )
    return result


__all__ = ["calculate_and_persist_scorecard"]
