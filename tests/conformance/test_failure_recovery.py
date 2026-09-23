"""Failure injection at the edge, restart recovery and corruption (fail closed).

Faults kill the real `cripto-research` process (os._exit, no cleanup) or make the real
worker crash/hang under predictor_ops. After each fault the SAME request is submitted in
a new process: exactly one domain effect, one Ops success and one result must exist.
"""

from __future__ import annotations

import json
import os
import sqlite3
import stat
from pathlib import Path

import pytest

from conformance.fixtures import (
    build,
    child_environment,
    cli,
    experiments,
    ops_runtime,
    request,
    work_dir,
    write_request,
)
from GarimpoInvestimentos.research_faults import FAULT_EXIT, FAULT_POINTS, PROCESS_DEATH_POINTS


def _only(lines):
    assert len(lines) == 1, lines
    return lines[0]


def _ops_successes(env) -> int:
    total = 0
    for events in ops_runtime(env).glob("crypto-research-*/events.jsonl"):
        for line in events.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("run_status") == "SUCCEEDED":
                total += 1
    return total


def _results(env) -> int:
    with sqlite3.connect(env["state"] / "results.sqlite") as db:
        return db.execute("SELECT count(*) FROM results").fetchone()[0]


def _single_experiment(env) -> Path:
    created = list(experiments(env).iterdir())
    assert len(created) == 1
    return created[0]


@pytest.mark.parametrize("point", PROCESS_DEATH_POINTS)
def test_process_death_at_each_point_recovers_exactly_once(tmp_path, point):
    env = build(tmp_path)
    path = write_request(env, "r", request("crypto:REQ-FAULT-001"))
    code, _ = cli(env, "process", str(path), fault=point)
    assert code == FAULT_EXIT
    if point == "before_admission_commit":
        with sqlite3.connect(env["state"] / "admission.sqlite") as db:
            assert db.execute("SELECT count(*) FROM request_inbox").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM admissions").fetchone()[0] == 0
    code, lines = cli(env, "process", str(path))
    outcome = _only(lines)
    assert code == 0 and outcome["status"] in {"RESULT", "DUPLICATE"}
    assert _ops_successes(env) == 1
    assert _results(env) == 1
    assert len(list((experiments(env)).rglob("domain-effect.json"))) == 1
    code, lines = cli(env, "show", "crypto:REQ-FAULT-001")
    assert code == 0 and _only(lines)["result"]["result_id"] == outcome["result_id"]
    code, lines = cli(env, "process", str(path))
    assert code == 0 and _only(lines)["status"] == "DUPLICATE"
    assert _ops_successes(env) == 1 and _results(env) == 1
    code, lines = cli(env, "reconcile")
    assert code == 0 and _only(lines)["findings"] == []


def test_ops_worker_crash_is_not_a_result_and_retry_succeeds(tmp_path):
    env = build(tmp_path)
    path = write_request(env, "r", request("crypto:REQ-CRASH-001"))
    code, lines = cli(env, "process", str(path), fault="ops_worker_crash")
    failed = _only(lines)
    assert code == 3 and failed["status"] == "OPS_FAILED_RETRYABLE"
    assert (failed["operational_state"], failed["scientific_state"], failed["economic_state"]) == (
        "FAILED",
        "NOT_EVALUATED",
        "NOT_EVALUATED",
    )
    assert _results(env) == 0
    assert cli(env, "show", "crypto:REQ-CRASH-001")[0] == 3
    code, lines = cli(env, "process", str(path))
    assert code == 0 and _only(lines)["status"] == "RESULT"
    assert _ops_successes(env) == 1 and _results(env) == 1


def test_ops_timeout_kills_worker_and_is_not_a_result(tmp_path):
    env = build(tmp_path, timeout_seconds=5)
    path = write_request(env, "r", request("crypto:REQ-TIMEOUT-001"))
    code, lines = cli(env, "process", str(path), fault="ops_worker_hang")
    failed = _only(lines)
    assert code == 3 and failed["status"] == "OPS_FAILED_RETRYABLE"
    assert failed["operational_state"] == "TIMEOUT" and failed["reason"] == "OPS_TIMEOUT"
    assert (
        failed["scientific_state"] == "NOT_EVALUATED"
        and failed["economic_state"] == "NOT_EVALUATED"
    )
    assert not list((experiments(env)).rglob("domain-effect.json"))
    code, lines = cli(env, "process", str(path))
    assert code == 0 and _only(lines)["status"] == "RESULT"


