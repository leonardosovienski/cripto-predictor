from copy import deepcopy

import pytest
from research_protocol import canonical, digest, payload_hash

from GarimpoInvestimentos.research_results import ResultConflict, ResultOutbox

SECRET = bytes.fromhex("33" * 32)
SHA = "ab" * 32
SOURCE = "12" * 20


class Admission:
    def admitted_context(self, task_id):
        assert task_id == "TASK-001"
        return {
            "task": {"research_id": "RESEARCH-001", "hypothesis_id": "H6"},
            "task_payload_hash": SHA,
            "receipt": {
                "admission_id": "ADMISSION-001",
                "policy_hash": SHA,
                "resolved_references": [{"content_hash": SHA}],
            },
        }


def identity():
    return {"package_version": "1.0.0", "source_sha": SOURCE, "artifact_sha256": SHA}


def content(name):
    return {"name": name, "version": "v1", "content_hash": SHA}


def result():
    resolved = digest(canonical([{"content_hash": SHA}]))
    return {
        "schema_version": "ResearchResultV1",
        "result_id": "RESULT-001",
        "task_id": "TASK-001",
        "admission_id": "ADMISSION-001",
        "research_id": "RESEARCH-001",
        "hypothesis_id": "H6",
        "experiment_id": "EXPERIMENT-001",
        "result_envelope_state": "PRODUCED",
        "envelope_failure_reason": None,
        "produced_at": "2026-09-19T23:03:00Z",
        "core_facts": {
            "identity": identity(), "trial_ids": ["TRIAL-001"],
            "scientific_state": "INCONCLUSIVE", "temporal_integrity": "PASS",
            "statistics_receipt_hash": SHA,
        },
        "ops_facts": {
            "identity": identity(), "ops_run_ids": ["RUN-001"],
            "operational_state": "SUCCEEDED", "started_at": "2026-09-19T23:00:00Z",
            "finished_at": "2026-09-19T23:02:00Z", "exit_code": 0,
            "runtime_provenance_hash": SHA,
        },
        "crypto_facts": {
            "identity": identity(), "dataset_identity": content("dataset"),
            "model_identity": content("model"), "feature_set_identity": content("features"),
            "data_cutoff": "2026-09-18T00:00:00Z",
            "metrics": {"sample_size": 100, "gross_return_bps": 10, "net_return_bps": -5,
                        "max_drawdown_bps": -20, "turnover_bps": 100,
                        "ci_low_bps": -30, "ci_high_bps": 20},
            "baseline_comparison": {"baseline_id": "BASE-001", "outcome": "LOSES",
                                    "gross_delta_bps": 2, "net_delta_bps": -3},
            "costs": {"fee_bps": 10, "slippage_bps": 5, "total_cost_bps": 15},
            "economic_state": "NO_EDGE", "artifacts": [],
        },
        "provenance": {"task_payload_hash": SHA, "admission_policy_hash": SHA,
                       "resolved_references_hash": resolved, "crypto_source_sha": SOURCE},
    }


def store(tmp_path):
    return ResultOutbox(tmp_path / "result.db", admission_store=Admission(),
                        publisher_identity="crypto-qa", key_id="crypto-f4-key", secret=SECRET)


def test_result_outbox_is_durable_idempotent_and_correlated(tmp_path):
    first = store(tmp_path).produce(result())
    assert first["status"] == "produced"
    second = store(tmp_path).produce(result())
    assert second["status"] == "duplicate"
    assert store(tmp_path).state("RESULT-001")["payload_hash"] == payload_hash(result())
    assert len(store(tmp_path).pending()) == 1


def test_result_id_payload_conflict_fails_closed(tmp_path):
    outbox = store(tmp_path)
    outbox.produce(result())
    changed = deepcopy(result())
    changed["crypto_facts"]["metrics"]["sample_size"] += 1
    with pytest.raises(ResultConflict):
        outbox.produce(changed)


def test_result_must_match_admission_identities(tmp_path):
    changed = result()
    changed["provenance"]["admission_policy_hash"] = "cd" * 32
    with pytest.raises(PermissionError):
        store(tmp_path).produce(changed)


def test_result_delivery_attempt_ack_and_retry_are_durable(tmp_path):
    path_store = store(tmp_path)
    envelope = path_store.produce(result())["envelope"]
    path_store.record_send("RESULT-001", envelope["message_id"])
    assert store(tmp_path).state("RESULT-001")["attempt_count"] == 1
    assert store(tmp_path).fail_delivery(
        "RESULT-001", envelope["message_id"], "CAIN_OFFLINE", max_attempts=2
    )["status"] == "RETRYABLE"
    store(tmp_path).record_send("RESULT-001", envelope["message_id"])
    state = store(tmp_path).acknowledge(
        "RESULT-001", envelope["message_id"], processed_at=result()["produced_at"]
    )
    assert state["status"] == "PUBLISHED"
    assert store(tmp_path).reconcile() == {"pending": 0, "published": 1, "dead_letters": 0}


def test_result_ack_rejects_wrong_message_identity(tmp_path):
    path_store = store(tmp_path)
    path_store.produce(result())
    with pytest.raises(ValueError, match="ACK_CONFLICT"):
        path_store.acknowledge("RESULT-001", "00" * 32, processed_at=result()["produced_at"])
