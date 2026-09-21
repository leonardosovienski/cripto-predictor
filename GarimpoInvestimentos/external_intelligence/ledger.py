"""Reference-only bridge into the existing causal opportunity ledger."""

from __future__ import annotations

from copy import deepcopy

from GarimpoInvestimentos.external_intelligence.context import ExternalIntelligenceContext


def attach_external_reference(record: dict, context: ExternalIntelligenceContext) -> dict:
    """Return a new research record; never mutate the canonical signal/ledger row."""
    result = deepcopy(record)
    result["external_evidence"] = {
        "external_dataset_snapshot_revision": context.dataset_snapshot_revision,
        "external_context_hash": context.context_hash,
        "cutoff": context.decision_time.isoformat(),
        "pit_composition": _counts(context, "pit_grade"),
        "rights_composition": {
            "cain_read_allowed": sum(
                bool(row["rights"]["cain_read"]) for row in context.observations
            ),
            "cain_generate_allowed": sum(
                bool(row["rights"]["cain_generate"]) for row in context.observations
            ),
        },
        "feature_definition_revisions": [],
    }
    return result


def _counts(context: ExternalIntelligenceContext, key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in context.observations:
        value = row[key]
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))