def test_retry_budget_exhaustion_is_a_terminal_operational_failure(tmp_path):
    env = build(tmp_path, max_retries=1)
    path = write_request(env, "r", request("crypto:REQ-BUDGET-001"))
    for _ in range(2):
        code, lines = cli(env, "process", str(path), fault="ops_worker_crash")
        assert code == 3 and _only(lines)["status"] == "OPS_FAILED_RETRYABLE"
    code, lines = cli(env, "process", str(path))
    outcome = _only(lines)
    assert code == 0 and outcome["result_state"] == "FAILED_OPERATIONAL"
    assert (
        outcome["operational_state"],
        outcome["scientific_state"],
        outcome["economic_state"],
    ) == ("FAILED", "NOT_EVALUATED", "NOT_EVALUATED")
    code, lines = cli(env, "show", "crypto:REQ-BUDGET-001")
    assert code == 0 and _only(lines)["result"]["result_state"] == "FAILED_OPERATIONAL"


def _completed(tmp_path, request_id="crypto:REQ-CORRUPT-001"):
    env = build(tmp_path)
    path = write_request(env, "r", request(request_id))
    assert cli(env, "process", str(path))[0] == 0
    return env, path, _single_experiment(env)


def _writable(path: Path) -> None:
    path.chmod(stat.S_IWRITE | stat.S_IREAD)


def test_db_says_result_exists_but_file_is_gone(tmp_path):
    env, path, work = _completed(tmp_path)
    (work / "research-result.json").unlink()
    assert cli(env, "show", "crypto:REQ-CORRUPT-001")[0] == 5
    code, lines = cli(env, "process", str(path))
    assert code == 5 and _only(lines)["status"] == "RECONCILIATION_REQUIRED"
    assert not (work / "research-result.json").exists()  # no silent repair
    assert cli(env, "reconcile")[0] == 5


def test_file_exists_but_index_lost_the_result(tmp_path):
    env, path, work = _completed(tmp_path)
    with sqlite3.connect(env["state"] / "results.sqlite") as db:
        db.execute("DELETE FROM results")
    code, lines = cli(env, "process", str(path))
    assert code == 5 and _only(lines)["status"] == "RECONCILIATION_REQUIRED"
    assert _results(env) == 0  # no silent re-index
    assert cli(env, "reconcile")[0] == 5


def test_modified_result_and_modified_effect_fail_closed(tmp_path, tmp_path_factory):
    env, path, work = _completed(tmp_path)
    result = work / "research-result.json"
    result.write_bytes(
        result.read_bytes()
        .replace(b'"NO_EDGE"', b'"WATCH"')
        .replace(b'"WATCH_NO_CAPITAL"', b'"NO_EDGE"')
    )
    assert cli(env, "show", "crypto:REQ-CORRUPT-001")[0] == 5
    env2, path2, work2 = _completed(tmp_path_factory.mktemp("e"), "crypto:REQ-CORRUPT-002")
    effect = work2 / "domain-effect.json"
    effect.write_bytes(effect.read_bytes() + b" ")
    code, lines = cli(env2, "process", str(path2))
    assert code == 5 and _only(lines)["reason"] == "EFFECT_HASH_MISMATCH"
    code, lines = cli(env2, "reconcile")
    assert code == 5 and any(
        f["finding"] == "EFFECT_HASH_MISMATCH" for f in _only(lines)["findings"]
    )


def test_wrong_hash_of_referenced_object_fails_before_ops(tmp_path):
    env = build(tmp_path)
    policy = json.loads(env["policy"].read_text(encoding="utf-8"))
    dataset = next(
        e for e in policy["registry"] if (e["kind"], e["name"]) == ("dataset", "positive")
    )
    target = env["objects"] / dataset["content_hash"][:2] / dataset["content_hash"]
    _writable(target)
    target.write_bytes(target.read_bytes().replace(b"0.022", b"0.122"))
    code, lines = cli(env, "process", str(write_request(env, "r", request("crypto:REQ-HASH-002"))))
    assert code == 5 and "REFERENCE" in _only(lines)["reason"]
    assert not ops_runtime(env).exists()


def test_reference_changed_after_materialization_fails_closed(tmp_path):
    env = build(tmp_path)
    path = write_request(env, "r", request("crypto:REQ-MAT-001"))
    assert cli(env, "process", str(path), fault="before_ops")[0] == FAULT_EXIT
    materialized = _single_experiment(env) / "references" / "dataset.json"
    _writable(materialized)
    materialized.write_bytes(materialized.read_bytes().replace(b"0.022", b"0.122"))
    code, lines = cli(env, "process", str(path))
    assert code == 5 and "changed after materialization" in _only(lines)["reason"]
    assert _results(env) == 0


