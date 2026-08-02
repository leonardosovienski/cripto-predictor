"""Configurable runtime paths; defaults never write inside an installed wheel."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_cache_path, user_data_path, user_log_path


def _configured(primary: str, legacy: str, default: Path) -> Path:
    raw = os.getenv(primary) or os.getenv(legacy)
    return Path(raw).expanduser().resolve() if raw else default.resolve()


DATA_DIR = _configured("DATA_DIR", "GARIMPO_DATA_DIR", user_data_path("cripto-predictor"))
OUTPUT_DIR = _configured("OUTPUT_DIR", "GARIMPO_OUTPUT_DIR", DATA_DIR / "output")
CACHE_DIR = _configured("CACHE_DIR", "GARIMPO_CACHE_DIR", user_cache_path("cripto-predictor"))
LOGS_DIR = _configured("LOGS_DIR", "GARIMPO_LOGS_DIR", user_log_path("cripto-predictor"))

for directory in (DATA_DIR, OUTPUT_DIR, CACHE_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

FEATURE_STORE_DB = OUTPUT_DIR / "feature_store.db"
