"""Operational entrypoints implemented with predictor_ops public APIs."""

from __future__ import annotations

import argparse
import os
import sys
import threading
from collections.abc import Sequence
from pathlib import Path

from platformdirs import user_state_path
from predictor_ops import JobConfig, RunResult, RunStatus, run_job

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB


def _state_root() -> Path:
    configured = os.getenv("PREDICTOR_OPS_STATE_DIR")
    return (
        Path(configured).expanduser().resolve()
        if configured
        else user_state_path("cripto-predictor")
    )


def job_config(name: str, *, timeout_seconds: float | None = None) -> JobConfig:
    commands = {
        "phase1": [sys.executable, "-m", "GarimpoInvestimentos.phase1"],
        "backtest": [sys.executable, "-m", "GarimpoInvestimentos.analyzers.backtest"],
        "watchdog": [sys.executable, "-m", "GarimpoInvestimentos.watchdog"],
        "v3-daily": [sys.executable, "-m", "GarimpoInvestimentos.v3.daily"],
        "observation-daily": [sys.executable, "-m", "GarimpoInvestimentos.observation_quality"],
    }
    if name not in commands:
        raise ValueError(f"unknown job: {name}")
    artifact = FEATURE_STORE_DB if name in {"phase1", "backtest"} else None
    return JobConfig(
        id=f"cripto-{name}",
        command=commands[name],
        timeout_seconds=timeout_seconds or (252_000 if name == "phase1" else 1_800),
        heartbeat_interval_seconds=5,
        expected_artifact=artifact,
        provenance={"domain": "crypto", "scientific_change": False},
        scientific_state="COLLECTION_ONLY" if name in {"v3-daily", "observation-daily"} else None,
        runtime={"backend": "local", "root": _state_root(), "lock_stale_after_seconds": 86_400},
    )


def execute_job(
    name: str, *, timeout_seconds: float | None = None, shutdown: threading.Event | None = None
) -> RunResult:
    return run_job(job_config(name, timeout_seconds=timeout_seconds), shutdown=shutdown)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run cripto-predictor jobs via predictor_ops")
    parser.add_argument(
        "job", choices=("phase1", "backtest", "watchdog", "v3-daily", "observation-daily")
    )
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args(argv)
    result = execute_job(args.job, timeout_seconds=args.timeout)
    return 0 if result.run_status in {RunStatus.SUCCEEDED, RunStatus.PARTIAL} else result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
