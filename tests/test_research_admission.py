import json

import pytest
from research_protocol import sign_task

from GarimpoInvestimentos.research_admission import AdmissionStore

SECRET = bytes.fromhex("22" * 32)
SCOPE = "crypto.research.propose"


def ref(kind, name):
    return {"kind": kind, "name": name, "version": "v1"}


def task(task_id="TASK-001"):
    return {
        "schema_version": "ResearchTaskV1",
        "task_id": task_id,
        "research_id": "RESEARCH-001",
        "parent_task_id": None,
        "hypothesis_id": "H6",
        "domain": "crypto",
        "request_type": "BACKTEST_EXISTING_HYPOTHESIS",
        "protocol_ref": ref("protocol", "backtest-standard"),
        "dataset_constraint_ref": ref("dataset", "btc-daily-pit"),
        "baseline_refs": [ref("baseline", "majority-direction")],
        "cost_model_ref": ref("cost_model", "spot-standard"),
        "evidence_refs": [ref("evidence", "cain-receipt-001")],
        "bounded_parameters": {
            "symbol": "BTCUSDT",
            "horizon_days": 7,
            "max_observations": 500,
            "fee_bps": 10,
            "slippage_bps": 5,
        },
        "priority_hint": "HIGH",
        "created_at": "2026-09-19T22:30:00Z",
        "expires_at": "2026-09-20T22:30:00Z",
        "requested_by": "qa-cain-f3",
        "provenance": {
            "cain_source_sha": "6f9d254776b2a3c251f6cce14529087c57ebbeae",
            "retrieval_receipt_ids": ["receipt-001"],
            "proposal_model": "deterministic-fixture",
        },
    }


def envelope(value=None, **overrides):
    arguments = dict(
        producer="CAIN",
        publisher_identity="cain-qa",
        consumer="CRIPTO",
        scope=SCOPE,
        key_id="cain-f3-key",
        secret=SECRET,
    )
    arguments.update(overrides)
    return sign_task(value or task(), **arguments)


def policy():
    entries = [
        ("protocol", "backtest-standard"),
        ("dataset", "btc-daily-pit"),
        ("baseline", "majority-direction"),
        ("cost_model", "spot-standard"),
        ("evidence", "cain-receipt-001"),
    ]
    return {
        "schema_version": "CryptoResearchAdmissionPolicyV1",
        "policy_id": "crypto-local-research",
        "policy_version": 1,
        "owner": "CRIPTO_OPERATOR",
        "publishers": [
            {
                "publisher_identity": "cain-qa",
                "key_id": "cain-f3-key",
                "scopes": [SCOPE],
                "revoked": False,
            }
        ],
        "handlers": {
            "BACKTEST_EXISTING_HYPOTHESIS": "crypto.handlers.backtest_existing_hypothesis.v1"
        },
        "registry": [
            {
                "kind": kind,
                "name": name,
                "version": "v1",
                "revision_id": f"{kind}:{name}:revision-001",
                "content_hash": f"{index + 1:064x}",
                "scopes": [SCOPE],
            }
            for index, (kind, name) in enumerate(entries)
        ],
        "limits": {
            "max_pending_tasks": 10,
            "max_task_bytes": 16384,
            "max_refs": 8,
            "max_parameter_bytes": 1024,
            "rate_limit_per_minute": 10,
            "max_concurrency": 1,
            "cpu_seconds": 60,
            "memory_mb": 512,
            "disk_mb": 128,
            "timeout_seconds": 120,
            "max_retries": 2,
            "dead_letter_threshold": 3,
            "max_age_seconds": 86400,
            "per_publisher_pending": 10,
            "max_priority": "NORMAL",
        },
        "allowed_symbols": ["BTCUSDT"],
    }


def setup(tmp_path, value=None, keys=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(value or policy()), encoding="utf-8")
    store = AdmissionStore(
        tmp_path / "admission.db",
        path,
        keys=keys if keys is not None else {("cain-qa", "cain-f3-key"): SECRET},
    )
    return store, path


def test_accepts_authenticates_freezes_refs_and_clamps_priority(tmp_path):
    store, _ = setup(tmp_path)
    receipt = store.submit(envelope(), now="2026-09-19T22:31:00Z")
    assert receipt["decision"] == "ACCEPTED"
    assert receipt["policy_id"] == "crypto-local-research"
    assert len(receipt["policy_hash"]) == 64
    assert len(receipt["resolved_references"]) == 5
    assert all(len(item["content_hash"]) == 64 for item in receipt["resolved_references"])
    assert receipt["admitted_handler"].endswith(".v1")
    assert receipt["normalized_priority"] == "NORMAL"
    assert receipt["provenance"]["authorization_result"] == "AUTHORIZED"
    assert store.revalidate("TASK-001", now="2026-09-19T22:32:00Z")["decision"] == "ACCEPTED"


