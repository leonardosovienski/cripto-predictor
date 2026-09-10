"""Read-only heartbeat decoding and strict clock validation for health reports."""

from datetime import datetime
from pathlib import Path

from GarimpoInvestimentos.durable_io import strict_json_loads
from GarimpoInvestimentos.trading.contracts import ensure_utc


def read_heartbeat(path: Path) -> dict | None:
    try:
        value = strict_json_loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def age_seconds(value: object, now: datetime) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        stamp = ensure_utc(datetime.fromisoformat(value), "heartbeat time")
        return (now - stamp).total_seconds()
    except (TypeError, ValueError):
        return None
