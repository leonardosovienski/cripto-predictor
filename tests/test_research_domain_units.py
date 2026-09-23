"""Unit tests of the crypto research domain (contract, admission, worker economics).

Includes the regression tests of the two defects reproduced at baseline 5fd4e1b:
  CR-F003  pending quota never released (AdmissionStore)
  CR-F004  net return reported with one leg and no funding; no net confidence interval
"""

from __future__ import annotations

import json

import pytest
from conformance.fixtures import build, request

from GarimpoInvestimentos.research_admission import AdmissionStore
from GarimpoInvestimentos.research_contract import (
    ContractError,
    request_content_hash,
    validate_request,
    validate_result,
)
from GarimpoInvestimentos.research_worker import evaluate
from GarimpoInvestimentos.v3.costs import CostModel


def test_client_ref_is_outside_the_content_identity():
    a = request("crypto:REQ-1", client_ref="x")
    b = request("crypto:REQ-1", client_ref={"other": [1, 2]})
    assert (
        request_content_hash(a)
        == request_content_hash(b)
        == request_content_hash(request("crypto:REQ-1"))
    )


@pytest.mark.parametrize(
    "field", ["command", "module", "path", "url", "handler", "capital_permission"]
)
def test_request_can_never_choose_execution(field):
    with pytest.raises(ContractError):
        validate_request(request("crypto:REQ-1") | {field: "x"})


def test_ids_must_be_domain_qualified():
    for field in ("request_id", "research_id", "hypothesis_id"):
        with pytest.raises(ContractError):
            validate_request(request("crypto:REQ-1") | {field: "H9"})


def test_pending_quota_is_released_when_the_request_terminates(tmp_path):
    """CR-F003 regression: max_pending_requests must not count finished requests forever."""
    env = build(tmp_path, max_pending=2)
    store = AdmissionStore(tmp_path / "admission.sqlite", env["policy"])
    assert store.submit(request("crypto:REQ-Q1"))["decision"] == "ACCEPTED"
    assert store.submit(request("crypto:REQ-Q2"))["decision"] == "ACCEPTED"
    blocked = store.submit(request("crypto:REQ-Q3"))
    assert (blocked["decision"], blocked["reason_code"]) == ("REJECTED", "PENDING_QUOTA")
    store.mark_terminal("crypto:REQ-Q1", "crypto:RESULT-Q1")
    assert store.submit(request("crypto:REQ-Q3"))["decision"] == "ACCEPTED"
    store.mark_terminal("crypto:REQ-Q1", "crypto:RESULT-Q1")  # idempotent
    with pytest.raises(ValueError, match="TERMINAL_RESULT_CONFLICT"):
        store.mark_terminal("crypto:REQ-Q1", "crypto:RESULT-OTHER")


def test_policy_change_requires_readmission(tmp_path):
    env = build(tmp_path)
    store = AdmissionStore(tmp_path / "admission.sqlite", env["policy"])
    store.submit(request("crypto:REQ-P1"))
    policy = json.loads(env["policy"].read_text(encoding="utf-8"))
    policy["policy_version"] = 2
    env["policy"].write_text(json.dumps(policy), encoding="utf-8")
    assert store.revalidate("crypto:REQ-P1") == {
        "decision": "REQUIRES_READMISSION",
        "reason_code": "POLICY_CHANGED",
    }


