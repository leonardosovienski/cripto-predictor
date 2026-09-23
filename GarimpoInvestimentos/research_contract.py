"""CRIPTO research contract: request/result schemas owned by the crypto domain.

No envelope, transport, signing or CAIN concepts live here (qualification stage A).
Requests arrive as local files (requester trust LOCAL_FILE_ONLY). Every identifier that
leaves the domain is qualified with the ``crypto:`` prefix.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any

DOMAIN_PREFIX = "crypto"
REQUEST_SCHEMA = "crypto-research-request/1"
RESULT_SCHEMA = "crypto-research-result/1"
OUTCOME_SCHEMA = "crypto-research-outcome/1"
REQUESTER_TRUST = "LOCAL_FILE_ONLY"

REQUEST_TYPES = {"BACKTEST_EXISTING_HYPOTHESIS"}
REFERENCE_KINDS = ("protocol", "dataset", "baseline", "cost_model", "evidence")
PRIORITIES = ("LOW", "NORMAL", "HIGH")

# Closed enum of terminal research results (C24.1 result_states).
RESULT_STATES = (
    "WATCH_NO_CAPITAL",
    "NO_EDGE",
    "INCONCLUSIVE",
    "REFUTED",
    "CLOSED_INSUFFICIENT_SAMPLE",
    "INCONCLUSIVE_DATA_QUALITY",
    "FAILED_OPERATIONAL",
)
# Non-terminal or refusal outcomes reported for one submission (never a stored result).
OUTCOME_STATUSES = (
    "RESULT",
    "DUPLICATE",
    "REJECTED",
    "CONFLICT",
    "NOT_READY",
    "OPS_FAILED_RETRYABLE",
    "TEMPORAL_INTEGRITY_VIOLATION",
    "RECONCILIATION_REQUIRED",
)
EXIT_CODES = {
    "RESULT": 0,
    "DUPLICATE": 0,
    "REJECTED": 2,
    "CONFLICT": 2,
    "NOT_READY": 3,
    "OPS_FAILED_RETRYABLE": 3,
    "TEMPORAL_INTEGRITY_VIOLATION": 4,
    "RECONCILIATION_REQUIRED": 5,
}
OPERATIONAL_STATES = ("SUCCEEDED", "FAILED", "TIMEOUT", "SKIPPED_ALREADY_SUCCEEDED")
SCIENTIFIC_STATES = ("SUPPORTED", "REFUTED", "INCONCLUSIVE", "INSUFFICIENT_SAMPLE", "NOT_EVALUATED")
ECONOMIC_STATES = ("WATCH", "NO_EDGE", "NOT_EVALUATED")

_ID = re.compile(r"^crypto:[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")

PARAMETER_BOUNDS = {
    "symbol": str,
    "horizon_days": (1, 90),
    "max_observations": (4, 5000),
    "fee_bps": (0, 1000),
    "slippage_bps": (0, 1000),
}


class ContractError(ValueError):
    """A request or result does not match the crypto contract (fail closed)."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def canonical(value: Any) -> bytes:
    """Canonical UTF-8 JSON: sorted keys, no whitespace, no NaN/Infinity."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def content_hash(value: Any) -> str:
    return digest(canonical(value))


def loads_strict(raw: bytes | str) -> Any:
    """Parse JSON rejecting duplicate keys and non-finite constants."""

    def pairs(items):
        out = {}
        for key, val in items:
            if key in out:
                raise ContractError("SCHEMA_INVALID", f"duplicate key {key!r}")
            out[key] = val
        return out

    def constant(name):
        raise ContractError("SCHEMA_INVALID", f"non-finite constant {name}")

    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except json.JSONDecodeError as exc:
        raise ContractError("SCHEMA_INVALID", "invalid JSON") from exc


def utc(value: Any, field: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ContractError("SCHEMA_INVALID", f"{field} must be ISO-8601 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("SCHEMA_INVALID", f"{field} is not a timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ContractError("SCHEMA_INVALID", f"{field} must be UTC")
    return parsed


def _keys(value: Any, required: set[str], optional: set[str], label: str) -> None:
    if type(value) is not dict:
        raise ContractError("SCHEMA_INVALID", f"{label} must be an object")
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing or extra:
        raise ContractError(
            "SCHEMA_INVALID", f"{label}: missing {sorted(missing)} unknown {sorted(extra)}"
        )


def qualified_id(value: Any, field: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise ContractError("SCHEMA_INVALID", f"{field} must be a crypto:-qualified identifier")
    return value


def validate_request(request: Any) -> dict:
    """Validate a crypto research request. Returns it unchanged or raises ContractError.

    The request declares intent only: request type, hypothesis, references by
    (name, version), cutoff and bounded parameters. It can never name a command,
    module, path, URL, handler or capital permission.
    """
    _keys(
        request,
        {
            "schema_version",
            "request_id",
            "request_type",
            "research_id",
            "hypothesis_id",
            "references",
            "data_cutoff",
            "parameters",
            "priority_hint",
        },
        {"client_ref"},
        "request",
    )
    if request["schema_version"] != REQUEST_SCHEMA:
        raise ContractError("SCHEMA_INVALID", "schema_version")
    for field in ("request_id", "research_id", "hypothesis_id"):
        qualified_id(request[field], field)
    if request["request_type"] not in REQUEST_TYPES:
        raise ContractError("REQUEST_TYPE_NOT_ALLOWED", str(request["request_type"])[:64])
    refs = request["references"]
    _keys(refs, set(REFERENCE_KINDS), set(), "references")
    for kind in REFERENCE_KINDS:
        _keys(refs[kind], {"name", "version"}, set(), f"references.{kind}")
        for field in ("name", "version"):
            if type(refs[kind][field]) is not str or not _NAME.fullmatch(refs[kind][field]):
                raise ContractError("SCHEMA_INVALID", f"references.{kind}.{field}")
    utc(request["data_cutoff"], "data_cutoff")
    params = request["parameters"]
    _keys(params, set(PARAMETER_BOUNDS), {"placebo_seed"}, "parameters")
    if type(params["symbol"]) is not str or not re.fullmatch(r"[A-Z0-9]{2,20}", params["symbol"]):
        raise ContractError("SCHEMA_INVALID", "parameters.symbol")
    for field, bounds in PARAMETER_BOUNDS.items():
        if field == "symbol":
            continue
        low, high = bounds
        value = params[field]
        if type(value) is not int or not low <= value <= high:
            raise ContractError("PARAMETER_OUT_OF_BOUNDS", field)
    seed = params.get("placebo_seed")
    if "placebo_seed" in params and (type(seed) is not int or not 0 <= seed <= 1_000_000):
        raise ContractError("PARAMETER_OUT_OF_BOUNDS", "placebo_seed")
    if request["priority_hint"] not in PRIORITIES:
        raise ContractError("SCHEMA_INVALID", "priority_hint")
    if "client_ref" in request:
        try:
            raw = canonical(request["client_ref"])
        except (TypeError, ValueError) as exc:
            raise ContractError("SCHEMA_INVALID", "client_ref must be JSON") from exc
        if len(raw) > 1024:
            raise ContractError("SCHEMA_INVALID", "client_ref larger than 1024 bytes")
    return request


def idempotency_key(request: dict) -> str:
    """Two submissions are the same logical request iff they share request_id."""
    return request["request_id"]


def request_content_hash(request: dict) -> str:
    """Content identity of a request; client_ref is excluded (opaque, echoed back)."""
    return content_hash({key: value for key, value in request.items() if key != "client_ref"})


def _finite(value: Any, path: str = "result") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError("RESULT_INVALID", f"non-finite value at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            _finite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _finite(item, f"{path}[{index}]")


RESULT_FIELDS = {
    "schema_version",
    "result_id",
    "request_id",
    "admission_id",
    "experiment_id",
    "research_id",
    "hypothesis_id",
    "result_state",
    "operational_state",
    "scientific_state",
    "economic_state",
    "capital_permission",
    "produced_at",
    "core_facts",
    "ops_facts",
    "domain_facts",
    "provenance",
}


def validate_result(result: Any) -> dict:
    """Validate a crypto research result, including authority separation invariants."""
    _keys(result, RESULT_FIELDS, set(), "result")
    if result["schema_version"] != RESULT_SCHEMA:
        raise ContractError("RESULT_INVALID", "schema_version")
    for field in (
        "result_id",
        "request_id",
        "admission_id",
        "experiment_id",
        "research_id",
        "hypothesis_id",
    ):
        qualified_id(result[field], field)
    if result["result_state"] not in RESULT_STATES:
        raise ContractError("RESULT_INVALID", "result_state")
    if result["operational_state"] not in OPERATIONAL_STATES:
        raise ContractError("RESULT_INVALID", "operational_state")
    if result["scientific_state"] not in SCIENTIFIC_STATES:
        raise ContractError("RESULT_INVALID", "scientific_state")
    if result["economic_state"] not in ECONOMIC_STATES:
        raise ContractError("RESULT_INVALID", "economic_state")
    if result["capital_permission"] is not False:
        raise ContractError("RESULT_INVALID", "capital_permission must be false")
    utc(result["produced_at"], "produced_at")
    for block in ("core_facts", "ops_facts", "domain_facts", "provenance"):
        if type(result[block]) is not dict:
            raise ContractError("RESULT_INVALID", f"{block} must be an object")
    # Authority separation: operations never imply science; science never implies edge.
    if (
        result["operational_state"] != "SUCCEEDED"
        and result["operational_state"] != "SKIPPED_ALREADY_SUCCEEDED"
    ):
        if (result["scientific_state"], result["economic_state"], result["result_state"]) != (
            "NOT_EVALUATED",
            "NOT_EVALUATED",
            "FAILED_OPERATIONAL",
        ):
            raise ContractError(
                "RESULT_INVALID", "failed operation cannot carry scientific or economic state"
            )
    if result["economic_state"] == "WATCH" and result["scientific_state"] != "SUPPORTED":
        raise ContractError("RESULT_INVALID", "economic WATCH requires SUPPORTED science")
    if result["result_state"] == "WATCH_NO_CAPITAL" and result["economic_state"] != "WATCH":
        raise ContractError("RESULT_INVALID", "WATCH_NO_CAPITAL requires economic WATCH")
    for field in ("content_hash", "request_content_hash"):
        value = result["provenance"].get(field)
        if value is not None and not _HASH.fullmatch(str(value)):
            raise ContractError("RESULT_INVALID", f"provenance.{field}")
    _finite(result)
    canonical(result)
    return result


__all__ = [
    "DOMAIN_PREFIX",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "OUTCOME_SCHEMA",
    "REQUESTER_TRUST",
    "REQUEST_TYPES",
    "REFERENCE_KINDS",
    "RESULT_STATES",
    "OUTCOME_STATUSES",
    "EXIT_CODES",
    "OPERATIONAL_STATES",
    "SCIENTIFIC_STATES",
    "ECONOMIC_STATES",
    "PARAMETER_BOUNDS",
    "ContractError",
    "canonical",
    "digest",
    "content_hash",
    "loads_strict",
    "utc",
    "qualified_id",
    "validate_request",
    "validate_result",
    "idempotency_key",
    "request_content_hash",
]
