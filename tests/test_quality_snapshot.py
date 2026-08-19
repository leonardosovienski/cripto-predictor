"""Painel de qualidade: engenharia vs amostra científica não devem se confundir.

Cobre especificamente o ponto levantado na auditoria de 2026-08-19: previsões
recém-gravadas (mesmo dia, sem preço realizado ainda) NÃO podem aparecer como
maduras, e a contagem de "H6 valid n" tem que vir da mesma função que fecha o
veredito oficial (h6_spearman_verdict), não de uma reimplementação do filtro.
"""

import json
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


def test_render_nao_quebra_com_stats_vazias(db_path):
    """Reusa o snapshot real de um banco vazio (não duplica o schema à mão —
    um dict sintético desatualiza sozinho toda vez que build_snapshot ganha
    um campo novo, como já aconteceu com maturity_stage)."""
    import asyncio

    with FeatureStore(db_path):
        pass
    snap = asyncio.run(quality_snapshot.build_snapshot())
    text = quality_snapshot.render(snap)
    assert "PROJECT QUALITY SNAPSHOT" in text
    assert "0 / 30" in text
    assert "VERY_EARLY" in text


def test_maturity_stage_thresholds():
    assert quality_snapshot._maturity_stage(0) == "VERY_EARLY"
    assert quality_snapshot._maturity_stage(9) == "VERY_EARLY"
    assert quality_snapshot._maturity_stage(10) == "IMMATURE"
    assert quality_snapshot._maturity_stage(29) == "IMMATURE"
    assert quality_snapshot._maturity_stage(30) == "PRELIMINARY"
    assert quality_snapshot._maturity_stage(99) == "PRELIMINARY"
    assert quality_snapshot._maturity_stage(100) == "DEVELOPING_EVIDENCE"
    assert quality_snapshot._maturity_stage(299) == "DEVELOPING_EVIDENCE"
    assert quality_snapshot._maturity_stage(300) == "SUBSTANTIAL_SAMPLE"
    assert quality_snapshot._maturity_stage(10_000) == "SUBSTANTIAL_SAMPLE"


def test_score_buckets_agrupa_corretamente():
    enriched = [
        {"score": 10, "var_d7_pct": -5.0},
        {"score": 25, "var_d7_pct": 1.0},
        {"score": 65, "var_d7_pct": 2.0},
        {"score": 100, "var_d7_pct": 3.0},  # extremo direito inclusivo
    ]
    buckets = quality_snapshot._score_buckets(enriched, 7)
    by_range = {b["range"]: b for b in buckets}
    assert by_range["0-20"]["n"] == 1
    assert by_range["0-20"]["avg_return"] == -5.0
    assert by_range["20-40"]["n"] == 1
    assert by_range["40-60"]["n"] == 0
    assert by_range["40-60"]["avg_return"] is None
    assert by_range["60-80"]["n"] == 1
    assert by_range["80-100"]["n"] == 1  # score=100 cai no último bucket


def test_majority_baseline_precisa_de_n_minimo():
    assert quality_snapshot._majority_baseline([{"var_d7_pct": 1.0}] * 3, 7) is None


def test_majority_baseline_calcula_direcao_majoritaria():
    enriched = [{"var_d7_pct": v} for v in (1.0, 2.0, 3.0, -1.0)]  # 3 up, 1 down
    baseline = quality_snapshot._majority_baseline(enriched, 7)
    assert baseline["majority_direction"] == "up"
    assert baseline["n"] == 4
    assert baseline["accuracy"] == pytest.approx(3 / 4)


def test_by_provider_quality_separa_por_juiz():
    enriched = [
        {"juiz": "mistral", "score": 60, "var_d7_pct": 1.0},
        {"juiz": "mistral", "score": 40, "var_d7_pct": -1.0},
        {"juiz": "groq", "score": 60, "var_d7_pct": -1.0},
    ]
    result = quality_snapshot._by_provider_quality(enriched, 7)
    assert result["mistral"]["n_total"] == 2
    assert result["mistral"]["accuracy"] == 1.0
    assert result["groq"]["n_total"] == 1
    assert result["groq"]["accuracy"] == 0.0


def test_append_history_e_realmente_append_only(tmp_path):
    history_path = tmp_path / "history.jsonl"
    snap1 = {
        "checked_at": "2026-08-19T00:00:00Z",
        "pipeline": {"llm_fallbacks_recent": 0.0, "status": "HEALTHY"},
        "sample": {
            "total_predictions": 2,
            "maturity_stage": "VERY_EARLY",
            "mature_d7": 0,
            "h6_valid_n": 2,
            "h6_gate": 30,
        },
        "predictive_quality": {
            "accuracy_d7": None,
            "balanced_accuracy_d7": None,
            "majority_baseline_d7": None,
            "spearman_d7": None,
        },
        "by_provider": {"mistral": 1, "groq": 1},
    }
    quality_snapshot.append_history(snap1, path=history_path)
    assert history_path.exists()
    lines_after_first = history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines_after_first) == 1
    record1 = json.loads(lines_after_first[0])
    assert record1["n"] == 2
    assert record1["maturity_stage"] == "VERY_EARLY"
    assert record1["providers"] == {"mistral": 1, "groq": 1}

    snap2 = {**snap1, "checked_at": "2026-08-20T00:00:00Z"}
    snap2["sample"] = {**snap1["sample"], "total_predictions": 5}
    quality_snapshot.append_history(snap2, path=history_path)

    lines_after_second = history_path.read_text(encoding="utf-8").splitlines()
    # a primeira linha continua exatamente igual — nada foi reescrito
    assert lines_after_second[0] == lines_after_first[0]
    assert len(lines_after_second) == 2
    record2 = json.loads(lines_after_second[1])
    assert record2["n"] == 5


def test_history_record_extrai_campos_pedidos():
    snap = {
        "checked_at": "x",
        "pipeline": {"llm_fallbacks_recent": 0.05, "status": "DEGRADED"},
        "sample": {
            "total_predictions": 12,
            "maturity_stage": "IMMATURE",
            "mature_d7": 8,
            "h6_valid_n": 8,
            "h6_gate": 30,
        },
        "predictive_quality": {
            "accuracy_d7": 0.625,
            "balanced_accuracy_d7": 0.6,
            "majority_baseline_d7": {"accuracy": 0.5, "n": 8, "majority_direction": "up"},
            "spearman_d7": {"rho": 0.12, "ic_lower": -0.1, "ic_upper": 0.3, "n": 8},
        },
        "by_provider": {"gemini": 4, "groq": 4},
    }
    record = quality_snapshot._history_record(snap)
    assert record["n"] == 12
    assert record["mature_n_d7"] == 8
    assert record["accuracy_d7"] == 0.625
    assert record["majority_baseline_accuracy_d7"] == 0.5
    assert record["spearman_d7"] == 0.12
    assert record["fallback_rate_recent"] == 0.05
    assert record["pipeline_status"] == "DEGRADED"
    assert record["providers"] == {"gemini": 4, "groq": 4}
    assert record["h6_valid_n"] == 8
