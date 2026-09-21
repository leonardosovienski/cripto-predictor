"""Versioned CRIPTO-owned contracts for external research evidence.

These contracts deliberately remain outside predictor-core until a second real
domain proves that the semantics are shared. They never authorize capital.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class PITGrade(StrEnum):
    PROVIDER_PIT = "PROVIDER_PIT"
    RECEIPT_PIT = "RECEIPT_PIT"
    RECONSTRUCTED = "RECONSTRUCTED"


class CapabilityState(StrEnum):
    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    RESTRICTED = "RESTRICTED"
    DEGRADED = "DEGRADED"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class FailureKind(StrEnum):
    UNSUPPORTED = "unsupported"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RESTRICTION = "restriction"
    RATE_LIMIT = "rate_limit"
    CREDIT_EXHAUSTED = "credit_exhausted"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    BAD_RESPONSE = "bad_response"
    SCHEMA_ERROR = "schema_error"
    PARTIAL_RESPONSE = "partial_response"
    UNKNOWN = "unknown"


def utc(value: datetime, *, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(UTC)


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value)
    return hashlib.sha256(raw).hexdigest()


def _json_value(value: Any) -> Any:
    canonical(value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite values are forbidden")
    return value


@dataclass(frozen=True)
class RightsPolicy:
    """Internal policy evidence, not a universal legal conclusion."""

    policy_version: str
    local_research: bool = False
    local_raw_storage: bool = False
    derived_export: bool = False
    raw_export: bool = False
    cain_read: bool = False
    cain_generate: bool = False
    persistent_memory: bool = False
    redistribution: bool = False
    evidence_ref: str | None = None
    evidence_hash: str | None = None
    checked_at: datetime | None = None
    status: str = "UNKNOWN"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("rights policy version is required")
        if self.checked_at is not None:
            object.__setattr__(self, "checked_at", utc(self.checked_at, label="rights_checked_at"))
        if self.evidence_hash is not None and (
            len(self.evidence_hash) != 64
            or any(char not in "0123456789abcdef" for char in self.evidence_hash)
        ):
            raise ValueError("rights evidence hash must be lowercase SHA-256")

    @classmethod
    def unknown(cls, version: str = "external-rights/1") -> RightsPolicy:
        return cls(policy_version=version)

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["checked_at"] = self.checked_at.isoformat() if self.checked_at else None
        return result


@dataclass(frozen=True)
class AssetMapping:
    provider: str
    canonical_asset_id: str
    provider_asset_id: str
    mapping_version: str
    chain: str | None = None
    contract: str | None = None
    mapping_type: str = "EXACT"
    status: CapabilityState = CapabilityState.SUPPORTED

    def __post_init__(self) -> None:
        if not self.canonical_asset_id.startswith("crypto:"):
            raise ValueError("canonical crypto asset identity must start with crypto:")
        if self.canonical_asset_id == "crypto:btc" and self.provider_asset_id.lower() == "wbtc":
            raise ValueError("BTC and WBTC cannot be mapped as exact equivalents")

    @property
    def mapping_id(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class ExternalObservationV1:
    provider: str
    dataset: str
    canonical_asset_id: str
    provider_asset_id: str
    metric: str
    metric_version: str
    value: Any
    observed_at: datetime
    received_at: datetime
    pit_grade: PITGrade
    rights: RightsPolicy
    collection_run_id: str
    collection_run_revision: str
    provider_available_at: datetime | None = None
    unit: str | None = None
    dimensions: dict[str, Any] = field(default_factory=dict)
    payload_reference: str | None = None
    payload_hash: str | None = None
    collector_version: str = "external-intelligence/1"
    capability_state: CapabilityState = CapabilityState.SUPPORTED
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "ExternalObservationV1"

    def __post_init__(self) -> None:
        if self.schema_version != "ExternalObservationV1":
            raise ValueError("unsupported observation contract")
        if not self.provider or not self.dataset or not self.metric or not self.metric_version:
            raise ValueError("provider, dataset, metric and metric_version are required")
        if not self.canonical_asset_id.startswith("crypto:"):
            raise ValueError("explicit canonical asset identity is required")
        object.__setattr__(self, "observed_at", utc(self.observed_at, label="observed_at"))
        object.__setattr__(self, "received_at", utc(self.received_at, label="received_at"))
        if self.provider_available_at is not None:
            object.__setattr__(
                self,
                "provider_available_at",
                utc(self.provider_available_at, label="provider_available_at"),
            )
        if self.pit_grade is PITGrade.PROVIDER_PIT and self.provider_available_at is None:
            raise ValueError("PROVIDER_PIT requires auditable provider_available_at")
        if self.provider_available_at and self.provider_available_at > self.received_at:
            raise ValueError("provider availability cannot be after receipt")
        if self.capability_state is CapabilityState.SUPPORTED and self.value is None:
            raise ValueError("supported observation cannot silently encode missing as null")
        if self.capability_state is not CapabilityState.SUPPORTED and self.value is not None:
            raise ValueError("unavailable capability state cannot be encoded as a value")
        _json_value(self.value)
        _json_value(self.dimensions)
        _json_value(self.metadata)

    @property
    def effective_available_at(self) -> datetime:
        if self.pit_grade is PITGrade.PROVIDER_PIT:
            assert self.provider_available_at is not None
            return self.provider_available_at
        return self.received_at

    @property
    def observation_id(self) -> str:
        return digest(
            {
                "provider": self.provider,
                "dataset": self.dataset,
                "canonical_asset_id": self.canonical_asset_id,
                "provider_asset_id": self.provider_asset_id,
                "metric": self.metric,
                "metric_version": self.metric_version,
                "observed_at": self.observed_at.isoformat(),
                "dimensions": self.dimensions,
            }
        )

    @property
    def content_hash(self) -> str:
        return digest({"value": self.value, "payload_hash": self.payload_hash})

    @property
    def revision_id(self) -> str:
        return digest(
            {
                "observation_id": self.observation_id,
                "content_hash": self.content_hash,
                "provider_available_at": self.provider_available_at.isoformat()
                if self.provider_available_at
                else None,
                "pit_grade": self.pit_grade,
                "capability_state": self.capability_state,
                "collector_version": self.collector_version,
                "rights": self.rights.as_dict(),
                "metadata": self.metadata,
            }
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "pit_grade": self.pit_grade.value,
            "capability_state": self.capability_state.value,
            "rights": self.rights.as_dict(),
            "observed_at": self.observed_at.isoformat(),
            "provider_available_at": self.provider_available_at.isoformat()
            if self.provider_available_at
            else None,
            "received_at": self.received_at.isoformat(),
            "effective_available_at": self.effective_available_at.isoformat(),
            "observation_id": self.observation_id,
            "revision_id": self.revision_id,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class CapabilitySnapshot:
    provider: str
    scope: dict[str, str | None]
    state: CapabilityState
    received_at: datetime
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "received_at", utc(self.received_at, label="received_at"))
        _json_value(self.scope)
        _json_value(self.evidence)

    @property
    def snapshot_id(self) -> str:
        return digest(
            {
                "provider": self.provider,
                "scope": self.scope,
                "state": self.state,
                "received_at": self.received_at.isoformat(),
                "evidence": self.evidence,
            }
        )


@dataclass(frozen=True)
class ExternalResearchDocumentV1:
    provider: str
    source: str
    provider_document_id: str
    received_at: datetime
    content_hash: str
    rights: RightsPolicy
    published_at: datetime | None = None
    payload_reference: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "received_at", utc(self.received_at, label="received_at"))
        if self.published_at is not None:
            object.__setattr__(self, "published_at", utc(self.published_at, label="published_at"))
        if len(self.content_hash) != 64 or any(
            char not in "0123456789abcdef" for char in self.content_hash
        ):
            raise ValueError("document content hash must be lowercase SHA-256")
        _json_value(self.provenance)

    @property
    def document_id(self) -> str:
        return digest(
            {
                "provider": self.provider,
                "source": self.source,
                "provider_document_id": self.provider_document_id,
            }
        )

    @property
    def revision_id(self) -> str:
        return digest(
            {
                "document_id": self.document_id,
                "content_hash": self.content_hash,
                "published_at": self.published_at.isoformat() if self.published_at else None,
                "provenance": self.provenance,
            }
        )


@dataclass(frozen=True)
class CollectionRun:
    collection_run_id: str
    provider: str
    collector_version: str
    started_at: datetime
    finished_at: datetime
    status: str
    requests: int
    observation_count: int
    document_count: int = 0
    errors: tuple[dict[str, Any], ...] = ()
    retries: int = 0
    capability_snapshot_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at", utc(self.started_at, label="started_at"))
        object.__setattr__(self, "finished_at", utc(self.finished_at, label="finished_at"))
        if self.finished_at < self.started_at:
            raise ValueError("collection run finished before it started")
        if min(self.requests, self.observation_count, self.document_count, self.retries) < 0:
            raise ValueError("collection counts cannot be negative")

    @property
    def manifest(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
        }

    @property
    def collection_run_revision(self) -> str:
        return digest(self.manifest)


@dataclass(frozen=True)
class FeatureDefinition:
    feature_id: str
    version: int
    entity: str
    inputs: tuple[str, ...]
    transform: str
    availability_policy: str = "effective_available_at"
    missing_policy: str = "preserve_missing"
    code_hash: str = ""

    @property
    def revision(self) -> str:
        return digest(asdict(self))
