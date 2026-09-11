"""Explicit process composition; no environment variable can relax analysis."""

import sys
from typing import Literal

Mode = Literal["analysis", "ingest"]
_mode: Mode = "analysis"


def selected_mode() -> Mode:
    return _mode


def select_mode(mode: Mode) -> None:
    global _mode
    module = sys.modules.get("GarimpoInvestimentos.config")
    if module is not None and module.settings.runtime_mode != mode:
        raise RuntimeError("runtime mode already initialized; start a new process")
    _mode = mode
