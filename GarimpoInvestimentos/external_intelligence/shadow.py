"""Downstream-only association between immutable canonical signals and evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from GarimpoInvestimentos.external_intelligence.context import ExternalIntelligenceContext


@dataclass(frozen=True)
class ShadowOpportunityContext:
    canonical_signal: Any
    external_context: ExternalIntelligenceContext
    decision_time: datetime
    external_dataset_snapshot_revision: str


def attach_shadow_context(
    canonical_signal: Any, external_context: ExternalIntelligenceContext, decision_time: datetime
) -> ShadowOpportunityContext:
    return ShadowOpportunityContext(
        canonical_signal=canonical_signal,
        external_context=external_context,
        decision_time=decision_time,
        external_dataset_snapshot_revision=external_context.dataset_snapshot_revision,
    )