def test_duplicate_is_idempotent_and_changed_payload_conflicts(tmp_path):
    store, _ = setup(tmp_path)
    first = store.submit(envelope(), now="2026-09-19T22:31:00Z")
    duplicate = store.submit(envelope(), now="2026-09-19T22:31:01Z")
    assert duplicate["duplicate"] is True
    assert duplicate["admission_id"] == first["admission_id"]
    changed = task()
    changed["bounded_parameters"]["fee_bps"] = 11
    conflict = store.submit(envelope(changed), now="2026-09-19T22:31:02Z")
    assert conflict["decision"] == "CONFLICT"
    assert store.receipt("TASK-001")["decision"] in {"ACCEPTED", "CONFLICT"}


@pytest.mark.parametrize(
    "case",
    ["unknown", "revoked", "wrong_scope", "forged"],
)
def test_publisher_failures_are_unauthorized(tmp_path, case):
    value = policy()
    keys = {("cain-qa", "cain-f3-key"): SECRET}
    message = envelope()
    if case == "unknown":
        message = envelope(publisher_identity="unknown")
    elif case == "revoked":
        value["publishers"][0]["revoked"] = True
    elif case == "wrong_scope":
        message = envelope(scope="crypto.research.admin")
    else:
        keys[("cain-qa", "cain-f3-key")] = bytes.fromhex("33" * 32)
    store, _ = setup(tmp_path, value, keys)
    receipt = store.submit(message, now="2026-09-19T22:31:00Z")
    assert receipt["decision"] == "UNAUTHORIZED"


def test_expiry_unknown_reference_symbol_and_quota_fail_closed(tmp_path):
    store, _ = setup(tmp_path)
    assert store.submit(envelope(), now="2026-09-21T00:00:00Z")["decision"] == "EXPIRED"

    store, _ = setup(tmp_path / "ref")
    changed = task("TASK-REF")
    changed["protocol_ref"]["name"] = "not-registered"
    receipt = store.submit(envelope(changed), now="2026-09-19T22:31:00Z")
    assert (receipt["decision"], receipt["reason_code"]) == (
        "REJECTED",
        "REFERENCE_UNAUTHORIZED_OR_UNKNOWN",
    )

    store, _ = setup(tmp_path / "symbol")
    changed = task("TASK-SYMBOL")
    changed["bounded_parameters"]["symbol"] = "ETHUSDT"
    receipt = store.submit(envelope(changed), now="2026-09-19T22:31:00Z")
    assert receipt["reason_code"] == "SYMBOL_NOT_ALLOWED"

    limited = policy()
    limited["limits"]["max_pending_tasks"] = 1
    store, _ = setup(tmp_path / "quota", limited)
    assert store.submit(envelope(task("TASK-Q1")), now="2026-09-19T22:31:00Z")["decision"] == "ACCEPTED"
    receipt = store.submit(envelope(task("TASK-Q2")), now="2026-09-19T22:31:01Z")
    assert receipt["reason_code"] == "GLOBAL_PENDING_QUOTA"


def test_policy_or_reference_change_requires_readmission(tmp_path):
    store, path = setup(tmp_path)
    store.submit(envelope(), now="2026-09-19T22:31:00Z")
    changed = policy()
    changed["registry"][0]["content_hash"] = "f" * 64
    changed["policy_version"] = 2
    path.write_text(json.dumps(changed), encoding="utf-8")
    result = store.revalidate("TASK-001", now="2026-09-19T22:32:00Z")
    assert result == {"decision": "REQUIRES_READMISSION", "reason_code": "POLICY_CHANGED"}


def test_unavailable_local_handler_is_rejected_without_dynamic_import(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy()), encoding="utf-8")
    store = AdmissionStore(
        tmp_path / "admission.db",
        path,
        keys={("cain-qa", "cain-f3-key"): SECRET},
        available_handlers=set(),
    )
    receipt = store.submit(envelope(), now="2026-09-19T22:31:00Z")
    assert (receipt["decision"], receipt["reason_code"]) == (
        "REJECTED",
        "HANDLER_UNAVAILABLE",
    )


def test_contract_unknown_fields_never_reach_inbox(tmp_path):
    store, _ = setup(tmp_path)
    message = envelope()
    message["payload"]["command"] = "powershell.exe"
    with pytest.raises(ValueError):
        store.submit(message, now="2026-09-19T22:31:00Z")
    with store.connection() as db:
        assert db.execute("SELECT count(*) FROM task_inbox").fetchone()[0] == 0
