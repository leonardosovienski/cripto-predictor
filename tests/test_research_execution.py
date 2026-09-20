import json
from datetime import UTC, datetime, timedelta

import pytest
from predictor_core.contracts.trial_v2 import dataset_fingerprint
from research_protocol import sign_task

from cain.research_results import ResultInbox
from cain.research_tasks import TaskOutbox
from GarimpoInvestimentos.research_admission import AdmissionStore
from GarimpoInvestimentos.research_execution import ReferenceStore, ResearchExecutor
from GarimpoInvestimentos.research_results import ResultOutbox

CAIN_SECRET = bytes.fromhex("42" * 32)
CRIPTO_SECRET = bytes.fromhex("43" * 32)
SCOPE = "crypto.research.propose"
SHA = "a1" * 32
SOURCE = "12" * 20


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def identity(name):
    return {"package_version": name, "source_sha": SOURCE, "artifact_sha256": SHA}


def setup_stack(tmp_path):
    object_store = ReferenceStore(tmp_path / "operator-objects")
    cutoff = datetime.now(UTC) - timedelta(days=1)
    rows = []
    for index in range(30):
        observed = cutoff - timedelta(days=30 - index)
        rows.append(
            {
                "observed_at": observed.isoformat().replace("+00:00", "Z"),
                "available_at": (observed + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                "gross_return": 0.002,
                "funding_rate": 0.0,
            }
        )
    dataset_hash = dataset_fingerprint(
        rows, fields=("observed_at", "available_at", "gross_return", "funding_rate")
    ).removeprefix("sha256:")
    objects = {
        "protocol": {
            "handler": "crypto.handlers.backtest_existing_hypothesis.v1",
            "minimum_sample": 20,
            "turnover_bps": 100,
            "hypothesis_family": "fixed-shadow-signal",
            "feature_version": "frozen-feature-v1",
            "model_version": "existing-hypothesis-v1",
            "selection_path": {
                "family": "fixed-shadow-signal",
                "candidate_set": ["existing-hypothesis-v1"],
                "selection_metric": "predeclared",
                "selected_candidate": "existing-hypothesis-v1",
            },
        },
        "dataset": {
            "dataset_version": "fixture-v1",
            "data_cutoff": cutoff.isoformat().replace("+00:00", "Z"),
            "label_start": rows[0]["observed_at"],
            "label_end": rows[-1]["available_at"],
            "row_fingerprint": dataset_hash,
            "rows": rows,
        },
        "baseline": {"baseline_id": "BASE-FROZEN-001", "gross_return_bps": 5, "net_return_bps": 0},
        "cost_model": {"fee_bps": 10, "slippage_bps": 5},
        "evidence": {"receipt_id": "CAIN-EVIDENCE-001", "classification": "qa-public"},
    }
    names = {
        "protocol": "backtest-standard", "dataset": "btc-daily-pit",
        "baseline": "majority-direction", "cost_model": "spot-standard",
        "evidence": "cain-receipt-001",
    }
    registry = []
    for kind, value in objects.items():
        content_hash = object_store.put_operator_bytes(encoded(value))
        registry.append(
            {"kind": kind, "name": names[kind], "version": "v1",
             "revision_id": f"{kind}:{names[kind]}:fixture-001",
             "content_hash": content_hash, "scopes": [SCOPE]}
        )
    policy = {
        "schema_version": "CryptoResearchAdmissionPolicyV1",
        "policy_id": "crypto-local-research", "policy_version": 1,
        "owner": "CRIPTO_OPERATOR",
        "publishers": [{"publisher_identity": "cain-qa", "key_id": "cain-key",
                        "scopes": [SCOPE], "revoked": False}],
        "handlers": {"BACKTEST_EXISTING_HYPOTHESIS": "crypto.handlers.backtest_existing_hypothesis.v1"},
        "registry": registry,
        "limits": {"max_pending_tasks": 10, "max_task_bytes": 16384, "max_refs": 8,
                   "max_parameter_bytes": 1024, "rate_limit_per_minute": 10,
                   "max_concurrency": 1, "cpu_seconds": 60, "memory_mb": 512,
                   "disk_mb": 128, "timeout_seconds": 30, "max_retries": 2,
                   "dead_letter_threshold": 3, "max_age_seconds": 86400,
                   "per_publisher_pending": 10, "max_priority": "NORMAL"},
        "allowed_symbols": ["BTCUSDT"],
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    admission = AdmissionStore(
        tmp_path / "admission.sqlite", policy_path,
        keys={("cain-qa", "cain-key"): CAIN_SECRET},
    )
    now = datetime.now(UTC)
    ref = lambda kind: {"kind": kind, "name": names[kind], "version": "v1"}
    task = {
        "schema_version": "ResearchTaskV1", "task_id": "TASK-E2E-001",
        "research_id": "RESEARCH-E2E-001", "parent_task_id": None,
        "hypothesis_id": "HYPOTHESIS-FROZEN-001", "domain": "crypto",
        "request_type": "BACKTEST_EXISTING_HYPOTHESIS",
        "protocol_ref": ref("protocol"), "dataset_constraint_ref": ref("dataset"),
        "baseline_refs": [ref("baseline")], "cost_model_ref": ref("cost_model"),
        "evidence_refs": [ref("evidence")],
        "bounded_parameters": {"symbol": "BTCUSDT", "horizon_days": 7,
                               "max_observations": 100, "fee_bps": 10, "slippage_bps": 5},
        "priority_hint": "HIGH", "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=12)).isoformat().replace("+00:00", "Z"),
        "requested_by": "cain-e2e", "provenance": {
            "cain_source_sha": SOURCE, "retrieval_receipt_ids": ["receipt-001"],
            "proposal_model": "deterministic-fixture",
        },
    }
    envelope = sign_task(
        task, producer="CAIN", publisher_identity="cain-qa", consumer="CRIPTO",
        scope=SCOPE, key_id="cain-key", secret=CAIN_SECRET,
    )
    assert admission.submit(envelope)["decision"] == "ACCEPTED"
    outbox = ResultOutbox(
        tmp_path / "result.sqlite", admission_store=admission,
        publisher_identity="crypto-qa", key_id="crypto-key", secret=CRIPTO_SECRET,
    )
    executor = ResearchExecutor(
        tmp_path / "execution", admission_store=admission, result_outbox=outbox,
        reference_store=object_store, crypto_source_sha=SOURCE,
        artifact_identities={"core": identity("3.2.1"), "ops": identity("4.2.1"),
                             "crypto": identity("1.1.1rc1")},
    )
    return executor, admission, outbox, object_store


def test_real_admitted_execution_uses_core_ops_and_crypto_and_enqueues_result(tmp_path):
    executor, _, outbox, _ = setup_stack(tmp_path)
    completed = executor.execute("TASK-E2E-001")
    result = completed["result"]
    assert completed["experiment"]["state"] == "COMPLETED"
    assert result["ops_facts"]["operational_state"] == "SUCCEEDED"
    assert result["core_facts"]["trial_ids"]
    assert result["core_facts"]["scientific_state"] == "SUPPORTED"
    assert result["crypto_facts"]["metrics"]["gross_return_bps"] == 20
    assert result["crypto_facts"]["metrics"]["net_return_bps"] == 5
    assert result["crypto_facts"]["economic_state"] == "NO_EDGE"
    assert outbox.pending()[0]["payload"]["result_id"] == result["result_id"]
    duplicate = executor.execute("TASK-E2E-001")
    assert duplicate["outbox"]["status"] == "duplicate"
    assert duplicate["result"] == result


def test_crash_after_domain_effect_recovers_without_second_logical_effect(tmp_path):
    executor, _, outbox, _ = setup_stack(tmp_path)
    with pytest.raises(RuntimeError, match="INJECTED_CRASH_AFTER_DOMAIN_EFFECT"):
        executor.execute("TASK-E2E-001", crash_at="after_domain_effect")
    assert executor.reconcile()[0]["finding"] == "ORPHAN_EFFECT_RECOVERABLE"
    effect = next((tmp_path / "execution/experiments").glob("*/domain-effect.json"))
    before = effect.read_bytes()
    recovered = executor.execute("TASK-E2E-001")
    assert recovered["experiment"]["state"] == "COMPLETED"
    assert effect.read_bytes() == before
    assert len(outbox.pending()) == 1


def test_reference_hash_tamper_fails_closed_before_ops(tmp_path):
    executor, _, _, store = setup_stack(tmp_path)
    target = next(path for path in store.root.rglob("*") if path.is_file())
    target.chmod(0o600)
    target.write_bytes(b"{}")
    with pytest.raises(ValueError, match="hash verification"):
        executor.execute("TASK-E2E-001")
    assert not (tmp_path / "execution/ops-runtime").exists()


def test_crash_after_result_recovers_and_enqueues_identical_result_once(tmp_path):
    executor, _, outbox, _ = setup_stack(tmp_path)
    with pytest.raises(RuntimeError, match="INJECTED_CRASH_AFTER_RESULT"):
        executor.execute("TASK-E2E-001", crash_at="after_result")
    result_file = next((tmp_path / "execution/experiments").glob("*/research-result.json"))
    before = result_file.read_bytes()
    recovered = executor.execute("TASK-E2E-001")
    assert recovered["experiment"]["state"] == "COMPLETED"
    assert result_file.read_bytes() == before
    assert len(outbox.pending()) == 1


def test_bidirectional_real_loop_survives_restart_and_correlates_in_cain(tmp_path):
    executor, admission, crypto_outbox, _ = setup_stack(tmp_path)
    context = admission.admitted_context("TASK-E2E-001")
    cain_tasks = TaskOutbox(
        tmp_path / "cain-task.sqlite", publisher_identity="cain-qa", key_id="cain-key",
        secret=CAIN_SECRET,
    )
    task_message = cain_tasks.propose(context["task"])["envelope"]
    cain_tasks.record_send("TASK-E2E-001", task_message["message_id"])
    duplicate_receipt = admission.submit(task_message)
    assert duplicate_receipt["duplicate"] is True
    cain_tasks.acknowledge(
        "TASK-E2E-001", task_message["message_id"], processed_at=duplicate_receipt["decided_at"]
    )

    executed = executor.execute("TASK-E2E-001")
    result_id = executed["result"]["result_id"]
    result_message = crypto_outbox.pending()[0]
    crypto_outbox.record_send(result_id, result_message["message_id"])
    cain_results = ResultInbox(
        tmp_path / "cain-result.sqlite", task_outbox=cain_tasks,
        publisher_identity="crypto-qa", key_id="crypto-key", secret=CRIPTO_SECRET,
    )
    receipt = cain_results.ingest(result_message)
    crypto_outbox.acknowledge(
        result_id, result_message["message_id"], processed_at=receipt["result"]["produced_at"]
    )
    restarted = ResultInbox(
        tmp_path / "cain-result.sqlite", task_outbox=cain_tasks,
        publisher_identity="crypto-qa", key_id="crypto-key", secret=CRIPTO_SECRET,
    )
    assert restarted.result(result_id)["task_id"] == "TASK-E2E-001"
    assert restarted.for_task("TASK-E2E-001")[0]["result_id"] == result_id
    assert cain_tasks.reconcile()["published"] == 1
    assert crypto_outbox.reconcile()["published"] == 1
