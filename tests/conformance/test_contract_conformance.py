"""Conformance vectors: E2E, IDEMPOTENCY, FUTURE_CANARY and TEMPORAL_INTEGRITY.

Every call goes through the installed `cripto-research` console script in a new process
(no pipeline assembled by hand, no mocks of predictor_core or predictor_ops).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conformance.fixtures import (
    CANARY,
    CUTOFF,
    build,
    cli,
    experiments,
    ops_runtime,
    request,
    write_request,
)


@pytest.fixture()
def env(tmp_path):
    return build(tmp_path)


def _only(lines):
    assert len(lines) == 1, lines
    return lines[0]


def _result(outcome):
    """Full result as written in the outcome file (stdout carries a summary line)."""
    return json.loads(Path(outcome["outcome_file"]).read_text(encoding="utf-8"))["result"]


def _all_text(root: Path) -> str:
    chunks = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl"}:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def test_e2e_result_is_reread_identically_after_restart(env):
    path = write_request(env, "e2e", request("crypto:REQ-E2E-001", client_ref={"ticket": 7}))
    code, lines = cli(env, "process", str(path))
    outcome = _only(lines)
    assert code == 0 and outcome["status"] == "RESULT"
    assert outcome["client_ref"] == {"ticket": 7}
    assert outcome["result_id"].startswith("crypto:RESULT-")
    assert outcome["experiment_id"].startswith("crypto:EXP-")
    assert outcome["operational_state"] == "SUCCEEDED"
    assert outcome["capital_permission"] is False
    stored = json.loads(Path(outcome["outcome_file"]).read_text(encoding="utf-8"))["result"]
    # new process: the authoritative result is re-read, never recomputed
    code, lines = cli(env, "show", "crypto:REQ-E2E-001")
    shown = _only(lines)
    assert code == 0 and shown["source"] == "authoritative_result_store"
    assert shown["result"] == stored
    assert stored["request_id"] == "crypto:REQ-E2E-001"
    assert (
        stored["core_facts"]["trial_ids"]
        and stored["core_facts"]["scientific_state_source"] == "core_trial_registry"
    )
    assert (
        stored["core_facts"]["temporal_validation"]["method"] == "predictor_core.measurement.replay"
    )
    assert (
        stored["ops_facts"]["ops_run_id"]
        and stored["ops_facts"]["operational_state"] == "SUCCEEDED"
    )
    assert stored["ops_facts"]["economic_lock_id"].startswith("economic-")
    assert (
        stored["domain_facts"]["metrics"]["net_ci_low_bps"]
        <= stored["domain_facts"]["metrics"]["net_return_bps"]
    )
    for block in ("core_facts", "ops_facts", "domain_facts", "provenance"):
        assert stored[block]
    code, lines = cli(env, "reconcile")
    assert code == 0 and _only(lines)["findings"] == []


def test_idempotency_duplicate_retry_and_conflict(env):
    first = write_request(env, "a", request("crypto:REQ-IDEM-001", client_ref="first"))
    code, lines = cli(env, "process", str(first))
    original = _only(lines)
    assert code == 0 and original["status"] == "RESULT"
    # same key, same content, different client_ref -> same result, own client_ref echoed
    again = write_request(env, "b", request("crypto:REQ-IDEM-001", client_ref="second"))
    for _ in range(2):
        code, lines = cli(env, "process", str(again))
        duplicate = _only(lines)
        assert code == 0 and duplicate["status"] == "DUPLICATE"
        assert duplicate["client_ref"] == "second"
        assert duplicate["result_id"] == original["result_id"]
        assert _result(duplicate) == _result(original)
    # same key, different content -> CONFLICT, never overwrites
    changed = request("crypto:REQ-IDEM-001", dataset="case_a")
    code, lines = cli(env, "process", str(write_request(env, "c", changed)))
    assert code == 2 and _only(lines)["status"] == "CONFLICT"
    code, lines = cli(env, "show", "crypto:REQ-IDEM-001")
    assert _only(lines)["result"] == _result(original)
    created = list(experiments(env).iterdir())
    assert len(created) == 1
    ops_events = list(ops_runtime(env).glob("crypto-research-*/events.jsonl"))
    succeeded = [
        json.loads(line)
        for line in ops_events[0].read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("run_status") == "SUCCEEDED"
    ]
    assert len(succeeded) == 1


def test_future_canary_fails_closed_and_never_leaks(env):
    path = write_request(env, "canary", request("crypto:REQ-CANARY-001", dataset="future_canary"))
    code, lines = cli(env, "process", str(path))
    outcome = _only(lines)
    assert code == 4 and outcome["status"] == "TEMPORAL_INTEGRITY_VIOLATION"
    assert (
        outcome["scientific_state"] == "NOT_EVALUATED"
        and outcome["economic_state"] == "NOT_EVALUATED"
    )
    assert "LookaheadError" in outcome["reason"]
    code, lines = cli(env, "show", "crypto:REQ-CANARY-001")
    assert code == 3
    assert not list((experiments(env)).rglob("domain-effect.json"))
    assert not list((experiments(env)).rglob("trials-v2.json"))
    # a legitimate request before the cutoff never carries the canary anywhere downstream
    ok = write_request(env, "ok", request("crypto:REQ-CANARY-OK"))
    assert cli(env, "process", str(ok))[0] == 0
    downstream = [
        p for p in (experiments(env)).rglob("*") if p.is_file() and "references" not in p.parts
    ]
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in downstream)
    assert CANARY not in text and "0.0987654321" not in text
    results_db = (env["state"] / "results.sqlite").read_bytes()
    assert CANARY.encode() not in results_db and b"0.0987654321" not in results_db
    assert CANARY not in _all_text(env["state"] / "outcomes")


def test_temporal_integrity_cutoff_mismatch_and_order(env):
    mismatch = request("crypto:REQ-CUTOFF-001", data_cutoff="2026-09-30T00:00:00Z")
    code, lines = cli(env, "process", str(write_request(env, "m", mismatch)))
    outcome = _only(lines)
    assert code == 4 and outcome["status"] == "TEMPORAL_INTEGRITY_VIOLATION"
    assert "data_cutoff" in outcome["reason"]


@pytest.mark.parametrize(
    ("dataset", "result_state", "scientific", "economic"),
    [
        ("case_a", "INCONCLUSIVE", "INCONCLUSIVE", "NO_EDGE"),
        ("case_b", "NO_EDGE", "SUPPORTED", "NO_EDGE"),
        ("insufficient", "CLOSED_INSUFFICIENT_SAMPLE", "INSUFFICIENT_SAMPLE", "NOT_EVALUATED"),
    ],
)
def test_authority_states_stay_separate(env, dataset, result_state, scientific, economic):
    path = write_request(
        env, dataset, request(f"crypto:REQ-{dataset.upper().replace('_', '-')}", dataset=dataset)
    )
    code, lines = cli(env, "process", str(path))
    outcome = _only(lines)
    assert code == 0 and outcome["operational_state"] == "SUCCEEDED"
    assert (outcome["result_state"], outcome["scientific_state"], outcome["economic_state"]) == (
        result_state,
        scientific,
        economic,
    )
    metrics = _result(outcome)["domain_facts"]["metrics"]
    if dataset == "case_b":
        assert metrics["gross_return_bps"] > 0 > metrics["net_return_bps"]
        assert metrics["gross_ci_low_bps"] > 0 and metrics["net_ci_high_bps"] < 0


@pytest.mark.parametrize(
    ("mutate", "status", "reason"),
    [
        (lambda r: r | {"command": "powershell.exe -c calc"}, "REJECTED", "SCHEMA_INVALID"),
        (lambda r: r | {"handler": "os.system"}, "REJECTED", "SCHEMA_INVALID"),
        (lambda r: r | {"capital_permission": True}, "REJECTED", "SCHEMA_INVALID"),
        (lambda r: r | {"request_type": "RUN_SHELL"}, "REJECTED", "REQUEST_TYPE_NOT_ALLOWED"),
        (lambda r: r | {"request_id": "REQ-NO-DOMAIN"}, "REJECTED", "SCHEMA_INVALID"),
        (lambda r: r | {"hypothesis_id": "crypto:H1"}, "REJECTED", "HYPOTHESIS_CLOSED"),
        (lambda r: r | {"hypothesis_id": "crypto:H7"}, "REJECTED", "HYPOTHESIS_NOT_ACTIVE"),
        (
            lambda r: r | {"hypothesis_id": "crypto:NOT-IN-POLICY"},
            "REJECTED",
            "HYPOTHESIS_NOT_ADMITTED",
        ),
        (
            lambda r: (
                r
                | {
                    "references": r["references"]
                    | {"dataset": {"name": "unknown", "version": "v1"}}
                }
            ),
            "REJECTED",
            "REFERENCE_UNAUTHORIZED_OR_UNKNOWN",
        ),
        (
            lambda r: r | {"parameters": r["parameters"] | {"symbol": "ETHUSDT"}},
            "REJECTED",
            "SYMBOL_NOT_ALLOWED",
        ),
        (
            lambda r: r | {"parameters": r["parameters"] | {"fee_bps": 10_000}},
            "REJECTED",
            "PARAMETER_OUT_OF_BOUNDS",
        ),
        (
            lambda r: (
                r
                | {
                    "references": r["references"]
                    | {"protocol": {"name": "frozen-family", "version": "v1"}},
                    "hypothesis_id": "crypto:QUAL-FROZEN-PROBE",
                }
            ),
            "REJECTED",
            "REFUSED",
        ),
    ],
)
def test_admission_rejects_before_any_execution(env, mutate, status, reason):
    value = mutate(request("crypto:REQ-BAD-001"))
    code, lines = cli(env, "process", str(write_request(env, "bad", value)))
    outcome = _only(lines)
    assert code == 2 and outcome["status"] == status
    assert outcome["reason"].startswith(reason)
    if reason != "REFUSED":
        assert not ops_runtime(env).exists()


def test_invalid_json_and_duplicate_keys_are_rejected(env):
    for text in ("{not json", '{"request_id": "crypto:A", "request_id": "crypto:B"}', "[]"):
        code, lines = cli(env, "process", str(write_request(env, "raw", text)))
        assert code == 2 and _only(lines)["status"] == "REJECTED"


def test_cutoff_constant_is_frozen():
    assert CUTOFF == "2026-08-31T00:00:00Z"


def test_duplicate_after_policy_change_returns_the_stored_result(env):
    """A finished request's authoritative result does not depend on the current policy."""
    path = write_request(env, "p", request("crypto:REQ-POLICY-001", client_ref="before"))
    code, lines = cli(env, "process", str(path))
    original = _only(lines)
    assert code == 0 and original["status"] == "RESULT"
    policy = json.loads(env["policy"].read_text(encoding="utf-8"))
    policy["policy_version"] += 1
    env["policy"].write_text(json.dumps(policy, indent=1), encoding="utf-8")
    code, lines = cli(
        env,
        "process",
        str(write_request(env, "p2", request("crypto:REQ-POLICY-001", client_ref="after"))),
    )
    duplicate = _only(lines)
    assert code == 0 and duplicate["status"] == "DUPLICATE"
    assert duplicate["client_ref"] == "after" and _result(duplicate) == _result(original)
    # a request admitted under the old policy but not finished must be readmitted (fail closed)
    pending = write_request(env, "q", request("crypto:REQ-POLICY-002"))
    policy["policy_version"] += 1
    assert cli(env, "process", str(pending), fault="after_admission")[0] == 86
    env["policy"].write_text(json.dumps(policy, indent=1), encoding="utf-8")
    code, lines = cli(env, "process", str(pending))
    assert code == 2 and _only(lines)["reason"] == "POLICY_CHANGED"
