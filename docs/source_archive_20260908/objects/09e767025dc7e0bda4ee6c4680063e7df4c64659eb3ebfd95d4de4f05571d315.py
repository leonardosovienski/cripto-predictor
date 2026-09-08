"""Orçamento determinístico antes das bordas de rede da Fase 1.

Não tenta substituir o rate-limit do provedor. A finalidade é impedir que o
orquestrador inicie uma nova unidade lógica de trabalho depois do teto declarado.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.paths import DATA_DIR


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    reason: str


_BUDGET_DB = DATA_DIR / "api_guard_budget.db"
# Auditoria hostil 2026-07-17: API_GUARD_ENABLED tem default False (padrão de
# instalação nova), e o ramo "disabled" abaixo não emitia log nem evento
# algum — se ninguém setasse a env var, o orçamento nunca protegeu nada
# desde o início, e não havia como saber isso sem ler o .env ou o
# código-fonte. Este flag garante UM evento por processo (não um por
# chamada — allow() roda por ativo/provider, seria ruído) avisando que o
# guard está inativo.
_disabled_notice_emitted = False


def allow(stage: str, key: str, limit: int) -> GuardDecision:
    """Consome uma unidade somente se ela puder iniciar dentro do orçamento."""
    if not settings.API_GUARD_ENABLED or limit <= 0:
        global _disabled_notice_emitted
        if not _disabled_notice_emitted:
            emit_event(
                "previsao_cripto",
                "api_guard_disabled",
                metrics={},
                metadata={
                    "reason": "API_GUARD_ENABLED is false or limit<=0",
                    "stage": stage,
                    "key": key,
                },
            )
            _disabled_notice_emitted = True
        return GuardDecision(True, "disabled")
    bucket = datetime.now(UTC).strftime("%Y-%m-%d")
    path = Path(_BUDGET_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=30) as conn:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS api_budget ("
            "bucket TEXT NOT NULL, stage TEXT NOT NULL, guard_key TEXT NOT NULL, "
            "used INTEGER NOT NULL CHECK(used >= 0), "
            "PRIMARY KEY(bucket, stage, guard_key))"
        )
        # BEGIN IMMEDIATE serializa o read-check-increment entre processos.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT used FROM api_budget WHERE bucket=? AND stage=? AND guard_key=?",
            (bucket, stage, key),
        ).fetchone()
        used = int(row[0]) if row else 0
        if used >= limit:
            conn.rollback()
            return GuardDecision(False, f"budget_exhausted:{stage}:{key}")
        conn.execute(
            "INSERT INTO api_budget(bucket,stage,guard_key,used) VALUES(?,?,?,1) "
            "ON CONFLICT(bucket,stage,guard_key) DO UPDATE SET used=used+1",
            (bucket, stage, key),
        )
        conn.commit()
    return GuardDecision(True, "allowed")


def reset_for_test() -> None:
    path = Path(_BUDGET_DB)
    if path.exists():
        with sqlite3.connect(path) as conn:
            conn.execute("DELETE FROM api_budget")
            conn.commit()
    global _disabled_notice_emitted
    _disabled_notice_emitted = False
