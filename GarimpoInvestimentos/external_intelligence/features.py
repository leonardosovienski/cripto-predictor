"""First minimal causal transformation; no speculative feature registry."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from GarimpoInvestimentos.external_intelligence.contracts import FeatureDefinition
from GarimpoInvestimentos.external_intelligence.store import ExternalIntelligenceStore

EXPANDING_ZSCORE_V1 = FeatureDefinition(
    feature_id="external.metric.expanding_zscore",
    version=1,
    entity="crypto_asset",
    inputs=("provider/dataset/metric",),
    transform="expanding_zscore(ddof=0, causal=true)",
    code_hash="stdlib-statistics-v1",
)


@dataclass(frozen=True)
class DerivedFeatureValue:
    definition: FeatureDefinition
    value: float | None
    cutoff: datetime
    input_revision_ids: tuple[str, ...]


def expanding_zscore_at(
    store: ExternalIntelligenceStore,
    *,
    asset: str,
    provider: str,
    dataset: str,
    metric: str,
    cutoff: datetime,
) -> DerivedFeatureValue:
    rows = [
        row
        for row in store.observations_at(cutoff, canonical_asset_id=asset, providers=(provider,))
        if row["dataset"] == dataset
        and row["metric"] == metric
        and row["capability_state"] == "SUPPORTED"
        and isinstance(row["value"], (int, float))
    ]
    rows.sort(key=lambda row: (row["observed_at"], row["revision_id"]))
    values = [float(row["value"]) for row in rows]
    if len(values) < 2:
        value = None
    else:
        mean = math.fsum(values) / len(values)
        variance = math.fsum((item - mean) ** 2 for item in values) / len(values)
        value = 0.0 if variance == 0 else (values[-1] - mean) / math.sqrt(variance)
    return DerivedFeatureValue(
        definition=EXPANDING_ZSCORE_V1,
        value=value,
        cutoff=cutoff,
        input_revision_ids=tuple(row["revision_id"] for row in rows),
    )
