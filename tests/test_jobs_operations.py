from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest
from predictor_ops import JobConfig, RunStatus, run_job

from GarimpoInvestimentos import jobs
from GarimpoInvestimentos.v3 import daily


def _job(tmp_path: Path, code: str, *, timeout: float = 5, environment=None) -> JobConfig:
    return JobConfig(
        id="contract-job",
        command=[sys.executable, "-c", code],
        timeout_seconds=timeout,
        heartbeat_interval_seconds=0.05,
        environment=environment or {},
        runtime={"root": tmp_path, "lock_stale_after_seconds": 30},
    )


def test_public_job_config_uses_installed_module_and_no_checkout_cwd(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    config = jobs.job_config("watchdog", timeout_seconds=2)
    assert config.command[:2] == [sys.executable, "-m"]
    assert config.cwd is None
    assert config.runtime.root == tmp_path
    with pytest.raises(ValueError, match="unknown job"):
        jobs.job_config("invalid")


def test_v3_daily_is_supervised_and_stops_on_first_failed_step(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    assert jobs.job_config("v3-daily").command[-1] == "GarimpoInvestimentos.v3.daily"
    assert jobs.job_config("v3-daily").scientific_state == "COLLECTION_ONLY"
    planned = daily.commands(("BTCUSDT",), start_date="2021-01-01", end_date="2026-01-01")
    assert [command[2] for command in planned] == [
        "GarimpoInvestimentos.v3.vision_ingest",
        "GarimpoInvestimentos.v3.pipeline",
        "GarimpoInvestimentos.v3.paper_trader",
        "GarimpoInvestimentos.v3.paper_report",
    ]

    calls = []

    def fail_second(command, check):
        calls.append((command, check))
        return type("Completed", (), {"returncode": 7 if len(calls) == 2 else 0})()

    monkeypatch.setattr(daily.subprocess, "run", fail_second)
    assert daily.main() == 7
    assert len(calls) == 2


def test_job_cli_maps_operational_status(monkeypatch):
    succeeded = type("Result", (), {"run_status": RunStatus.SUCCEEDED, "exit_code": 0})()
    failed = type("Result", (), {"run_status": RunStatus.FAILED, "exit_code": 9})()
    monkeypatch.setattr(jobs, "execute_job", lambda *args, **kwargs: succeeded)
    assert jobs.main(["watchdog", "--timeout", "1"]) == 0
    monkeypatch.setattr(jobs, "execute_job", lambda *args, **kwargs: failed)
    assert jobs.main(["watchdog"]) == 9


def test_timeout_shutdown_heartbeat_events_and_redaction(tmp_path):
    secret = "synthetic-serp-secret-123456"
    leaking = _job(
        tmp_path,
        "import os,sys,time; print(os.environ['SERP_API_KEY']); print(os.environ['SERP_API_KEY'], file=sys.stderr); time.sleep(5)",
        timeout=1.0,
        environment={"SERP_API_KEY": secret},
    )
    result = run_job(leaking)
    assert result.exit_code == 124 and result.run_status == RunStatus.FAILED
    serialized = json.dumps(result.record)
    assert secret not in serialized and "[REDACTED]" in serialized
    root = tmp_path / leaking.id
    assert json.loads((root / "heartbeat.json").read_text())["run_status"] == "FAILED"
    assert secret not in (root / "events.jsonl").read_text()

    stop = threading.Event()
    stop.set()
    shutdown = run_job(_job(tmp_path, "import time; time.sleep(5)"), shutdown=stop)
    assert shutdown.exit_code == 130
    assert shutdown.record["termination"]["reason"] == "shutdown"


def test_lock_prevents_concurrent_duplicate(tmp_path):
    job = _job(tmp_path, "import time; time.sleep(0.5)")
    first: list = []
    thread = threading.Thread(target=lambda: first.append(run_job(job)))
    thread.start()
    time.sleep(0.1)
    second = run_job(job)
    thread.join()
    assert second.run_status == RunStatus.SKIPPED
    assert first[0].run_status == RunStatus.SUCCEEDED
