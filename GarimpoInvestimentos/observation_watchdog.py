"""Operational watchdog for the Binance COLLECTION_ONLY observation."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.dpl.derivatives import SOURCE
from GarimpoInvestimentos.governance import load_observation_plan
from GarimpoInvestimentos.health_io import age_seconds, read_heartbeat
from GarimpoInvestimentos.trading.contracts import ensure_utc


def check_observation_health(
    *, db_path: Path = FEATURE_STORE_DB, state_root: Path | None = None, now: datetime | None = None
) -> dict:
    stamp = ensure_utc(now or datetime.now(UTC), "now")
    configured = os.environ.get("PREDICTOR_OPS_STATE_DIR")
    root = state_root or (
        Path(configured) if configured else FEATURE_STORE_DB.parent / "unconfigured-ops"
    )
    heartbeat_path = root / "cripto-v3-daily" / "heartbeat.json"
    violations: list[str] = []
    if state_root is None and not configured:
        violations.append("state_root_not_configured")
    heartbeat = None
    heartbeat = read_heartbeat(heartbeat_path)
    if heartbeat is not None:
        if heartbeat.get("run_status") not in {"SUCCEEDED", "PARTIAL"}:
            violations.append("v3_daily_unsuccessful")
        if heartbeat.get("scientific_state") != "COLLECTION_ONLY":
            violations.append("scientific_state_changed")
        finished = heartbeat.get("finished_at")
        if (elapsed := age_seconds(finished, stamp)) is None or not 0 <= elapsed <= 36 * 3600:
            violations.append("v3_daily_heartbeat_stale")
    else:
        violations.append("v3_daily_heartbeat_missing")

    live_path = root / "cripto-observation-live" / "heartbeat.json"
    live = read_heartbeat(live_path)
    if live is not None:
        if live.get("run_status") not in {"WAITING", "SUCCEEDED", "PARTIAL"}:
            violations.append("live_collection_unsuccessful")
        if live.get("scientific_state") != "COLLECTION_ONLY":
            violations.append("live_scientific_state_changed")
        heartbeat_at = live.get("heartbeat_at")
        if (elapsed := age_seconds(heartbeat_at, stamp)) is None or not 0 <= elapsed <= 600:
            violations.append("live_collection_stale")
    else:
        violations.append("live_collection_heartbeat_missing")

    plan = load_observation_plan()
    day = (stamp - timedelta(days=1)).date().isoformat()
    states = {}
    if db_path.exists():
        try:
            with closing(
                sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
            ) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute(
                    """SELECT metric, state, scientific_state FROM observation_scorecards
                       WHERE plan_id=? AND source=? AND substr(window_start,1,10)=?""",
                    (plan.plan_id, SOURCE, day),
                ).fetchall()
            states = {row["metric"]: row["state"] for row in rows}
            if any(row["scientific_state"] != "COLLECTION_ONLY" for row in rows):
                violations.append("scorecard_scientific_state_changed")
            if set(states) != {"funding_rate", "open_interest"}:
                violations.append("daily_scorecards_missing")
            if "QUARANTINED" in states.values():
                violations.append("source_quarantined")
            elif any(state != "HEALTHY" for state in states.values()):
                violations.append("source_degraded")
        except sqlite3.DatabaseError:
            violations.append("feature_store_unreadable")

    else:
        violations.append("feature_store_missing")
    payload = {
        "checked_at": stamp.isoformat(),
        "day": day,
        "healthy": not violations,
        "violations": violations,
        "scorecard_states": states,
        "scientific_state": "COLLECTION_ONLY",
    }
    emit_event(
        "v3_cripto",
        "observation.watchdog",
        metrics={"violation_count": len(violations)},
        metadata=payload,
    )
    return payload


def main() -> int:
    result = check_observation_health()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["check_observation_health"]
