"""Domain instances of predictor-core scientific governance contracts."""

from __future__ import annotations

import json
from pathlib import Path

from predictor_core.contracts import DataAcquisitionCharter

ROOT = Path(__file__).resolve().parents[1]
FUNDING_OI_CHARTER = ROOT / "charters" / "funding_oi_v3.json"


def load_acquisition_charter(path: Path | str = FUNDING_OI_CHARTER) -> DataAcquisitionCharter:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid acquisition charter {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("acquisition charter root must be a JSON object")
    return DataAcquisitionCharter.from_dict(value)


__all__ = ["FUNDING_OI_CHARTER", "load_acquisition_charter"]
