"""Small conditional-outcome engine for exploratory, causal snapshots."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ConditionalAnalysisResult:
    classification: str
    condition_id: str
    cohort_size: int
    baseline_size: int
    horizons: tuple[str, ...]
    conditional_means: dict[str, float | None]
    baseline_means: dict[str, float | None]
    status: str
    limitations: tuple[str, ...]


def analyze(
    rows: list[dict],
    *,
    condition_id: str,
    condition: Callable[[dict], bool],
    horizons: tuple[str, ...] = ("return_1d", "return_3d", "return_7d"),
    classification: str = "EXPLORATORY",
) -> ConditionalAnalysisResult:
    if classification not in {"EXPLORATORY", "CONFIRMATORY"}:
        raise ValueError("analysis classification must be explicit")
    baseline = [row for row in rows if row.get("pit_valid") is True]
    selected = [row for row in baseline if condition(row)]

    def mean(sample: list[dict], horizon: str) -> float | None:
        values = [
            float(row[horizon]) for row in sample if isinstance(row.get(horizon), (int, float))
        ]
        return math.fsum(values) / len(values) if values else None

    status = "HYPOTHESIS_GENERATING_ONLY" if classification == "EXPLORATORY" else "NOT_EVALUATED"
    return ConditionalAnalysisResult(
        classification=classification,
        condition_id=condition_id,
        cohort_size=len(selected),
        baseline_size=len(baseline),
        horizons=horizons,
        conditional_means={horizon: mean(selected, horizon) for horizon in horizons},
        baseline_means={horizon: mean(baseline, horizon) for horizon in horizons},
        status=status,
        limitations=(
            "No predictive or economic claim is authorized by retrospective results.",
            "Missing provider coverage is excluded, never coerced to zero.",
        ),
    )
