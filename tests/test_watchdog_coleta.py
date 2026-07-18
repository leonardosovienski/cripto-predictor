"""Watchdog da coleta H5 — regressão da contagem de previsões do dia.

Bug (auditoria 2026-07-18): o watchdog contava TODAS as linhas de predictions
do dia, inclusive fallback do LLM (llm_fallback=1). Uma execução manual de
main.py que persistisse fallbacks no mesmo dia de uma coleta noturna falhada
mascararia o alerta (n>0 falso). A contagem agora usa a MESMA semântica de
FeatureStore.predictions_on: só previsão real conta como coleta.
Offline, sem chaves reais, sem tocar o feature_store.db de produção.
"""
import importlib.util
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _load_watchdog():
    spec = importlib.util.spec_from_file_location(
        "watchdog_coleta", ROOT / "scripts" / "watchdog_coleta.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def watchdog():
    return _load_watchdog()


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "fs.db"
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE predictions (
        ativo TEXT, ts TEXT, score REAL, juiz TEXT, llm_fallback INTEGER,
        PRIMARY KEY (ativo, ts))""")
    con.commit()
    con.close()
    return path


def _insert(path, rows):
    con = sqlite3.connect(path)
    con.executemany(
        "INSERT INTO predictions (ativo, ts, score, juiz, llm_fallback) "
        "VALUES (?,?,?,?,?)", rows)
    con.commit()
    con.close()


def test_fallback_nao_conta_como_previsao_do_dia(watchdog, db):
    _insert(db, [
        ("bitcoin", "2026-07-18 01:00:00", 55.0, "gemini:m:h", 0),
        ("ethereum", "2026-07-18 01:05:00", 50.0, "groq:m:h", 1),   # fallback
        ("solana", "2026-07-18 01:10:00", 50.0, "mistral:m:h", 1),  # fallback
    ])
    n, juizes = watchdog.contagem_previsoes_reais(db, "2026-07-18")
    assert (n, juizes) == (1, 1)


def test_dia_so_com_fallback_e_tratado_como_zero(watchdog, db):
    # Cenário do bug: coleta noturna falhou; um run manual gravou só fallbacks.
    _insert(db, [
        ("bitcoin", "2026-07-18 12:00:00", 50.0, "gemini:m:h", 1),
        ("ethereum", "2026-07-18 12:01:00", 50.0, "groq:m:h", 1),
    ])
    assert watchdog.contagem_previsoes_reais(db, "2026-07-18") == (0, 0)


def test_legado_com_llm_fallback_null_conta_como_real(watchdog, db):
    # Linhas pré-migração-0009 têm llm_fallback NULL — semântica de predictions_on:
    # COALESCE(NULL,0)=0 → contam como reais (nunca reinterpretar o legado).
    _insert(db, [
        ("bitcoin", "2026-07-18 01:00:00", 60.0, "gemini:m:h", None),
        ("ethereum", "2026-07-18 01:05:00", 40.0, "groq:m:h", None),
    ])
    assert watchdog.contagem_previsoes_reais(db, "2026-07-18") == (2, 2)


def test_outro_dia_fica_de_fora(watchdog, db):
    _insert(db, [
        ("bitcoin", "2026-07-17 01:00:00", 55.0, "gemini:m:h", 0),
    ])
    assert watchdog.contagem_previsoes_reais(db, "2026-07-18") == (0, 0)
