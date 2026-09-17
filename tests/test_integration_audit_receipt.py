"""Failure receipts preserve successful subchecks without greenwashing the run."""

import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/integration_audit_receipt.py"
summarize = runpy.run_path(str(SCRIPT))["summarize"]


def write_receipts(work, *, expired=False, completed=False):
    work.mkdir(exist_ok=True)
    records = [{"name": "crypto-wheel-contract", "exit_code": 0, "expected_exit": 0}]
    if expired:
        raw = (
            b"ECOSYSTEM_DRIFT_DETECTED (OFFLINE): 1\n"
            b"  - brasileirao-predictor: atestado venceu em 2026-09-13T16:42:06Z e segue ALIGNED\n"
        )
        (work / "logs").mkdir()
        (work / "logs/ecosystem-offline.log").write_bytes(raw)
        records.append(
            {
                "name": "ecosystem-offline",
                "exit_code": 1,
                "expected_exit": 0,
                "log": "logs/ecosystem-offline.log",
                "log_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    (work / "commands.json").write_text(json.dumps(records))
    if completed:
        (work / "result.json").write_text('{"status": "PASS"}')


def test_expiration_preserves_contract_success_and_global_failure(tmp_path):
    write_receipts(tmp_path, expired=True)
    result = summarize(tmp_path, 1)
    assert result["overall"] == "FAIL"
    assert result["checks"][0]["status"] == "PASS"
    assert result["checks"][1]["status"] == "FAIL"
    assert result["current_validity"] == "BLOCKED_EXPIRED_ATTESTATION"
    assert len(result["expired_attestation_reports"]) == 1
    assert result["economic_validation"] is False


def test_process_success_without_completion_is_not_approval(tmp_path):
    write_receipts(tmp_path)
    assert summarize(tmp_path, 0)["overall"] == "FAIL"


def test_complete_success_does_not_assert_economic_or_current_validity(tmp_path):
    write_receipts(tmp_path, completed=True)
    result = summarize(tmp_path, 0)
    assert result["overall"] == "PASS"
    assert result["current_validity"] == "NOT_DETERMINED"
    assert result["economic_validation"] is False


def test_modified_log_is_rejected(tmp_path):
    write_receipts(tmp_path, expired=True)
    (tmp_path / "logs/ecosystem-offline.log").write_text("replacement")
    with pytest.raises(ValueError, match="digest mismatch"):
        summarize(tmp_path, 1)


def test_external_log_path_is_rejected(tmp_path):
    write_receipts(tmp_path, expired=True)
    records = json.loads((tmp_path / "commands.json").read_text())
    records[-1]["log"] = "../outside.log"
    (tmp_path / "commands.json").write_text(json.dumps(records))
    with pytest.raises(ValueError, match="outside"):
        summarize(tmp_path, 1)


def test_wrapper_preserves_actual_child_failure_code(tmp_path):
    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    wrapper = root / "scripts/integration_audit_receipt.py"
    wrapper.write_bytes(SCRIPT.read_bytes())
    child = root / ".ci/integration-audit/validate.py"
    child.parent.mkdir(parents=True)
    child.write_text("raise SystemExit(7)\n")
    work = tmp_path / "execution"
    run = subprocess.run(
        [sys.executable, str(wrapper), "--crypto-sha", "test", "--work", str(work)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert run.returncode == 7
    receipt = json.loads((work / "remediation-summary.json").read_text())
    assert receipt["overall"] == "FAIL"
    assert receipt["process_exit_code"] == 7
    second = subprocess.run(
        [sys.executable, str(wrapper), "--crypto-sha", "test", "--work", str(work)],
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert second.returncode != 0
    assert json.loads((work / "remediation-summary.json").read_text()) == receipt
