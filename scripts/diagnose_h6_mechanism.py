"""Diagnóstico do MECANISMO da H6 — o LLM está só descrevendo o passado?

Recomendação da pesquisa externa (2026-08-24, frente W5): Chen, Green & Gulen
(arXiv:2409.11540) mostram que LLMs extrapolam retornos passados e são
mal-calibrados — ou seja, score alto pode ser apenas eco do retorno recente
("hype meter"). Se for esse o mecanismo, o sinal invertido da H6 precisa
bater um baseline de REVERSAL INGÊNUO (retorno D-7→D0 invertido, sem LLM)
para ter valor incremental — senão o LLM é custo sem informação.

Este script mede, offline e sem emitir veredito científico (exploratório —
não registra trial, não altera gate nenhum):

  1. rho_passado  = Spearman(score, retorno D-7→D0 no momento da previsão)
       → alto = o score é em boa parte espelho do passado.
  2. rho_futuro   = Spearman(score, retorno realizado D+7)  (sanidade: deve
       reproduzir o sinal negativo da H5 no mesmo recorte).
  3. rho_baseline = Spearman(-retorno D-7→D0, retorno D+7)
       → o reversal ingênuo. Se |rho_baseline| ≥ |rho_futuro|, o LLM não
       agrega nada além de um indicador de reversal de graça.

Uso:  uv run python -m scripts.diagnose_h6_mechanism
"""

from __future__ import annotations

from datetime import datetime, timedelta

from GarimpoInvestimentos.dpl.feature_store import FeatureStore


def compute_mechanism(rows: list[dict]) -> dict:
    """Núcleo puro (testável): rows com score, past_ret_pct, fut_ret_pct."""
    from GarimpoInvestimentos.analyzers.backtest import _spearman_rho

    valid = [
        r
        for r in rows
        if r.get("score") is not None
        and r.get("past_ret_pct") is not None
        and r.get("fut_ret_pct") is not None
    ]
    scores = [float(r["score"]) for r in valid]
    past = [float(r["past_ret_pct"]) for r in valid]
    fut = [float(r["fut_ret_pct"]) for r in valid]
    return {
        "n": len(valid),
        "rho_score_vs_passado": _spearman_rho(scores, past),
        "rho_score_vs_futuro": _spearman_rho(scores, fut),
        "rho_reversal_ingenuo": _spearman_rho([-p for p in past], fut),
    }


def interpret(m: dict) -> str:
    """Leitura exploratória dos três coeficientes (sem veredito de gate)."""
    if m["n"] < 10:
        return f"n={m['n']} pequeno demais para leitura — acumule coleta."
    lines = [f"n={m['n']}"]
    rp, rf, rb = (
        m["rho_score_vs_passado"],
        m["rho_score_vs_futuro"],
        m["rho_reversal_ingenuo"],
    )
    if rp is not None:
        lines.append(
            f"  score × passado D-7→D0: rho={rp:+.3f}  "
            + ("(score é em grande parte ESPELHO do passado)" if abs(rp) > 0.3 else "")
        )
    if rf is not None:
        lines.append(f"  score × futuro D+7:       rho={rf:+.3f}  (sanidade H5: esperado negativo)")
    if rb is not None:
        lines.append(f"  reversal ingênuo × D+7:   rho={rb:+.3f}  (baseline sem LLM)")
    if rf is not None and rb is not None:
        if abs(rb) >= abs(rf):
            lines.append(
                "  → o baseline de reversal INGÊNUO iguala/supera o LLM: "
                "o valor incremental do LLM ainda não está demonstrado."
            )
        else:
            lines.append(
                "  → o score do LLM carrega algo ALÉM do reversal ingênuo — "
                "a H6 tem valor incremental potencial."
            )
    return "\n".join(lines)


def load_mechanism_rows(store: FeatureStore, preds: list[dict], *, horizon_days: int) -> list[dict]:
    """Monta a amostra sem permitir informação indisponível na previsão.

    O retorno passado é uma feature e exige `published_at <= ts` da previsão.
    O retorno futuro é o desfecho e pode usar o candle posteriormente observado.
    """
    rows = []
    for r in preds:
        if r.get("score") is None or r.get("price_usd") is None:
            continue
        try:
            pred_dt = datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")
            price = float(r["price_usd"])
            score = float(r["score"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0:
            continue
        ativo = (r.get("ativo") or "").lower()
        past = store.close_on(
            ativo,
            "1d",
            pred_dt - timedelta(days=horizon_days),
            published_as_of=pred_dt,
        )
        fut = store.close_on(ativo, "1d", pred_dt + timedelta(days=horizon_days))
        if not past or not fut:
            continue
        rows.append(
            {
                "score": score,
                "past_ret_pct": (price / past[0] - 1) * 100,
                "fut_ret_pct": (fut[0] / price - 1) * 100,
            }
        )
    return rows


def main() -> int:
    from GarimpoInvestimentos.analyzers.backtest import PRIMARY_HORIZON
    from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB

    with FeatureStore(FEATURE_STORE_DB) as store:
        preds = store.read_predictions()
        rows = load_mechanism_rows(store, preds, horizon_days=PRIMARY_HORIZON)
    m = compute_mechanism(rows)
    print("Diagnóstico do mecanismo da H6 (EXPLORATÓRIO — não é veredito):\n")
    print(interpret(m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
