"""Passo 4 — Feature Store como histórico oficial: migração do CSV legado e
integração do backtest (lê da store, produz as mesmas linhas que o loader CSV
produzia para a mesma amostra).
"""
import sys
import types

from GarimpoInvestimentos.core import history
from GarimpoInvestimentos.dpl import FeatureStore

# CSV legado real (era pré-Fonte + linha carimbada) — espelha o output/ de produção.
_LEGACY_CSV = (
    "﻿Ativo,Sentimento,Score,Resumo,Data,price_usd,Juiz,Divergencia\r\n"
    "BITCOIN,negativo,25.0,tendencia de baixa,2026-06-30 02:35:23,59296.8,gemini:x:y,0\r\n"
)
_STAMPED_CSV = (
    "﻿Ativo,Sentimento,Score,Resumo,Data,price_usd,Juiz,Divergencia,Fonte\r\n"
    "SOLANA,positivo,85.0,momentum,2026-07-01 23:02:31,150.0,gemini:x:y,0,dpl:fallback\r\n"
    "VELVET,positivo,80.0,fallback aplicado,2026-07-01 23:49:26,1.0,gemini:x:y,0,dpl:fallback\r\n"
    "QUEBRADA,positivo,,sem score,2026-07-01 23:50:00,1.0,gemini:x:y,0,\r\n"
)


def test_migracao_csv_backfill_direct_e_preserva_dados(tmp_path):
    csv_path = tmp_path / "legado.csv"
    csv_path.write_text(_LEGACY_CSV, encoding="utf-8")
    bytes_antes = csv_path.read_bytes()
    with FeatureStore(tmp_path / "fs.db") as fs:
        n = history.migrate_csv_to_store(fs, csv_path=str(csv_path))
        preds = fs.read_predictions()
    assert n == 1 and len(preds) == 1
    p = preds[0]
    assert p["fonte"] == "direct"                 # linha pré-DPL → backfill
    assert p["resumo"] == "tendencia de baixa"    # dado não corrompido
    assert p["juiz"] == "gemini:x:y" and p["score"] == 25.0
    # CSV não foi tocado (fica congelado como registro da era pré-store)
    assert csv_path.read_bytes() == bytes_antes


def test_migracao_idempotente_e_linha_malformada_fica_fora(tmp_path):
    csv_path = tmp_path / "misto.csv"
    csv_path.write_text(_STAMPED_CSV, encoding="utf-8")
    with FeatureStore(tmp_path / "fs.db") as fs:
        n1 = history.migrate_csv_to_store(fs, csv_path=str(csv_path))
        n2 = history.migrate_csv_to_store(fs, csv_path=str(csv_path))  # 2ª vez = upsert
        preds = fs.read_predictions()
    assert n1 == n2 == 2                          # QUEBRADA (sem score) não entra
    assert len(preds) == 2                        # idempotente: nada duplicou
    assert {p["fonte"] for p in preds} == {"dpl:fallback"}  # carimbo preservado


def test_backtest_le_da_store_com_mesmo_resultado_do_loader_csv(tmp_path, monkeypatch):
    """Integração: _load_rows agora lê da store e reproduz o contrato do loader
    CSV antigo — filtra fallback de LLM e linhas inválidas, normaliza tipos,
    backfill de fonte. A amostra cobre os 4 casos."""
    monkeypatch.setenv("GEMINI_API_KEY", "GEMINIKEY-0123456789-abcdef")
    monkeypatch.setenv("SERP_API_KEY", "SERPKEY-0123456789-abcdef")
    monkeypatch.setitem(sys.modules, "httpx", types.ModuleType("httpx"))

    from GarimpoInvestimentos.analyzers import backtest

    db = tmp_path / "fs.db"
    with FeatureStore(db) as fs:
        fs.write_predictions([
            {"ativo": "BITCOIN", "ts": "2026-06-30 02:35:23", "score": 25.0,
             "sentimento": "negativo", "resumo": "baixa", "price_usd": 59296.8,
             "juiz": "gemini:x:y", "divergencia": 0, "fonte": "direct"},
            {"ativo": "SOLANA", "ts": "2026-07-01 23:02:31", "score": 85.0,
             "sentimento": "positivo", "resumo": "alta", "price_usd": 150.0,
             "juiz": "gemini:x:y", "divergencia": 1, "fonte": "dpl:fallback"},
            {"ativo": "VELVET", "ts": "2026-07-01 23:49:26", "score": 80.0,
             "sentimento": "positivo", "resumo": "fallback aplicado", "price_usd": 1.0,
             "juiz": "gemini:x:y", "divergencia": 0, "fonte": "dpl:fallback"},
            {"ativo": "ZERADA", "ts": "2026-07-01 23:55:00", "score": 50.0,
             "sentimento": "neutro", "resumo": "preco invalido", "price_usd": 0.0,
             "juiz": "gemini:x:y", "divergencia": 0, "fonte": "dpl:fallback"},
        ])
    monkeypatch.setattr(backtest, "FEATURE_STORE_DB", db)
    monkeypatch.setattr(history, "HIST_CSV", str(tmp_path / "inexistente.csv"))

    rows = backtest._load_rows()
    # VELVET (fallback de LLM) e ZERADA (preço <= 0) ficam fora — como no CSV
    assert [r["ativo"] for r in rows] == ["bitcoin", "solana"]
    btc, sol = rows
    assert btc["fonte"] == "direct" and sol["fonte"] == "dpl:fallback"
    assert btc["score"] == 25.0 and btc["pred_price"] == 59296.8
    assert sol["divergencia"] == 1
    assert btc["pred_date"].year == 2026 and btc["pred_date"].month == 6


