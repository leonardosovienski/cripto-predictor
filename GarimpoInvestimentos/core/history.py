import csv
import os

from GarimpoInvestimentos.core.paths import OUTPUT_DIR

HIST_CSV = str(OUTPUT_DIR / "garimpo_historico.csv")

# "Juiz" = carimbo provider:modelo:hash-do-prompt (reprodutibilidade — impede o
# backtest de poolar estimadores diferentes).
# Colunas técnicas (RSI14..Bollinger_pctB) = snapshot dos indicadores no instante da
# previsão, persistido para o backtest RESIDUALIZAR o score contra eles (separar o
# sinal do LLM do RSI/tendência redescobertos). Tudo aditivo; histórico antigo é migrado.
FIELDNAMES = ["Ativo", "Sentimento", "Score", "Resumo", "Data", "price_usd", "Juiz", "Divergencia",
              "RSI14", "MACD_hist", "vs_SMA50_pct", "vs_SMA200_pct", "Bollinger_pctB"]


def _ensure_header() -> None:
    """Migra um histórico de header antigo para FIELDNAMES (aditivo: colunas novas
    ficam vazias nas linhas velhas). Preserva TODOS os dados — nunca destrói."""
    if not os.path.exists(HIST_CSV):
        return
    with open(HIST_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames == FIELDNAMES:
            return
        rows = list(reader)
    with open(HIST_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


def _existing_keys() -> set:
    """Chaves (Ativo, Data) já presentes no histórico — para não duplicar previsões."""
    keys = set()
    if os.path.exists(HIST_CSV):
        with open(HIST_CSV, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                keys.add((row.get("Ativo", ""), row.get("Data", "")))
    return keys


def append_history(resultados: list[dict]) -> None:
    _ensure_header()
    seen = _existing_keys()
    file_exists = os.path.exists(HIST_CSV)
    with open(HIST_CSV, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for r in resultados:
            key = (r.get("ativo", "").upper(), r.get("data", ""))
            # Pula cache hits / reexecuções: a mesma previsão (ativo + timestamp) não
            # deve inflar o n estatístico do backtest.
            if key in seen:
                continue
            seen.add(key)
            writer.writerow({
                "Ativo":      r.get("ativo", "").upper(),
                "Sentimento": r.get("sentimento", ""),
                "Score":      r.get("score", 0),
                "Resumo":     r.get("resumo", ""),
                "Data":       r.get("data", ""),
                "price_usd":  r.get("price_usd", ""),
                "Juiz":       r.get("judge", ""),
                "Divergencia": r.get("divergencia", ""),
                "RSI14":         r.get("rsi_14", ""),
                "MACD_hist":     r.get("macd_histogram", ""),
                "vs_SMA50_pct":  r.get("preco_vs_sma50_pct", ""),
                "vs_SMA200_pct": r.get("preco_vs_sma200_pct", ""),
                "Bollinger_pctB": r.get("bollinger_pct_b", ""),
            })
