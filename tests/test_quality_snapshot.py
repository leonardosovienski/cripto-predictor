"""Painel de qualidade: engenharia vs amostra científica não devem se confundir.

Cobre especificamente o ponto levantado na auditoria de 2026-08-19: previsões
recém-gravadas (mesmo dia, sem preço realizado ainda) NÃO podem aparecer como
maduras, e a contagem de "H6 valid n" tem que vir da mesma função que fecha o
veredito oficial (h6_spearman_verdict), não de uma reimplementação do filtro.
"""

from datetime import UTC, datetime

import pytest

from GarimpoInvestimentos import quality_snapshot
from GarimpoInvestimentos.dpl import FeatureStore


def _row(ativo, ts, score, juiz, fonte="dpl:fallback", price=50000.0):
    return {
        "ativo": ativo,
        "ts": ts,
        "score": score,
        "sentimento": "neutro",
        "resumo": "ok",
        "price_usd": price,
        "juiz": juiz,
        "divergencia": 0,
        "fonte": fonte,
        "llm_fallback": 0,
    }


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "feature_store.db"
    monkeypatch.setattr("GarimpoInvestimentos.analyzers.backtest.FEATURE_STORE_DB", path)
    return path


def test_snapshot_com_banco_vazio(db_path):
    import asyncio

    with FeatureStore(db_path):
        pass  # só cria o schema

    snap = asyncio.run(quality_snapshot.build_snapshot())
    assert snap["sample"]["total_predictions"] == 0
    assert snap["sample"]["mature_d1"] == 0
    assert snap["sample"]["h6_valid_n"] == 0
    # não deve quebrar a renderização com amostra vazia
    text = quality_snapshot.render(snap)
    assert "PROJECT QUALITY SNAPSHOT" in text
    assert "NOT_AVAILABLE" in text


def test_previsao_do_mesmo_dia_nao_conta_como_madura(db_path):
    import asyncio

    now = datetime.now(UTC)
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    with FeatureStore(db_path) as store:
        store.write_predictions([_row("bitcoin", ts, 55.0, "mistral:mistral-small-latest:hash")])

    snap = asyncio.run(quality_snapshot.build_snapshot(now=now))
    assert snap["sample"]["total_predictions"] == 1
    assert snap["pipeline"]["predictions_today"] == 1
    # a previsão é de agora — D+1 ainda não existe, não pode aparecer madura
    assert snap["sample"]["mature_d1"] == 0
    assert snap["sample"]["h6_valid_n"] == 0
    assert snap["predictive_quality"]["accuracy_d1"] is None


def test_fallback_do_llm_nao_entra_na_contagem_de_predictions(db_path):
    import asyncio

    now = datetime.now(UTC)
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    with FeatureStore(db_path) as store:
        store.write_predictions(
            [
                _row("bitcoin", ts, 55.0, "mistral:mistral-small-latest:hash"),
                {**_row("ethereum", ts, 50.0, "groq:x:hash"), "llm_fallback": 1},
            ]
        )

    snap = asyncio.run(quality_snapshot.build_snapshot(now=now))
    # só a previsao real conta — fallback do LLM eh explicitamente diferente
    # de "fonte=dpl:fallback" (nome de dado de origem, nao de falha do juiz)
    assert snap["sample"]["total_predictions"] == 1
    assert "bitcoin" in snap["by_asset"]
    assert "ethereum" not in snap["by_asset"]


def test_directional_stats_ignora_score_neutro():
    enriched = [
        {"score": 60, "var_d1_pct": 2.0},  # acertou (score>50, retorno>0)
        {"score": 40, "var_d1_pct": -1.0},  # acertou (score<50, retorno<=0)
        {"score": 40, "var_d1_pct": 3.0},  # errou
        {"score": 50, "var_d1_pct": 1.0},  # neutro — deve ser ignorado
    ]
    stats = quality_snapshot._directional_stats(enriched, 1)
    assert stats["n"] == 3  # exclui o score=50
    assert stats["accuracy"] == pytest.approx(2 / 3)


def test_render_nao_quebra_com_stats_vazias():
    snap = {
        "checked_at": "x",
        "pipeline": {
            "predictions_persisted": 0,
            "predictions_today": 0,
            "llm_fallbacks_recent": None,
            "status": "FAILED",
            "watchdog_violations": ["no_real_prediction_ever_recorded"],
            "watchdog_degraded": [],
            "last_successful_run": None,
        },
        "sample": {
            "total_predictions": 0,
            "mature_d1": 0,
            "mature_d7": 0,
            "h6_valid_n": 0,
            "h6_gate": 30,
            "h6_fonte_esperada": "dpl:fallback",
        },
        "predictive_quality": {
            "accuracy_d1": None,
            "accuracy_d7": None,
            "balanced_accuracy_d1": None,
            "balanced_accuracy_d7": None,
            "spearman_d7": None,
        },
        "by_asset": {},
        "by_provider": {},
        "by_fonte": {},
        "historical_state": {
            "H5": "CLOSED_NO_GO",
            "H6": "COLLECTION_ONLY_IMMATURE",
            "V3_frozen_families": ["funding_oi_hmm_v3"],
            "capital_authorized": False,
        },
    }
    text = quality_snapshot.render(snap)
    assert "FAILED" in text
    assert "0 / 30" in text
