"""Operational outcomes, separate from scientific and economic conclusions."""

from collections import Counter


def summarize_outcomes(outcomes: dict[str, str]) -> dict:
    allowed = {
        "FAILED",
        "SOURCE_UNAVAILABLE",
        "NOT_COMPLETED",
        "SUCCEEDED",
        "CACHED",
        "FILTERED",
        "DEGRADED",
        "BUDGET_SKIPPED",
    }
    if set(outcomes.values()) - allowed:
        raise ValueError("unknown operational outcome")
    counts = Counter(outcomes.values())
    failures = sum(counts[state] for state in ("FAILED", "SOURCE_UNAVAILABLE", "NOT_COMPLETED"))
    completed = sum(counts[state] for state in ("SUCCEEDED", "CACHED", "FILTERED"))
    degraded = sum(counts[state] for state in ("DEGRADED", "BUDGET_SKIPPED"))
    status = (
        "FAILED"
        if not completed and failures
        else "PARTIAL"
        if failures or degraded
        else "SUCCEEDED"
    )
    if not outcomes:
        status = "FAILED"
    return {
        "schema_version": "crypto-run-outcomes/1",
        "run_status": status,
        "assets": dict(outcomes),
        "counts": dict(counts),
        "capital_permission": False,
    }
