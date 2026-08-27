"""Replay deterministico de falhas que ja ocorreram ou quase invalidaram o projeto.

Esta suite nao chama rede nem usa o banco real. Cada caso verifica simultaneamente
o erro esperado e uma invariante pos-falha (status, artefato ou ledger preservado).
Rode com: ``pytest -q tests/test_failure_replay.py``.
"""

from __future__ import annotations

import asyncio
import math
import sqlite3
import sys
import types

import pytest
from predictor_ops import JobConfig, RunStatus, run_job

from GarimpoInvestimentos import quality_snapshot
from GarimpoInvestimentos.analyzers import prefilter
from GarimpoInvestimentos.config import Settings
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.hash_chain import seal_chain, verify_chain
from GarimpoInvestimentos.v3.backtest_v3 import _find_spot_return
from scripts.feature_store_backup import create_backup, verify_backup


def _snap(n: int, *, verdict: str | None) -> dict:
    return {
        "checked_at": "2026-08-27T00:00:00+00:00",
        "h6": {"n": n, "veredito": verdict} if verdict is not None else None,
        "h6_power": None,
        "sample": {
            "h6_valid_n": n,
            "h6_gate": 30,
            "h6_fonte_esperada": "dpl:fallback",
        },
    }


def _prediction(ts: str = "2026-08-20 12:00:00") -> dict:
    return {
        "ativo": "bitcoin",
        "ts": ts,
        "score": 70.0,
        "sentimento": "positivo",
        "resumo": "failure-replay",
        "price_usd": 100_000.0,
        "juiz": "gemini:test:hash",
        "divergencia": 0,
        "fonte": "direct",
        "input_degradado": 0,
        "llm_fallback": 0,
        "news_provider": "serpapi",
        "news_degraded_reason": None,
        "collection_policy": None,
    }


def test_replay_provider_digitado_errado_para_antes_da_rede():
    with pytest.raises(ValueError, match="LLM_MULTI_PROVIDERS"):
        Settings(
            _env_file=None,
            LLM_PROVIDER="multi",
            LLM_MULTI_PROVIDERS="gemini,grok",
            GEMINI_API_KEY="synthetic-gemini-key-long-enough",
            SERP_API_KEY="synthetic-serp-key-long-enough",
        )


def test_replay_todos_os_ingests_falham_nao_produz_sucesso_vazio(tmp_path, monkeypatch):
    # O CLI importa o exportador XLSX avidamente, mas ingestao nao o usa. Isola
    # esse extra para que o replay continue executavel numa instalacao sem Excel.
    reporter = types.ModuleType("GarimpoInvestimentos.output.reporter")
    reporter.export_results = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "GarimpoInvestimentos.output.reporter", reporter)
    sys.modules.pop("GarimpoInvestimentos.main", None)
    from GarimpoInvestimentos import main as app_main

    class EmptyStore:
        def __init__(self, _path):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    async def offline(*_args, **_kwargs):
        raise TimeoutError("provider offline")

    async def no_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(app_main, "FEATURE_STORE_DB", tmp_path / "never-written.db")
    monkeypatch.setattr(app_main, "FeatureStore", EmptyStore)
    monkeypatch.setattr(app_main, "CryptoDataProvider", lambda **_kwargs: object())
    monkeypatch.setattr(app_main, "FearAndGreedProvider", lambda: object())
    monkeypatch.setattr(app_main, "ingest_crypto", offline)
    monkeypatch.setattr(app_main.asyncio, "sleep", no_sleep)

    with pytest.raises(RuntimeError, match="nenhum ativo"):
        asyncio.run(app_main.run_ingest(["bitcoin", "ethereum"]))
    assert not (tmp_path / "never-written.db").exists()


def test_replay_timeout_de_job_e_failed_e_preserva_artefato(tmp_path):
    scientific = tmp_path / "h6_status.json"
    original = '{"n":31,"veredito":"VALIDADO"}\n'
    scientific.write_text(original, encoding="utf-8")
    cfg = JobConfig(
        id="failure-replay-timeout",
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        timeout_seconds=0.25,
        heartbeat_interval_seconds=0.05,
        runtime={"root": tmp_path / "ops", "lock_stale_after_seconds": 30},
    )
    result = run_job(cfg)
    assert result.exit_code == 124
    assert result.run_status is RunStatus.FAILED
    assert scientific.read_text(encoding="utf-8") == original


def test_replay_h6_nunca_regride_estado_publicado(tmp_path):
    status = tmp_path / "h6_status.json"
    quality_snapshot.write_h6_status(_snap(31, verdict="VALIDADO"), status)
    before = status.read_bytes()
    result = quality_snapshot.write_h6_status(_snap(0, verdict=None), status)
    assert result == quality_snapshot.H6_REFUSED_REGRESSION
    assert status.read_bytes() == before


def test_replay_candle_futuro_mais_proximo_continua_invisivel():
    hour = 3_600_000
    # O close 1000 da vela aberta em t esta mais perto, mas so existe em t+1h.
    spot = {hour: 100.0, 2 * hour: 1_000.0, 3 * hour: 110.0}
    got = _find_spot_return(2 * hour, 2, spot)
    assert got == pytest.approx(math.log(110.0 / 100.0))


def test_replay_bypass_de_schema_ainda_e_detectado_pela_cadeia(tmp_path):
    with FeatureStore(tmp_path / "ledger.db") as store:
        store.write_predictions([_prediction(), _prediction("2026-08-21 12:00:00")])
        assert seal_chain(store._conn) == 2
        for trigger in (
            "predictions_archive_block_update",
            "predictions_archive_block_delete",
            "predictions_archive_chain_block_update",
            "predictions_archive_chain_block_delete",
        ):
            store._conn.execute(f"DROP TRIGGER {trigger}")
        store._conn.execute(
            "UPDATE predictions_archive SET score=999 WHERE archive_id=1"
        )
        report = verify_chain(store._conn)
        assert not report.ok
        assert report.first_bad_archive_id == 1
        with pytest.raises(RuntimeError, match="selo recusado"):
            seal_chain(store._conn)


def test_replay_backup_com_wal_ativo_inclui_commit_e_verifica(tmp_path):
    database = tmp_path / "live.db"
    writer = sqlite3.connect(database)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE observations (id INTEGER PRIMARY KEY, value REAL)")
    writer.execute("INSERT INTO observations VALUES (1, 1.0)")
    writer.commit()
    try:
        writer.execute("INSERT INTO observations VALUES (2, 2.0)")
        writer.commit()
        backup = create_backup(tmp_path / "backup", database=database)
    finally:
        writer.close()
    verify_backup(backup)
    restored = sqlite3.connect(backup / "feature_store.db")
    try:
        assert restored.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 2
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        restored.close()


def test_replay_prefiltro_ativo_exclui_dado_ausente_com_motivo(monkeypatch):
    monkeypatch.setattr(prefilter.settings, "LLM_PREFILTER_ENABLED", True)
    monkeypatch.setattr(prefilter.settings, "LLM_PREFILTER_MIN_VOLUME_USD", 10_000_000)
    decision = prefilter.decide({"change_7d": 8.0, "indicadores": {}})
    assert not decision.selected
    assert decision.reason == "low_or_missing_volume"
