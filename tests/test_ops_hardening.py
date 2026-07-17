"""Hardening operacional (triagem 2026-07-16/17): redação de segredos no log,
lock órfão auto-recuperável, idempotência por judge_signature completo e a API
pública FeatureStore.predictions_on. Offline, sem chaves reais."""
import importlib.util
import logging
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _load_fase1():
    spec = importlib.util.spec_from_file_location(
        "garimpo_fase1", ROOT / "scripts" / "garimpo_fase1.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fase1():
    return _load_fase1()


@pytest.fixture()
def store(tmp_path):
    from GarimpoInvestimentos.dpl import FeatureStore
    with FeatureStore(tmp_path / "fs.db") as s:
        yield s


def _pred(ativo, ts, juiz, fallback=0):
    return {"ativo": ativo, "ts": ts, "score": 55.0, "sentimento": "neutro",
            "resumo": "t", "price_usd": 1.0, "juiz": juiz, "divergencia": 0,
            "fonte": "direct", "input_degradado": 0, "llm_fallback": fallback}


# ---------------- FeatureStore.predictions_on ----------------

def test_predictions_on_filtra_dia_e_fallback(store):
    store.write_predictions([
        _pred("bitcoin", "2026-07-17T01:00:00Z", "gemini:m:abc"),
        _pred("ethereum", "2026-07-17T01:05:00Z", "groq:m:abc", fallback=1),
        _pred("solana", "2026-07-16T01:00:00Z", "mistral:m:abc"),
    ])
    pares = store.predictions_on("2026-07-17")
    assert pares == [("bitcoin", "gemini:m:abc")]  # fallback e outro dia ficam de fora


# ---------------- idempotência por assinatura completa ----------------

def test_judges_done_today_compara_assinatura_completa(fase1, store):
    store.write_predictions([
        _pred("bitcoin", "2026-07-17T01:00:00Z", "gemini:modelo-antigo:h1"),
    ])
    done = fase1.judges_done_today(store, "2026-07-17")
    assert ("bitcoin", "gemini:modelo-antigo:h1") in done
    # mesmo provedor com modelo/prompt diferente NÃO conta como coletado
    assert ("bitcoin", "gemini:modelo-novo:h2") not in done


def test_fallback_nao_conta_como_coletado(fase1, store):
    store.write_predictions([
        _pred("bitcoin", "2026-07-17T01:00:00Z", "gemini:m:h", fallback=1),
    ])
    assert fase1.judges_done_today(store, "2026-07-17") == set()


# ---------------- lock órfão ----------------

def test_lock_com_pid_morto_e_stale(fase1, tmp_path, monkeypatch):
    lock = tmp_path / "garimpo.lock"
    lock.write_text("pid=999999999 started=2026-07-17T00:00:00Z", encoding="utf-8")
    monkeypatch.setattr(fase1, "_pid_alive", lambda pid: False)
    assert fase1._lock_is_stale(lock) is True


def test_lock_com_pid_vivo_recente_nao_e_stale(fase1, tmp_path):
    lock = tmp_path / "garimpo.lock"
    lock.write_text(f"pid={os.getpid()} started=x", encoding="utf-8")
    assert fase1._lock_is_stale(lock) is False


def test_lock_velho_demais_e_stale_mesmo_com_pid_vivo(fase1, tmp_path):
    lock = tmp_path / "garimpo.lock"
    lock.write_text(f"pid={os.getpid()} started=x", encoding="utf-8")
    velho = time.time() - (fase1.STALE_LOCK_HOURS + 1) * 3600
    os.utime(lock, (velho, velho))
    assert fase1._lock_is_stale(lock) is True


def test_lock_corrompido_e_stale(fase1, tmp_path):
    lock = tmp_path / "garimpo.lock"
    lock.write_text("lixo sem pid", encoding="utf-8")
    assert fase1._lock_is_stale(lock) is True


def test_acquire_lock_assume_lock_orfao(fase1, tmp_path, monkeypatch):
    lock = tmp_path / "garimpo.lock"
    lock.write_text("pid=999999999 started=x", encoding="utf-8")
    monkeypatch.setattr(fase1, "LOCK_FILE", lock)
    monkeypatch.setattr(fase1, "_pid_alive", lambda pid: False)
    assert fase1.acquire_lock() is True
    assert f"pid={os.getpid()}" in lock.read_text(encoding="utf-8")


def test_acquire_lock_respeita_instancia_viva(fase1, tmp_path, monkeypatch):
    lock = tmp_path / "garimpo.lock"
    lock.write_text(f"pid={os.getpid()} started=x", encoding="utf-8")
    monkeypatch.setattr(fase1, "LOCK_FILE", lock)
    assert fase1.acquire_lock() is False


# ---------------- redação de segredos ----------------

def test_redact_filter_mascara_segredos(fase1):
    filt = fase1._RedactSecrets(["chave-super-secreta-123456"])
    rec = logging.LogRecord("httpx", logging.INFO, "x", 1,
                            "GET https://serpapi.com/search?api_key=chave-super-secreta-123456&q=btc",
                            None, None)
    assert filt.filter(rec) is True
    assert "chave-super-secreta-123456" not in rec.getMessage()
    assert "***" in rec.getMessage()


def test_redact_filter_ignora_segredos_curtos(fase1):
    # segredos < 8 chars não entram no filtro (evita mascarar texto legítimo)
    filt = fase1._RedactSecrets(["", "curto"])
    rec = logging.LogRecord("x", logging.INFO, "x", 1, "texto curto normal", None, None)
    filt.filter(rec)
    assert rec.getMessage() == "texto curto normal"
