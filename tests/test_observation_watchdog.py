import json
from datetime import UTC, datetime

from GarimpoInvestimentos.observation_watchdog import check_observation_health


def test_watchdog_fails_closed_when_collection_has_not_started(tmp_path, monkeypatch):
    events = []
    monkeypatch.setattr(
        "GarimpoInvestimentos.observation_watchdog.emit_event",
        lambda domain, event, **payload: events.append((event, payload)),
    )
    result = check_observation_health(
        db_path=tmp_path / "missing.db",
        state_root=tmp_path / "ops",
        now=datetime(2026, 8, 8, tzinfo=UTC),
    )
    assert result["healthy"] is False
    assert result["violations"] == ["v3_daily_heartbeat_missing", "feature_store_missing"]
    assert events[0][0] == "observation.watchdog"


def test_watchdog_rejects_non_collection_only_heartbeat(tmp_path):
    root = tmp_path / "ops" / "cripto-v3-daily"
    root.mkdir(parents=True)
    now = datetime(2026, 8, 8, tzinfo=UTC)
    (root / "heartbeat.json").write_text(
        json.dumps(
            {
                "run_status": "SUCCEEDED",
                "scientific_state": "SHADOW",
                "finished_at": now.isoformat(),
            }
        ),
        encoding="utf-8",
    )
    result = check_observation_health(
        db_path=tmp_path / "missing.db",
        state_root=tmp_path / "ops",
        now=now,
    )
    assert "scientific_state_changed" in result["violations"]
