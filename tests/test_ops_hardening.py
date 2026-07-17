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


# ---------------- ordenação anti-buraco do api_guard ----------------

def test_order_by_staleness_prioriza_mais_antigo_e_nunca_previsto(fase1, store):
    store.write_predictions([
        _pred("bitcoin", "2026-07-16T01:00:00Z", "gemini:m:h"),
        _pred("ethereum", "2026-07-10T01:00:00Z", "groq:m:h"),
    ])
    ordem = fase1.order_by_staleness(["bitcoin", "ethereum", "solana"], store)
    # solana nunca prevista vem primeiro; depois a previsão mais antiga (ethereum)
    assert ordem == ["solana", "ethereum", "bitcoin"]


def test_order_by_staleness_ignora_fallback(fase1, store):
    # fallback não conta como previsão real: ativo só-com-fallback = nunca previsto
    store.write_predictions([
        _pred("bitcoin", "2026-07-16T01:00:00Z", "gemini:m:h", fallback=1),
        _pred("ethereum", "2026-07-10T01:00:00Z", "groq:m:h"),
    ])
    ordem = fase1.order_by_staleness(["ethereum", "bitcoin"], store)
    assert ordem == ["bitcoin", "ethereum"]


# ---------------- paridade simulação x prefiltro canônico ----------------

def test_prefilter_simulation_parity(monkeypatch):
    """A régua paramétrica do simulate_prefilter deve decidir IGUAL ao
    prefilter.decide() canônico com os mesmos thresholds — senão a calibração
    retroativa mente."""
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location("simulate_prefilter", ROOT / "scripts" / "simulate_prefilter.py")
    sim = _ilu.module_from_spec(spec)
    spec.loader.exec_module(sim)

    from GarimpoInvestimentos.analyzers import prefilter
    from GarimpoInvestimentos.analyzers.score_engine import technical_direction
    from GarimpoInvestimentos.config import settings

    monkeypatch.setattr(settings, "LLM_PREFILTER_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PREFILTER_MIN_VOLUME_USD", 10_000_000.0)
    monkeypatch.setattr(settings, "LLM_PREFILTER_MIN_ABS_CHANGE_7D", 2.0)

    casos = [
        {},  # sem nada -> low_or_missing_volume
        {"volume_usd": 5e6, "change_7d": 9.0},
        {"volume_usd": 5e7},  # sem change_7d
        {"volume_usd": 5e7, "change_7d": 0.5},
        {"volume_usd": 5e7, "change_7d": 9.0},  # sem indicadores -> neutral/missing
        {"volume_usd": 5e7, "change_7d": 9.0,
         "indicadores": {"preco_vs_sma200_pct": 5.0, "macd_histogram": 1.0}},
        {"volume_usd": 5e7, "change_7d": -9.0,
         "indicadores": {"preco_vs_sma200_pct": -5.0, "macd_histogram": -1.0}},
        {"volume_usd": 5e7, "change_7d": 9.0,
         "indicadores": {"preco_vs_sma200_pct": 5.0, "macd_histogram": -1.0}},  # neutro
    ]
    for hard in casos:
        canonico = prefilter.decide(hard)
        simulado = sim.simulate_decision(hard, 10_000_000.0, 2.0, technical_direction)
        assert (simulado == "selected") == canonico.selected, hard
        if not canonico.selected:
            assert simulado == canonico.reason, hard