def test_reference_receipt_from_another_request_fails_closed(tmp_path):
    env = build(tmp_path)
    first = write_request(env, "a", request("crypto:REQ-A-001"))
    assert cli(env, "process", str(first))[0] == 0
    donor = _single_experiment(env) / "reference-materialization.json"
    second = request("crypto:REQ-B-001", dataset="case_a")
    path = write_request(env, "b", second)
    assert cli(env, "process", str(path), fault="after_admission")[0] == FAULT_EXIT
    # plant the first request's receipt where the second experiment will look
    from GarimpoInvestimentos.research_admission import AdmissionStore
    from GarimpoInvestimentos.research_execution import ResearchExecutor

    context = AdmissionStore(env["state"] / "admission.sqlite", env["policy"]).admitted_context(
        "crypto:REQ-B-001"
    )
    _, logical = ResearchExecutor.logical_identity(context)
    work = work_dir(env, logical)
    work.mkdir(parents=True)
    (work / "reference-materialization.json").write_bytes(donor.read_bytes())
    code, lines = cli(env, "process", str(path))
    assert code == 5 and _only(lines)["reason"] == "REFERENCE_FROM_ANOTHER_REQUEST"


def test_result_metadata_inconsistent_with_index_fails_closed(tmp_path):
    env, path, work = _completed(tmp_path)
    from GarimpoInvestimentos.research_contract import canonical, content_hash

    result = json.loads((work / "research-result.json").read_text(encoding="utf-8"))
    forged = result | {"request_id": "crypto:REQ-SOMEONE-ELSE"}
    raw = canonical(forged)
    result_file = work / "research-result.json"
    result_file.write_bytes(raw)
    with sqlite3.connect(env["state"] / "results.sqlite") as db:
        db.execute("UPDATE results SET result=?, content_hash=?", (raw, content_hash(forged)))
    code, lines = cli(env, "show", "crypto:REQ-CORRUPT-001")
    assert code == 5 and "inconsistent" in _only(lines)["reason"]


def test_fault_points_are_the_frozen_matrix():
    assert PROCESS_DEATH_POINTS == (
        "before_admission_commit",
        "after_admission",
        "during_materialization",
        "before_ops",
        "after_ops",
        "after_domain_effect",
        "during_result_write",
        "after_result_write",
        "after_result_store",
    )
    assert FAULT_POINTS[-3:] == ("ops_worker_crash", "ops_worker_hang", "ops_worker_slow")
    assert os.environ.get("CRIPTO_RESEARCH_FAULT") is None


def test_host_process_killed_during_ops_job_recovers_exactly_once(tmp_path):
    """Crash of the process hosting predictor_ops while the worker runs (killed from outside).

    Windows: the Ops job object kills the worker with its host. Linux: the worker survives
    as an orphan in its own session and may finish later; either way there must be one
    logical effect, one result and no second success reported by Ops for another effect.
    """
    import subprocess
    import sys
    import time

    env = build(tmp_path)
    path = write_request(env, "r", request("crypto:REQ-HOSTKILL-001"))
    environment = child_environment(CRIPTO_RESEARCH_FAULT="ops_worker_slow")
    host = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "GarimpoInvestimentos.research_runner",
            "--state",
            str(env["state"]),
            "process",
            "--policy",
            str(env["policy"]),
            "--objects",
            str(env["objects"]),
            str(path),
        ],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    ops_root = ops_runtime(env)
    deadline = time.monotonic() + 60
    while not list(ops_root.glob("crypto-research-*/heartbeat.json")):
        assert host.poll() is None and time.monotonic() < deadline, "job never started"
        time.sleep(0.05)
    time.sleep(0.5)
    host.kill()
    host.wait(30)
    code, lines = cli(env, "process", str(path))
    outcome = _only(lines)
    assert code == 0 and outcome["status"] == "RESULT"
    time.sleep(12)  # let a possible orphan worker (Linux) finish its slow run
    effects = list((experiments(env)).rglob("domain-effect.json"))
    assert len(effects) == 1
    stored = _only(cli(env, "show", "crypto:REQ-HOSTKILL-001")[1])["result"]
    assert (
        stored["domain_facts"]["effect_sha256"]
        == __import__("hashlib").sha256(effects[0].read_bytes()).hexdigest()
    )
    assert _results(env) == 1
    code, lines = cli(env, "process", str(path))
    assert code == 0 and _only(lines)["status"] == "DUPLICATE"
    code, lines = cli(env, "reconcile")
    assert code == 0 and _only(lines)["findings"] == []
