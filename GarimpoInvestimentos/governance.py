"""Domain instances of predictor-core scientific governance contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from predictor_core.contracts import DataAcquisitionCharter
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]


def _artifact(directory: str, filename: str) -> Path:
    packaged = Path(__file__).resolve().parent / directory / filename
    return packaged if packaged.exists() else ROOT / directory / filename


FUNDING_OI_CHARTER = _artifact("charters", "funding_oi_v3.json")
BINANCE_OBSERVATION_PLAN = _artifact("observation_plans", "binance_funding_oi_v1.yaml")


class DurationTargets(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    initial: int = Field(ge=1)
    desired: int = Field(ge=1)

    @model_validator(mode="after")
    def desired_not_shorter(self) -> DurationTargets:
        if self.desired < self.initial:
            raise ValueError("desired duration must be >= initial duration")
        return self


class ObservationMetric(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str = Field(min_length=1)
    signal_metrics: tuple[str, ...] = Field(min_length=1)
    cadence_seconds: int = Field(gt=0)
    min_duration_days: DurationTargets
    min_points: int = Field(gt=0)
    min_daily_coverage: float = Field(ge=0, le=1)
    min_weekly_coverage: float = Field(ge=0, le=1)
    max_consecutive_gaps: int = Field(ge=0)
    latency_p50_max_ms: int = Field(ge=0)
    latency_p95_max_ms: int = Field(ge=0)
    latency_p99_max_ms: int = Field(ge=0)
    max_allowed_degraded_events_per_month: int = Field(ge=0)
    max_unexplained_quarantines: int = Field(ge=0)
    scheduled_tests: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def ordered_latencies(self) -> ObservationMetric:
        if not (self.latency_p50_max_ms <= self.latency_p95_max_ms <= self.latency_p99_max_ms):
            raise ValueError("latency thresholds must be ordered p50 <= p95 <= p99")
        return self


class GlobalCriteria(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hash_stability_required: bool
    idempotency_required: bool
    cost_within_charter: bool
    human_approval_required_after_initial: bool
    human_approval_required_after_desired: bool


class ObservationPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str
    plan_id: str = Field(min_length=1)
    created_at: str
    target_source: str
    metrics_under_observation: tuple[ObservationMetric, ...] = Field(min_length=1)
    global_criteria: GlobalCriteria
    state: str
    scientific_state: str
    plan_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def fixed_governance(self) -> ObservationPlan:
        if self.state not in {"ACTIVE", "COMPLETED"}:
            raise ValueError("state must be ACTIVE or COMPLETED")
        if self.scientific_state != "COLLECTION_ONLY":
            raise ValueError("observation plans must remain COLLECTION_ONLY")
        names = [item.metric for item in self.metrics_under_observation]
        if len(names) != len(set(names)):
            raise ValueError("observation metrics must be unique")
        return self

    def metric(self, name: str) -> ObservationMetric:
        return next(item for item in self.metrics_under_observation if item.metric == name)


def _plan_checksum(value: dict) -> str:
    unsigned = dict(value)
    unsigned.pop("plan_checksum", None)
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_observation_plan(path: Path | str = BINANCE_OBSERVATION_PLAN) -> ObservationPlan:
    try:
        value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid observation plan {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("observation plan root must be a mapping")
    plan = ObservationPlan.model_validate(value)
    actual = _plan_checksum(value)
    if plan.plan_checksum != actual:
        raise ValueError("observation plan checksum mismatch; ACTIVE plans are immutable")
    return plan


def load_acquisition_charter(path: Path | str = FUNDING_OI_CHARTER) -> DataAcquisitionCharter:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid acquisition charter {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("acquisition charter root must be a JSON object")
    return DataAcquisitionCharter.from_dict(value)


__all__ = [
    "BINANCE_OBSERVATION_PLAN",
    "FUNDING_OI_CHARTER",
    "ObservationPlan",
    "load_acquisition_charter",
    "load_observation_plan",
]
