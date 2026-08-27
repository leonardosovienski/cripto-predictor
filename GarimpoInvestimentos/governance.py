"""Domain instances of predictor-core scientific governance contracts."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path

import yaml
from predictor_core.contracts import DataAcquisitionCharter
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]


def _artifact(directory: str, filename: str) -> Path:
    packaged = Path(__file__).resolve().parent / directory / filename
    return packaged if packaged.exists() else ROOT / directory / filename


FUNDING_OI_CHARTER = _artifact("charters", "funding_oi_v3.json")
BINANCE_SPOT_MICROSTRUCTURE_CHARTER = _artifact("charters", "binance_spot_microstructure_v1.json")
BINANCE_OBSERVATION_PLAN = _artifact("observation_plans", "binance_funding_oi_v1.yaml")
BINANCE_OBSERVATION_ACTIVATION = _artifact(
    "observation_plans/activations", "binance_funding_oi_v1_2026-08-09.json"
)
SCIENTIFIC_STATE_CHARTER = _artifact("charters", "scientific_state.json")


class HypothesisStatus(str, Enum):
    """Vocabulário fechado do ciclo de vida das hipóteses científicas.

    Não inclui ``ACTIVE`` de propósito: as ocorrências desse valor nos outros
    contratos pertencem a planos de observação, não a hipóteses. Um novo estado
    só deve entrar aqui junto com transições e invariantes explicitamente definidas.
    """

    REGISTERED_NOT_ACTIVATED = "REGISTERED_NOT_ACTIVATED"
    COLLECTION_ONLY_IMMATURE = "COLLECTION_ONLY_IMMATURE"
    CLOSED_NO_GO = "CLOSED_NO_GO"
    CLOSED_INSUFFICIENT_SAMPLE = "CLOSED_INSUFFICIENT_SAMPLE"
    CLOSED_INSUFFICIENT_DATA_DUE_TO_IRRECOVERABLE_DATA_LOSS = (
        "CLOSED_INSUFFICIENT_DATA_DUE_TO_IRRECOVERABLE_DATA_LOSS"
    )

    @property
    def is_closed(self) -> bool:
        return self.value.startswith("CLOSED_")


class ScientificStateCharter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str
    as_of_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    capital_authorized: bool
    leverage_authorized: bool
    llm_direct_trading_authorized: bool
    security_incident: str
    hypotheses: dict[str, HypothesisStatus]
    # Rótulo H<N> -> nome real da trial em trials.json. Existe porque "H1" sozinho
    # é ambíguo sem isso: auditoria de 2026-08-19 descobriu que "H1" vinha sendo
    # confundido com `v1-direct-gemini-h7` (o ancestral pré-protocolo da linha LLM,
    # que nunca teve rótulo formal) quando o H1 real, definido em
    # docs/HYPOTHESES.md, é `v3-hmm-funding-oi-fr90`. Mantém as duas fontes
    # (trials.json e este charter) conectadas de forma explícita e verificável.
    hypothesis_trials: dict[str, str]
    frozen_families: tuple[str, ...]
    notes: str

    @model_validator(mode="after")
    def fail_closed(self) -> ScientificStateCharter:
        if self.capital_authorized or self.leverage_authorized:
            raise ValueError("scientific state must not authorize capital or leverage")
        if self.llm_direct_trading_authorized:
            raise ValueError("LLM direct trading must remain forbidden")
        for hypothesis in ("H1", "H2", "H3", "H5"):
            if self.hypotheses.get(hypothesis) != "CLOSED_NO_GO":
                raise ValueError(f"{hypothesis} must remain CLOSED_NO_GO")
        if "funding_oi_hmm_v3" not in self.frozen_families:
            raise ValueError("funding/OI HMM V3 family must remain frozen")
        if set(self.hypothesis_trials) != set(self.hypotheses):
            raise ValueError(
                "hypothesis_trials deve ter exatamente as mesmas chaves H<N> que hypotheses "
                f"(diferenca: {set(self.hypothesis_trials) ^ set(self.hypotheses)})"
            )
        return self


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


class ActivationTaskEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task_name: str = Field(min_length=1)
    interval: str = Field(pattern=r"^PT[1-9][0-9]*M$")
    first_scheduled_run_id: str = Field(min_length=1)
    first_scheduled_run_status: str

    @model_validator(mode="after")
    def successful_run_required(self) -> ActivationTaskEvidence:
        if self.first_scheduled_run_status != "SUCCEEDED":
            raise ValueError("activation requires a successful scheduled collection run")
        return self


class ActivationWatchdogEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task_name: str = Field(min_length=1)
    interval: str = Field(pattern=r"^PT[1-9][0-9]*M$")
    verification_run_id: str = Field(min_length=1)
    verification_run_status: str
    healthy: bool
    violations: tuple[str, ...]

    @model_validator(mode="after")
    def healthy_run_required(self) -> ActivationWatchdogEvidence:
        if self.verification_run_status != "SUCCEEDED" or not self.healthy or self.violations:
            raise ValueError("activation requires a healthy watchdog run without violations")
        return self


class ObservationActivation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str
    activation_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    plan_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    activated_at: str
    activated_by: str = Field(min_length=1)
    activation_code_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    state: str
    scientific_state: str
    capital_authorized: bool
    collection: ActivationTaskEvidence
    watchdog: ActivationWatchdogEvidence
    activation_gate_status: str
    quality_baseline_status: str
    quality_baseline_note: str = Field(min_length=1)
    minimum_observation_days: int = Field(ge=1)
    desired_observation_days: int = Field(ge=1)
    activation_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def collection_only_activation(self) -> ObservationActivation:
        if self.state != "ACTIVE" or self.activation_gate_status != "PASSED":
            raise ValueError("observation activation gate must be ACTIVE and PASSED")
        if self.scientific_state != "COLLECTION_ONLY" or self.capital_authorized:
            raise ValueError("observation activation cannot authorize science or capital")
        if self.desired_observation_days < self.minimum_observation_days:
            raise ValueError("desired observation duration must not be shorter than minimum")
        return self


def _plan_checksum(value: dict) -> str:
    unsigned = dict(value)
    unsigned.pop("plan_checksum", None)
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _activation_checksum(value: dict) -> str:
    unsigned = dict(value)
    unsigned.pop("activation_checksum", None)
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


def load_observation_activation(
    path: Path | str = BINANCE_OBSERVATION_ACTIVATION,
) -> ObservationActivation:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid observation activation {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("observation activation root must be a JSON object")
    activation = ObservationActivation.model_validate(value)
    if activation.activation_checksum != _activation_checksum(value):
        raise ValueError(
            "observation activation checksum mismatch; activation records are immutable"
        )
    return activation


def load_acquisition_charter(path: Path | str = FUNDING_OI_CHARTER) -> DataAcquisitionCharter:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid acquisition charter {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("acquisition charter root must be a JSON object")
    return DataAcquisitionCharter.from_dict(value)


def load_microstructure_charter(
    path: Path | str = BINANCE_SPOT_MICROSTRUCTURE_CHARTER,
) -> DataAcquisitionCharter:
    return load_acquisition_charter(path)


def load_scientific_state(
    path: Path | str = SCIENTIFIC_STATE_CHARTER,
) -> ScientificStateCharter:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid scientific state charter {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("scientific state charter root must be a JSON object")
    return ScientificStateCharter.model_validate(value)


__all__ = [
    "BINANCE_OBSERVATION_PLAN",
    "BINANCE_OBSERVATION_ACTIVATION",
    "BINANCE_SPOT_MICROSTRUCTURE_CHARTER",
    "FUNDING_OI_CHARTER",
    "HypothesisStatus",
    "SCIENTIFIC_STATE_CHARTER",
    "ObservationPlan",
    "ObservationActivation",
    "ScientificStateCharter",
    "load_acquisition_charter",
    "load_observation_plan",
    "load_observation_activation",
    "load_microstructure_charter",
    "load_scientific_state",
]
