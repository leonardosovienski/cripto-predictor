"""Histórico de previsões — Feature Store como repositório OFICIAL (passo 4).

O garimpo_historico.csv foi APOSENTADO como canônico: `append_history` agora grava
na tabela `predictions` da Feature Store (migração 0006). O CSV, se existir, é
fonte LEGADA: `migrate_csv_to_store` o absorve idempotentemente (upsert por
(ativo, ts) — rodar N vezes = rodar 1 vez) com backfill de fonte: linha antiga
sem carimbo lê-se como 'direct'. O arquivo não é modificado nem apagado; como o
pipeline não escreve mais nele, fica congelado como registro da era pré-store.

Carimbos preservados: "Juiz" (provider:modelo:hash — impede poolar estimadores
diferentes) e "fonte" (direct | dpl:fallback | dpl:consensus — a equivalência
mediu diffs de até 7.8pp nos change_* entre fontes; o backtest ESTRATIFICA).
"""
import csv
import os

from GarimpoInvestimentos.core.paths import OUTPUT_DIR

HIST_CSV = str(OUTPUT_DIR / "garimpo_historico.csv")

# Header do CSV legado (leitura de migração; não se escreve mais neste formato).
LEGACY_FIELDNAMES = ["Ativo", "Sentimento", "Score", "Resumo", "Data",
                     "price_usd", "Juiz", "Divergencia", "Fonte"]


def to_prediction_rows(resultados: list[dict]) -> list[dict]:
    """Mapeia o dict de resultado do pipeline para a linha da tabela predictions."""
    rows = []
    for r in resultados:
        rows.append({
            "ativo":       (r.get("ativo") or "").upper(),
            "ts":          r.get("data", ""),
            "score":       float(r.get("score", 0) or 0),
            "sentimento":  r.get("sentimento", ""),
            "resumo":      r.get("resumo", ""),
            "price_usd":   float(r.get("price_usd", 0) or 0),
            "juiz":        r.get("judge", ""),
            "divergencia": 1 if str(r.get("divergencia", "")).strip() in ("1", "True", "true") else 0,
            "fonte":       r.get("data_source", "") or "direct",
        })
    return rows


def append_history(resultados: list[dict], store) -> int:
    """Grava previsões no histórico oficial (Feature Store). Upsert por (ativo, ts):
    cache hits/reexecuções não inflam o n estatístico do backtest."""
    rows = to_prediction_rows(resultados)
    if rows:
        store.write_predictions(rows)
    return len(rows)


def migrate_csv_to_store(store, csv_path: str | None = None) -> int:
    """Absorve o CSV legado na Feature Store (idempotente; 0 se o CSV não existe).

    Backfill do carimbo: 'Fonte' vazia/ausente → 'direct' (linhas pré-DPL).
    O CSV não é tocado — vira registro congelado da era pré-store."""
    path = csv_path or HIST_CSV
    if not os.path.exists(path):
        return 0
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                score = float(r["Score"])
            except (KeyError, ValueError, TypeError):
                continue    # linha malformada não entra no histórico oficial
            try:
                price = float(r.get("price_usd") or 0)
            except (ValueError, TypeError):
                price = 0.0
            rows.append({
                "ativo":       (r.get("Ativo") or "").upper(),
                "ts":          r.get("Data", ""),
                "score":       score,
                "sentimento":  r.get("Sentimento", ""),
                "resumo":      r.get("Resumo", ""),
                "price_usd":   price,
                "juiz":        r.get("Juiz", ""),
                "divergencia": 1 if str(r.get("Divergencia", "")).strip() in ("1", "True", "true") else 0,
                "fonte":       (r.get("Fonte") or "").strip() or "direct",
            })
    if rows:
        store.write_predictions(rows)
    return len(rows)