def test_load_rows_ignora_ts_ilegivel_sem_quebrar_as_demais(tmp_path, monkeypatch):
    """Gap encontrado na auditoria de cobertura (2026-07-20): todo teste de
    temporalidade existente cobre ORDEM errada (published_at < ts) ou LAG
    excessivo — nenhum cobria um `ts` genuinamente ilegível (string que não é
    data nenhuma), o cenário real de uma linha corrompida de CSV legado ou
    escrita manual na store. `write_predictions` não valida o formato de `ts`
    (coluna TEXT, sem checagem) — a defesa real é o try/except de
    `_load_rows()` em `datetime.strptime`. Fixa que ele funciona: a linha
    ilegível é descartada, as válidas sobrevivem."""
    from GarimpoInvestimentos.analyzers import backtest

    db = tmp_path / "fs.db"
    with FeatureStore(db) as fs:
        fs.write_predictions([
            {"ativo": "BITCOIN", "ts": "não-é-uma-data-nenhuma", "score": 70.0,
             "sentimento": "positivo", "resumo": "x", "price_usd": 100.0,
             "juiz": "gemini:x:y", "divergencia": 0, "fonte": "direct"},
            {"ativo": "SOLANA", "ts": "2026-07-01 23:02:31", "score": 85.0,
             "sentimento": "positivo", "resumo": "ok", "price_usd": 150.0,
             "juiz": "gemini:x:y", "divergencia": 0, "fonte": "dpl:fallback"},
        ])
    monkeypatch.setattr(backtest, "FEATURE_STORE_DB", db)
    monkeypatch.setattr(history, "HIST_CSV", str(tmp_path / "inexistente.csv"))

    rows = backtest._load_rows()  # não deve levantar StrptimeError/ValueError
    assert [r["ativo"] for r in rows] == ["solana"]


def test_analise_persiste_previsao_ANTES_de_fechar_a_store():
    """Regressão da conferência de 2026-07-02: um store.close() herdado do fluxo
    pré-passo-4 rodava antes do append_history — a previsão pontuava, exportava
    e SUMIA em silêncio (sqlite 'Cannot operate on a closed database' engolido).
    Asserção estrutural sobre o fonte de main.py (importá-lo exige chaves):
    o append tem que vir antes do close."""
    from pathlib import Path

    src = (Path(__file__).parent.parent / "GarimpoInvestimentos" / "main.py").read_text(
        encoding="utf-8")
    assert "append_history(resultados, store)" in src
    assert "store.close()" in src
    assert src.index("append_history(resultados, store)") < src.index("store.close()"), (
        "store.close() antes do append_history: previsões seriam descartadas em silêncio")


def test_report_estratifica_por_fonte(tmp_path, monkeypatch, capsys):
    """A estratificação por Fonte aparece no horizonte principal — a equivalência
    mediu diffs de até 7.8pp nos change_* entre fontes; poolar sem mostrar os
    estratos contaminaria o veredito."""
    import random

    monkeypatch.setenv("GEMINI_API_KEY", "GEMINIKEY-0123456789-abcdef")
    monkeypatch.setenv("SERP_API_KEY", "SERPKEY-0123456789-abcdef")
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(tmp_path / "ev.jsonl"))
    monkeypatch.setitem(sys.modules, "httpx", types.ModuleType("httpx"))

    from GarimpoInvestimentos.analyzers import backtest

    rng = random.Random(1)
    enriched = []
    for i in range(24):
        score = rng.uniform(0, 100)
        enriched.append({
            "score": score, "divergencia": 0,
            "fonte": "direct" if i % 2 == 0 else "dpl:fallback",
            "var_d1_pct": rng.gauss(0, 2),
            "var_d7_pct": 0.08 * (score - 50) + rng.gauss(0, 2),
            "var_d30_pct": rng.gauss(0, 5),
        })
    backtest._report(enriched)
    out = capsys.readouterr().out
    assert "fonte=direct" in out
    assert "fonte=dpl:fallback" in out
