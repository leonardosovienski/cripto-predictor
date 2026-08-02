from __future__ import annotations

from typing import Protocol

from GarimpoInvestimentos.contracts import PredictionResult


class PredictionRepository(Protocol):
    def save(self, prediction: PredictionResult, *, idempotency_key: str) -> None: ...
    def get(self, prediction_id: str) -> PredictionResult | None: ...


class FeatureRepository(Protocol):
    def latest(self, asset_id: str, *, feature_version: str = "v1") -> dict[str, float]: ...
    def health(self) -> str: ...


class ArtifactStore(Protocol):
    def put(self, name: str, payload: bytes, *, sha256: str) -> str: ...
