import json
from datetime import UTC, datetime

from GarimpoInvestimentos.dpl import FeatureStore
from GarimpoInvestimentos.phase1_watchdog import check_phase1_health


def _write_heartbeat(root, job, *, run_status, finished_at):
    d = root / f"cripto-{job}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "heartbeat.json").write_text(
        json.dumps({"run_status": run_status, "finished_at": finished_at}),
        encoding="utf-8",
    )


def test_failed_quando_nunca_rodou(tmp_path):
    result = check_phase1_health(
        db_path=tmp_path / "missing.db",
        state_root=tmp_path / "ops",
        now=datetime(2026, 8, 19, tzinfo=UTC),
    )
    assert result["status"] == "FAILED"
    assert "phase1_heartbeat_missing" in result["violations"]
    assert "feature_store_missing" in result["violations"]
    assert result["last_successful_run"] is None


def test_healthy_com_heartbeat_recente_e_prediction_real(tmp_path):
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    _write_heartbeat(
        tmp_path / "ops", "phase1", run_status="SUCCEEDED", finished_at=now.isoformat()
    )
    db_path = tmp_path / "feature_store.db"
    with FeatureStore(str(db_path)) as store:
        store.write_predictions(
            [
                {
                    "ativo": "bitcoin",
                    "ts": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "score": 55.0,
                    "sentimento": "neutro",
                    "resumo": "ok",
                    "price_usd": 50000.0,
                    "juiz": "gemini",
                    "divergencia": 0,
                    "fonte": "direct",
                    "llm_fallback": 0,
                }
            ]
        )
    result = check_phase1_health(db_path=db_path, state_root=tmp_path / "ops", now=now)
    assert result["status"] == "HEALTHY"
    assert result["violations"] == []
    assert result["last_successful_run"] is not None


def test_failed_quando_ultima_prediction_real_e_muito_antiga(tmp_path):
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    _write_heartbeat(
        tmp_path / "ops", "phase1", run_status="SUCCEEDED", finished_at=now.isoformat()
    )
    db_path = tmp_path / "feature_store.db"
    with FeatureStore(str(db_path)) as store:
        store.write_predictions(
            [
                {
                    "ativo": "bitcoin",
                    "ts": "2026-08-01 00:00:00",  # 18 dias atras
                    "score": 55.0,
                    "sentimento": "neutro",
                    "resumo": "ok",
                    "price_usd": 50000.0,
                    "juiz": "gemini",
                    "divergencia": 0,
                    "fonte": "direct",
                    "llm_fallback": 0,
                }
            ]
        )
    result = check_phase1_health(db_path=db_path, state_root=tmp_path / "ops", now=now)
    assert result["status"] == "FAILED"
    assert any(v.startswith("no_real_prediction_in_") for v in result["violations"])


def test_degraded_quando_taxa_de_fallback_alta(tmp_path):
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    _write_heartbeat(
        tmp_path / "ops", "phase1", run_status="SUCCEEDED", finished_at=now.isoformat()
    )
    db_path = tmp_path / "feature_store.db"
    with FeatureStore(str(db_path)) as store:
        rows = []
        for i in range(10):
            rows.append(
                {
                    "ativo": f"asset{i}",
                    "ts": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "score": 50.0,
                    "sentimento": "neutro",
                    "resumo": "fallback aplicado" if i < 6 else "ok",
                    "price_usd": 50000.0,
                    "juiz": "gemini",
                    "divergencia": 0,
                    "fonte": "direct",
                    "llm_fallback": 1 if i < 6 else 0,
                }
            )
        store.write_predictions(rows)
    result = check_phase1_health(db_path=db_path, state_root=tmp_path / "ops", now=now)
    assert result["status"] == "DEGRADED"
    assert any(s.startswith("fallback_rate_") for s in result["degraded_signals"])


def test_emite_evento(tmp_path, monkeypatch):
    events = []
    monkeypatch.setattr(
        "GarimpoInvestimentos.phase1_watchdog.emit_event",
        lambda domain, event, **payload: events.append((event, payload)),
    )
    check_phase1_health(
        db_path=tmp_path / "missing.db",
        state_root=tmp_path / "ops",
        now=datetime(2026, 8, 19, tzinfo=UTC),
    )
    assert events[0][0] == "phase1.watchdog"
