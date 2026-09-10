"""Health check da coleta prospectiva do juiz LLM (linha A: H5/H6, job `phase1`).

Motivação (auditoria 2026-08-19): a tabela `predictions` ficou zerada por dias
sem que ninguém percebesse — não porque faltasse o dado em si, mas porque não
existia NENHUM monitoramento dedicado a essa linha (o watchdog existente,
`observation_watchdog.py`, cobre só a família V3/microestrutura, que é
COLLECTION_ONLY). Este módulo espelha o mesmo padrão (heartbeat de
`predictor_ops.run_job` + violations + `emit_event`) para o job `phase1`.

Estado (`HEALTHY` / `DEGRADED` / `FAILED`) é conservador por design: qualquer
violação séria (job nunca rodou, nenhuma prediction real na janela esperada)
já é `FAILED`. Taxa de fallback alta ou heartbeat levemente atrasado é
`DEGRADED` — o pipeline ainda está vivo, mas merece atenção antes de virar
silêncio total como em agosto/2026.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.health_io import age_seconds, read_heartbeat
from GarimpoInvestimentos.trading.contracts import ensure_utc

# Cadência esperada: garimpo_fase1.py roda uma vez por dia UTC (run_daily.ps1 via
# Windows Task Scheduler, tarefa GarimpoFase1). Uma folga de 2x a cadência absorve
# um dia perdido isolado (rede, rate limit) sem gerar alarme; além disso é FAILED.
EXPECTED_CADENCE_HOURS = 24
STALE_AFTER_HOURS = EXPECTED_CADENCE_HOURS * 2  # 48h sem prediction real = FAILED
DEGRADED_AFTER_HOURS = EXPECTED_CADENCE_HOURS * 1.5  # 36h = DEGRADED
FALLBACK_RATE_DEGRADED = 0.30  # >30% de fallback nas últimas N previsões = DEGRADED
FALLBACK_RATE_WINDOW = 20  # últimas N linhas (fallback incluído) para a taxa acima


def _heartbeat(root: Path, job: str) -> dict | None:
    path = root / f"cripto-{job}" / "heartbeat.json"
    if not path.exists():
        return None
    return read_heartbeat(path)


def check_phase1_health(
    *, db_path: Path = FEATURE_STORE_DB, state_root: Path | None = None, now: datetime | None = None
) -> dict:
    """Retorna {'status': HEALTHY|DEGRADED|FAILED, 'violations': [...], ...}."""
    stamp = ensure_utc(now or datetime.now(UTC), "now")
    violations: list[str] = []
    degraded: list[str] = []

    configured_root = os.environ.get("PREDICTOR_OPS_STATE_DIR")
    root = state_root or (Path(configured_root) if configured_root else None)
    heartbeat = _heartbeat(root, "phase1") if root is not None else None

    if root is None:
        violations.append("state_root_not_configured")
    elif heartbeat is None:
        violations.append("phase1_heartbeat_missing")
    else:
        if heartbeat.get("run_status") not in {"SUCCEEDED", "PARTIAL"}:
            violations.append(f"phase1_run_status={heartbeat.get('run_status')}")
        finished = heartbeat.get("finished_at")
        if finished:
            elapsed = age_seconds(finished, stamp)
            age_hours = elapsed / 3600 if elapsed is not None else -1
            if age_hours < 0:
                violations.append("phase1_heartbeat_invalid_time")
            elif age_hours > STALE_AFTER_HOURS:
                violations.append(f"phase1_heartbeat_stale_{age_hours:.0f}h")
            elif age_hours > DEGRADED_AFTER_HOURS:
                degraded.append(f"phase1_heartbeat_aging_{age_hours:.0f}h")
        else:
            violations.append("phase1_heartbeat_missing_finished_at")

    last_real_ts: str | None = None
    fallback_rate: float | None = None
    n_recent = 0
    if not db_path.exists():
        violations.append("feature_store_missing")
    else:
        try:
            with closing(
                sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
            ) as connection:
                row = connection.execute(
                    "SELECT MAX(ts) FROM predictions WHERE COALESCE(llm_fallback, 0) = 0"
                ).fetchone()
                last_real_ts = row[0] if row else None

                recent = connection.execute(
                    "SELECT llm_fallback FROM predictions ORDER BY ts DESC LIMIT ?",
                    (FALLBACK_RATE_WINDOW,),
                ).fetchall()
                n_recent = len(recent)
                if n_recent:
                    n_fallback = sum(1 for r in recent if r[0] == 1)
                    fallback_rate = n_fallback / n_recent
                    if fallback_rate > FALLBACK_RATE_DEGRADED:
                        degraded.append(f"fallback_rate_{fallback_rate:.0%}_over_last_{n_recent}")

            if last_real_ts is None:
                violations.append("no_real_prediction_ever_recorded")
            else:
                age_hours = (
                    stamp - datetime.strptime(last_real_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
                ).total_seconds() / 3600
                if age_hours < 0:
                    violations.append("real_prediction_in_future")
                elif age_hours > STALE_AFTER_HOURS:
                    violations.append(f"no_real_prediction_in_{age_hours:.0f}h")
                elif age_hours > DEGRADED_AFTER_HOURS:
                    degraded.append(f"last_real_prediction_{age_hours:.0f}h_ago")
        except (sqlite3.DatabaseError, ValueError, TypeError):
            violations.append("feature_store_unreadable_or_invalid_timestamp")

    if violations:
        status = "FAILED"
    elif degraded:
        status = "DEGRADED"
    else:
        status = "HEALTHY"

    payload = {
        "checked_at": stamp.isoformat(),
        "status": status,
        "violations": violations,
        "degraded_signals": degraded,
        "last_successful_run": last_real_ts,
        "fallback_rate_recent": fallback_rate,
        "fallback_rate_window": n_recent,
    }
    emit_event(
        "previsao_cripto",
        "phase1.watchdog",
        metrics={"violation_count": len(violations), "degraded_count": len(degraded)},
        metadata=payload,
    )
    return payload


def main() -> int:
    result = check_phase1_health()
    print(json.dumps(result, sort_keys=True, default=str))
    return {"HEALTHY": 0, "DEGRADED": 1, "FAILED": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "check_phase1_health",
    "EXPECTED_CADENCE_HOURS",
    "STALE_AFTER_HOURS",
    "DEGRADED_AFTER_HOURS",
]
