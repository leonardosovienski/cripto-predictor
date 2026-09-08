"""Ensemble multi-sample do juiz LLM (LLM_ENSEMBLE_N).

Objetivo: reduzir a variância de uma única chamada (temperature=0.2) rodando N
amostras do MESMO prompt/provider e agregando por mediana — sem introduzir juiz
novo (mesmo provider/modelo/prompt) nem mudar o comportamento default (N=1
preserva a chamada única de sempre, byte a byte do contrato de retorno).
"""

import asyncio

import pytest


def _import_ai(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "GEMINIKEY-0123456789-abcdef")
    monkeypatch.setenv("SERP_API_KEY", "SERPKEY-0123456789-abcdef")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    import GarimpoInvestimentos.analyzers.ai_insights as ai

    return ai


# --- _aggregate_ensemble (unidade, sem rede) --------------------------------


def test_aggregate_ensemble_uses_median_and_closest_sample_for_text(monkeypatch):
    ai = _import_ai(monkeypatch)
    samples = [
        {"sentiment": "negativo", "summary": "a", "opportunity_score": 20, "llm_fallback": False},
        {"sentiment": "neutro", "summary": "b", "opportunity_score": 50, "llm_fallback": False},
        {"sentiment": "positivo", "summary": "c", "opportunity_score": 90, "llm_fallback": False},
    ]
    result = ai._aggregate_ensemble(samples)
    assert result["opportunity_score"] == 50
    assert result["sentiment"] == "neutro"  # amostra mais próxima da mediana
    assert result["summary"] == "b"
    assert result["llm_fallback"] is False
    assert result["ensemble_n"] == 3
    assert result["ensemble_samples_used"] == 3
    assert result["opportunity_score_std"] > 0


def test_aggregate_ensemble_ignores_fallback_samples_in_median(monkeypatch):
    ai = _import_ai(monkeypatch)
    samples = [
        {"sentiment": "positivo", "summary": "ok", "opportunity_score": 80, "llm_fallback": False},
        {"sentiment": "neutro", "summary": "erro", "opportunity_score": 50, "llm_fallback": True},
    ]
    result = ai._aggregate_ensemble(samples)
    assert result["opportunity_score"] == 80
    assert result["llm_fallback"] is False
    assert result["ensemble_n"] == 2
    assert result["ensemble_samples_used"] == 1
    assert result["opportunity_score_std"] == 0.0


def test_aggregate_ensemble_all_fallback_stays_fallback(monkeypatch):
    ai = _import_ai(monkeypatch)
    samples = [
        {"sentiment": "neutro", "summary": "erro", "opportunity_score": 50, "llm_fallback": True},
        {"sentiment": "neutro", "summary": "erro", "opportunity_score": 50, "llm_fallback": True},
    ]
    result = ai._aggregate_ensemble(samples)
    assert result["llm_fallback"] is True
    assert result["ensemble_n"] == 2
    assert result["ensemble_samples_used"] == 0


# --- analyze_asset com _analyze_once mockado (sem rede) ---------------------


def test_analyze_asset_n1_is_byte_identical_to_legacy_contract(monkeypatch):
    """Default LLM_ENSEMBLE_N=1: mesma chamada única, mesmo dict de sempre (sem
    chaves novas de ensemble) — ninguém que já lê o retorno pode notar diferença."""
    ai = _import_ai(monkeypatch)
    assert ai.settings.LLM_ENSEMBLE_N == 1

    calls = {"n": 0}

    async def fake_once(asset_name, prompt, provider):
        calls["n"] += 1
        return {
            "sentiment": "positivo",
            "summary": "ok",
            "opportunity_score": 77,
            "llm_fallback": False,
        }

    monkeypatch.setattr(ai, "_analyze_once", fake_once)
    result = asyncio.run(ai.analyze_asset("bitcoin", {}, []))
    assert calls["n"] == 1
    assert result == {
        "sentiment": "positivo",
        "summary": "ok",
        "opportunity_score": 77,
        "llm_fallback": False,
    }


def test_analyze_asset_ensemble_n3_calls_three_times_and_aggregates(monkeypatch):
    ai = _import_ai(monkeypatch)
    monkeypatch.setattr(ai.settings, "LLM_ENSEMBLE_N", 3)

    scores = iter([30, 50, 90])
    calls = {"n": 0}

    async def fake_once(asset_name, prompt, provider):
        calls["n"] += 1
        return {
            "sentiment": "neutro",
            "summary": f"amostra {calls['n']}",
            "opportunity_score": next(scores),
            "llm_fallback": False,
        }

    monkeypatch.setattr(ai, "_analyze_once", fake_once)
    result = asyncio.run(ai.analyze_asset("bitcoin", {}, []))
    assert calls["n"] == 3
    assert result["opportunity_score"] == 50
    assert result["ensemble_n"] == 3
    assert result["ensemble_samples_used"] == 3


@pytest.mark.parametrize("n", [0, -1])
def test_llm_ensemble_n_below_one_is_rejected(monkeypatch, n):
    monkeypatch.setenv("GEMINI_API_KEY", "GEMINIKEY-0123456789-abcdef")
    monkeypatch.setenv("SERP_API_KEY", "SERPKEY-0123456789-abcdef")
    monkeypatch.setenv("LLM_ENSEMBLE_N", str(n))
    from GarimpoInvestimentos.config import Settings

    with pytest.raises(ValueError, match="LLM_ENSEMBLE_N"):
        Settings()


# --- judge_signature reflete o ensemble -------------------------------------


def test_judge_signature_unchanged_when_n1(monkeypatch):
    ai = _import_ai(monkeypatch)
    assert ai.judge_signature().count(":") == 2  # provider:modelo:hash, sem 4º campo


def test_judge_signature_gains_ensemble_suffix_when_ngt1(monkeypatch):
    ai = _import_ai(monkeypatch)
    monkeypatch.setattr(ai.settings, "LLM_ENSEMBLE_N", 5)
    sig = ai.judge_signature()
    assert sig.endswith(":ensemble5")
    assert sig.count(":") == 3
