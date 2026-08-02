from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from predictor_ops import OperationalState as OperationalStatus
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScientificStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    EXCLUDED_DEGRADED = "EXCLUDED_DEGRADED"
    NO_GO = "NO_GO"
    SHADOW = "SHADOW"
    COLLECTION_ONLY = "COLLECTION_ONLY"
    PENDING_SAMPLE = "PENDING_SAMPLE"
    CLOSED_BY_HUMAN_DECISION = "CLOSED_BY_HUMAN_DECISION"


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    prediction_id: str
    asset_id: str
    trial_id: str
    predicted_at: datetime
    data_as_of: datetime
    matures_at: datetime
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    _times = field_validator("predicted_at", "data_as_of", "matures_at")(_aware)


class PredictionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    prediction_id: str
    domain: str = "crypto"
    model_name: str
    model_version: str
    trial_id: str
    predicted_at: datetime
    data_as_of: datetime
    matures_at: datetime
    input_provenance: dict[str, Any]
    code_commit: str | None = None
    core_version: str
    degraded: bool = False
    degraded_reasons: tuple[str, ...] = ()
    scientific_status: ScientificStatus = ScientificStatus.ELIGIBLE
    score: float
    _times = field_validator("predicted_at", "data_as_of", "matures_at")(_aware)


class CollectionRequest(BaseModel):
    asset_ids: tuple[str, ...]
    scheduled_at: datetime
    idempotency_key: str
    _scheduled = field_validator("scheduled_at")(_aware)


class CollectionResult(BaseModel):
    status: OperationalStatus
    collected: int = 0
    degraded_reasons: tuple[str, ...] = ()


class SettlementRequest(BaseModel):
    prediction_id: str
    settled_at: datetime
    _settled = field_validator("settled_at")(_aware)


class SettlementResult(BaseModel):
    status: OperationalStatus
    prediction_id: str


class HealthStatus(BaseModel):
    status: OperationalStatus
    details: dict[str, str] = Field(default_factory=dict)


@runtime_checkable
class PredictorPlugin(Protocol):
    def predict(self, request: PredictionRequest) -> PredictionResult: ...


@runtime_checkable
class CollectorPlugin(Protocol):
    async def collect(self, request: CollectionRequest) -> CollectionResult: ...


@runtime_checkable
class SettlementPlugin(Protocol):
    def settle(self, request: SettlementRequest) -> SettlementResult: ...


@runtime_checkable
class HealthProvider(Protocol):
    def health(self) -> HealthStatus: ...
