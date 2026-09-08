"""Operational watchdog for the Binance COLLECTION_ONLY observation."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.dpl.derivatives import SOURCE
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.governance import load_observation_plan


def check_observation_health(
    *, db_path: Path = FEATURE_STORE_DB, state_root: Path | None = None, now: datetime | None = None
) -> dict:
    stamp = now or datetime.now(UTC)
    root = state_root or Path(os.environ["PREDICTOR_OPS_STATE_DIR"])
    heartbeat_path = root / "cripto-v3-daily" / "heartbeat.json"
    violations: list[str] = []
    heartbeat = None
    if heartbeat_path.exists():
        heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        if heartbeat.get("run_status") not in {"SUCCEEDED", "PARTIAL"}:
            violations.append("v3_daily_unsuccessful")
        if heartbeat.get("scientific_state") != "COLLECTION_ONLY":
            violations.append("scientific_state_changed")
        finished = heartbeat.get("finished_at")
        if not finished or stamp - datetime.fromisoformat(finished) > timedelta(hours=36):
            violations.append("v3_daily_heartbeat_stale")
    else:
        violations.append("v3_daily_heartbeat_missing")

    live_path = root / "cripto-observation-live" / "heartbeat.json"
    if live_path.exists():
        live = json.loads(live_path.read_text(encoding="utf-8"))
        if live.get("run_status") not in {"WAITING", "SUCCEEDED", "PARTIAL"}:
            violations.append("live_collection_unsuccessful")
        if live.get("scientific_state") != "COLLECTION_ONLY":
            violations.append("live_scientific_state_changed")
        heartbeat_at = live.get("heartbeat_at")
        if not heartbeat_at or stamp - datetime.fromisoformat(heartbeat_at) > timedelta(minutes=10):
            violations.append("live_collection_stale")
    else:
        violations.append("live_collection_heartbeat_missing")

    plan = load_observation_plan()
    day = (stamp - timedelta(days=1)).date().isoformat()
    states = {}
    if db_path.exists():
        with FeatureStore(db_path) as store:
            rows = store._conn.execute(
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
