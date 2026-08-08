"""Domain wiring for predictor-core source quality scorecards."""

from __future__ import annotations

from datetime import UTC, datetime

from predictor_core.contracts import SignalPoint
from predictor_core.data.source_quality import (
    SourceQualityScorecard,
    SourceQualityThresholds,
    source_quality_scorecard,
)
from predictor_core.obs import emit_event

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.governance import load_acquisition_charter


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
    result = source_quality_scorecard(
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
