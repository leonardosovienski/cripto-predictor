"""Deterministic downstream-only context serving."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from GarimpoInvestimentos.external_intelligence.contracts import canonical, digest
from GarimpoInvestimentos.external_intelligence.store import ExternalIntelligenceStore


@dataclass(frozen=True)
class ExternalIntelligenceContext:
    canonical_asset_id: str
    decision_time: datetime
    dataset_snapshot_revision: str
    observations: tuple[dict[str, Any], ...]

    @property
    def context_hash(self) -> str:
        return digest(
            {
                "canonical_asset_id": self.canonical_asset_id,
                "decision_time": self.decision_time.isoformat(),
                "dataset_snapshot_revision": self.dataset_snapshot_revision,
                "observation_revision_ids": [row["revision_id"] for row in self.observations],
            }
        )

    def canonical_bytes(self) -> bytes:
        return canonical(
            {
                "canonical_asset_id": self.canonical_asset_id,
                "decision_time": self.decision_time.isoformat(),
                "dataset_snapshot_revision": self.dataset_snapshot_revision,
                "observations": self.observations,
                "context_hash": self.context_hash,
            }
        )


def context_at(
    store: ExternalIntelligenceStore,
    *,
    asset: str,
    decision_time: datetime,
    providers: tuple[str, ...] = (),
) -> ExternalIntelligenceContext:
    snapshot = store.materialize_snapshot(
        decision_time,
        canonical_asset_id=asset,
        providers=providers,
    )
    rows = tuple(
        store.observations_at(decision_time, canonical_asset_id=asset, providers=providers)
    )
    return ExternalIntelligenceContext(
        canonical_asset_id=asset,
        decision_time=decision_time,
        dataset_snapshot_revision=snapshot["dataset_snapshot_revision"],
        observations=rows,
    )
