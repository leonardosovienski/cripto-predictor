"""Edge fault injection for qualification of the crypto research circuit.

Only active when CRIPTO_RESEARCH_FAULT names a point. In-process points end the real
process with os._exit (no cleanup, no finally blocks); worker points make the real
worker, running under predictor_ops, crash, hang or run slowly. Nothing here mocks
predictor_core or predictor_ops.
"""

from __future__ import annotations

import os
import sys

FAULT_ENV = "CRIPTO_RESEARCH_FAULT"
FAULT_EXIT = 86
# Points where the cripto-research process itself dies.
PROCESS_DEATH_POINTS = (
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
# Points injected into the worker supervised by predictor_ops.
WORKER_POINTS = ("ops_worker_crash", "ops_worker_hang", "ops_worker_slow")
FAULT_POINTS = PROCESS_DEATH_POINTS + WORKER_POINTS


def active() -> str | None:
    return os.environ.get(FAULT_ENV) or None


def fault(point: str) -> None:
    """A real, uncleaned process death at `point` when it is the configured fault."""
    if os.environ.get(FAULT_ENV) == point:
        sys.stderr.write(f"INJECTED_FAULT {point}\n")
        sys.stderr.flush()
        os._exit(FAULT_EXIT)


def worker_flag() -> list[str]:
    """Worker CLI flag for the configured worker fault (the worker never reads the env)."""
    return {
        "ops_worker_crash": ["--fault", "crash"],
        "ops_worker_hang": ["--fault", "hang"],
        "ops_worker_slow": ["--fault", "slow"],
    }.get(os.environ.get(FAULT_ENV, ""), [])


__all__ = [
    "FAULT_ENV",
    "FAULT_EXIT",
    "FAULT_POINTS",
    "PROCESS_DEATH_POINTS",
    "WORKER_POINTS",
    "active",
    "fault",
    "worker_flag",
]