def _worker_request(tmp_path, dataset="case_b"):
    from conformance.fixtures import objects

    refs, identities = [], {}
    import hashlib

    from GarimpoInvestimentos.research_contract import canonical

    chosen = {
        "protocol": "fixed-shadow",
        "dataset": dataset.replace("_", "-"),
        "baseline": "flat",
        "cost_model": "v3-frozen",
        "evidence": "none",
    }
    for kind, name in chosen.items():
        raw = canonical(objects()[(kind, name)])
        path = tmp_path / f"{kind}.json"
        path.write_bytes(raw)
        refs.append({"kind": kind, "path": str(path)})
        identities[kind] = hashlib.sha256(raw).hexdigest()
    task = {k: v for k, v in request("crypto:REQ-W", dataset=dataset).items()}
    return {
        "schema": "crypto-admitted-backtest/2",
        "experiment_id": "crypto:EXP-W",
        "trial_id": "crypto:TRIAL-W",
        "request": task,
        "references": refs,
        "identities": identities,
        "registered_at": "2026-09-01T00:00:00Z",
        "code_version": "cripto-predictor==test",
    }


def test_net_return_uses_the_frozen_cost_model_and_has_its_own_interval(tmp_path):
    """CR-F004 regression: net = gross + funding − 2 legs × (fee + slippage), with a net CI."""
    from conformance.fixtures import DATASETS

    effect = evaluate(_worker_request(tmp_path, "case_b"))
    costs = CostModel(10.0, 5.0)
    expected = [costs.net_return(g, 1.0, 0.0001, 7 * 24.0) for g in DATASETS["case_b"]]
    metrics = effect["metrics"]
    assert metrics["net_return_bps"] == round(sum(expected) / len(expected) * 10_000)
    assert effect["costs"]["round_trip_friction_bps"] == 30
    assert metrics["gross_return_bps"] > 0 > metrics["net_return_bps"]
    assert metrics["net_ci_low_bps"] <= metrics["net_return_bps"] <= metrics["net_ci_high_bps"]
    assert effect["economic_state"] == "NO_EDGE"


def test_placebo_signal_is_data_independent_and_seeded(tmp_path):
    base = _worker_request(tmp_path, "positive")
    first = dict(
        base,
        request=base["request"]
        | {"parameters": base["request"]["parameters"] | {"placebo_seed": 3}},
    )
    a, b = evaluate(first), evaluate(first)
    assert a == b
    assert a["metrics"]["short_observations"] > 0 and a["placebo_seed"] == 3


def test_result_validation_keeps_authorities_separate():
    ok = {
        "schema_version": "crypto-research-result/1",
        "result_id": "crypto:RESULT-1",
        "request_id": "crypto:REQ-1",
        "admission_id": "crypto:ADM-1",
        "experiment_id": "crypto:EXP-1",
        "research_id": "crypto:R",
        "hypothesis_id": "crypto:H",
        "result_state": "FAILED_OPERATIONAL",
        "operational_state": "FAILED",
        "scientific_state": "NOT_EVALUATED",
        "economic_state": "NOT_EVALUATED",
        "capital_permission": False,
        "produced_at": "2026-09-01T00:00:00Z",
        "core_facts": {},
        "ops_facts": {},
        "domain_facts": {},
        "provenance": {},
    }
    validate_result(ok)
    for bad in (
        ok | {"scientific_state": "SUPPORTED"},  # Ops failure -> science
        ok | {"economic_state": "WATCH"},  # Ops failure -> edge
        ok
        | {
            "operational_state": "SUCCEEDED",
            "result_state": "WATCH_NO_CAPITAL",
            "scientific_state": "INCONCLUSIVE",
            "economic_state": "WATCH",
        },  # no science -> edge
        ok | {"capital_permission": True},  # edge -> capital
    ):
        with pytest.raises(ContractError):
            validate_result(bad)


def test_windows_state_root_longer_than_max_path_budget_fails_fast(tmp_path, monkeypatch):
    import sys

    from GarimpoInvestimentos.research_execution import MAX_STATE_ROOT_CHARS
    from GarimpoInvestimentos.research_runner import Circuit

    monkeypatch.setattr(sys, "platform", "win32")
    deep = tmp_path / ("d" * (MAX_STATE_ROOT_CHARS + 5))
    with pytest.raises(SystemExit, match="STATE_ROOT_TOO_LONG"):
        Circuit(deep)
    assert not deep.exists()
