"""Painel diário de qualidade — engenharia, amostra científica e estado histórico.

Motivação: depois de restaurar o pipeline (auditoria 2026-08-19), a pergunta
natural é "como estamos indo" — mas isso mistura duas coisas que precisam
ficar sempre separadas: a engenharia (o pipeline está rodando? gravando?
sem fallback do LLM?) e a qualidade preditiva (o score prevê alguma coisa?
já dá pra saber?). Nos primeiros dias de uma coleta reiniciada, a resposta
honesta para a segunda pergunta é quase sempre "ainda não" — e este painel
deve deixar isso explícito, nunca inflar confiança com n pequeno.

NÃO recalcula a matemática de H5/H6 — importa e chama as MESMAS funções que
`analyzers/backtest.py` usa para fechar vereditos oficiais
(`enrich_with_realized_prices`, `h6_spearman_verdict`, `H6_*`), pra nunca
divergir do critério real de elegibilidade/maturidade. Ver nota em
`enrich_with_realized_prices` sobre por que isso é obrigatório.

Uso:
    python -m GarimpoInvestimentos.quality_snapshot
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import UTC, datetime

from predictor_core.stats import spearman_block_ci

from GarimpoInvestimentos.analyzers.backtest import (
    H6_LIVE_FONTE,
    H6_MIN_N,
    PRIMARY_HORIZON,
    _load_rows,
    enrich_with_realized_prices,
    h6_spearman_verdict,
    overlap_block_length,
)
from GarimpoInvestimentos.governance import SCIENTIFIC_STATE_CHARTER
from GarimpoInvestimentos.phase1_watchdog import check_phase1_health


def _directional_stats(enriched: list[dict], horizon: int) -> dict:
    """Acurácia direcional + balanced accuracy no horizonte, sobre previsões
    maduras com score != 50 (score=50 é neutro, não tem direção prevista)."""
    key = f"var_d{horizon}_pct"
    mature = [r for r in enriched if r.get(key) is not None and r["score"] != 50]
    if not mature:
        return {"n": 0, "accuracy": None, "balanced_accuracy": None}

    up_true = [r for r in mature if r[key] > 0]
    down_true = [r for r in mature if r[key] <= 0]
    hits = sum(1 for r in mature if (r["score"] > 50) == (r[key] > 0))
    accuracy = hits / len(mature)

    recall_up = sum(1 for r in up_true if r["score"] > 50) / len(up_true) if up_true else None
    recall_down = (
        sum(1 for r in down_true if r["score"] <= 50) / len(down_true) if down_true else None
    )
    recalls = [r for r in (recall_up, recall_down) if r is not None]
    balanced = sum(recalls) / len(recalls) if recalls else None

    return {"n": len(mature), "accuracy": accuracy, "balanced_accuracy": balanced}


def _spearman_stats(enriched: list[dict], horizon: int) -> dict | None:
    key = f"var_d{horizon}_pct"
    pairs = [(r["score"], r[key]) for r in enriched if r.get(key) is not None]
    if len(pairs) < 4:
        return None
    rho, lo, hi = spearman_block_ci(pairs, block_length=overlap_block_length(horizon))
    if rho is None:
        return None
    return {"n": len(pairs), "rho": rho, "ic_lower": lo, "ic_upper": hi}


def _fmt_pct(value: float | None) -> str:
    return f"{value * 100:.1f}%" if value is not None else "NOT_AVAILABLE"


def _fmt_rho(stats: dict | None) -> str:
    if stats is None:
        return "NOT_AVAILABLE"
    if stats["ic_lower"] is None:
        return f"{stats['rho']:+.3f} (n={stats['n']}, IC indisponível)"
    return (
        f"{stats['rho']:+.3f} [{stats['ic_lower']:+.3f}, {stats['ic_upper']:+.3f}] (n={stats['n']})"
    )


async def build_snapshot(now: datetime | None = None) -> dict:
    stamp = now or datetime.now(UTC)
    today_str = stamp.strftime("%Y-%m-%d")

    # backtest_module para ler FEATURE_STORE_DB do MESMO lugar que _load_rows() usa
    # de fato (nome ligado no módulo de backtest.py, não em core.paths — os dois
    # normalmente apontam pro mesmo arquivo, mas podem divergir se um dos dois for
    # monkeypatchado isoladamente; usar sempre o mesmo evita esse tipo de bug).
    import GarimpoInvestimentos.analyzers.backtest as _backtest_module

    health = check_phase1_health(db_path=_backtest_module.FEATURE_STORE_DB, now=stamp)

    rows_real = _load_rows()  # já exclui llm_fallback=1 (previsão de verdade)
    with_price = await enrich_with_realized_prices(rows_real) if rows_real else []

    by_asset = Counter(r["ativo"] for r in rows_real)
    by_juiz = Counter(r["juiz"] for r in rows_real if r.get("juiz"))
    by_fonte = Counter(r.get("fonte", "direct") for r in rows_real)
    predictions_today = sum(
        1 for r in rows_real if r["pred_date"].strftime("%Y-%m-%d") == today_str
    )

    d1 = _directional_stats(with_price, 1)
    d7 = _directional_stats(with_price, PRIMARY_HORIZON)
    spearman_primary = _spearman_stats(with_price, PRIMARY_HORIZON)

    h6_result = None
    if with_price:
        h6_result = h6_spearman_verdict(with_price, PRIMARY_HORIZON)

    state = {}
    if SCIENTIFIC_STATE_CHARTER.exists():
        state = json.loads(SCIENTIFIC_STATE_CHARTER.read_text(encoding="utf-8"))

    return {
        "checked_at": stamp.isoformat(),
        "pipeline": {
            "predictions_persisted": len(rows_real),
            "predictions_today": predictions_today,
            "llm_fallbacks_recent": health.get("fallback_rate_recent"),
            "status": health["status"],
            "watchdog_violations": health["violations"],
            "watchdog_degraded": health["degraded_signals"],
            "last_successful_run": health["last_successful_run"],
        },
        "sample": {
            "total_predictions": len(rows_real),
            "mature_d1": d1["n"],
            "mature_d7": d7["n"],
            "h6_valid_n": h6_result["n"] if h6_result else 0,
            "h6_gate": H6_MIN_N,
            "h6_fonte_esperada": H6_LIVE_FONTE,
        },
        "predictive_quality": {
            "accuracy_d1": d1["accuracy"],
            "accuracy_d7": d7["accuracy"],
            "balanced_accuracy_d1": d1["balanced_accuracy"],
            "balanced_accuracy_d7": d7["balanced_accuracy"],
            "spearman_d7": spearman_primary,
        },
        "by_asset": dict(by_asset),
        "by_provider": dict(by_juiz),
        "by_fonte": dict(by_fonte),
        "historical_state": {
            "H5": state.get("hypotheses", {}).get("H5", "UNKNOWN"),
            "H6": state.get("hypotheses", {}).get("H6", "UNKNOWN"),
            "V3_frozen_families": state.get("frozen_families", []),
            "capital_authorized": state.get("capital_authorized"),
        },
    }


def render(snap: dict) -> str:
    p, s, q = snap["pipeline"], snap["sample"], snap["predictive_quality"]
    lines = [
        "PROJECT QUALITY SNAPSHOT",
        f"  (gerado em {snap['checked_at']})",
        "",
        "Pipeline",
        "--------",
        f"  Predictions persisted (nao-fallback): {p['predictions_persisted']}",
        f"  Predictions today:                    {p['predictions_today']}",
        f"  LLM fallback rate (ultimas 20):        {_fmt_pct(p['llm_fallbacks_recent'])}",
        f"  Pipeline status (watchdog):            {p['status']}",
        f"  Last successful (juiz real) run:       {p['last_successful_run']}",
    ]
    if p["watchdog_violations"]:
        lines.append(f"  Violations: {p['watchdog_violations']}")
    if p["watchdog_degraded"]:
        lines.append(f"  Degraded signals: {p['watchdog_degraded']}")
    lines += [
        "",
        "Scientific sample",
        "------------------",
        f"  Total prospective predictions:  {s['total_predictions']}",
        f"  Mature D+1 predictions:         {s['mature_d1']}",
        f"  Mature D+{PRIMARY_HORIZON} predictions:         {s['mature_d7']}",
        f"  H6 valid n (fonte={s['h6_fonte_esperada']}, pred_date>registered_at): {s['h6_valid_n']}",
        f"  H6 gate:                        {s['h6_valid_n']} / {s['h6_gate']}",
        "",
        "Predictive quality",
        "-------------------",
        f"  Accuracy D+1:              {_fmt_pct(q['accuracy_d1'])}",
        f"  Accuracy D+{PRIMARY_HORIZON}:              {_fmt_pct(q['accuracy_d7'])}",
        f"  Balanced accuracy D+1:     {_fmt_pct(q['balanced_accuracy_d1'])}",
        f"  Balanced accuracy D+{PRIMARY_HORIZON}:     {_fmt_pct(q['balanced_accuracy_d7'])}",
        f"  Spearman(score, D+{PRIMARY_HORIZON}):      {_fmt_rho(q['spearman_d7'])}",
        "",
        "Economic quality",
        "-----------------",
        "  PnL / Sharpe / Edge after costs: NOT_AVAILABLE (n insuficiente; nunca reportar sem custos reais)",
        "",
        "Predictions by asset:    "
        + (", ".join(f"{k}={v}" for k, v in snap["by_asset"].items()) or "-"),
        "Predictions by provider: "
        + (", ".join(f"{k}={v}" for k, v in snap["by_provider"].items()) or "-"),
        "Predictions by fonte:    "
        + (", ".join(f"{k}={v}" for k, v in snap["by_fonte"].items()) or "-"),
        "",
        "Historical state",
        "-----------------",
        f"  H5:  {snap['historical_state']['H5']}",
        f"  H6:  {snap['historical_state']['H6']}",
        f"  V3/HMM frozen families: {snap['historical_state']['V3_frozen_families']}",
        f"  Capital authorized: {snap['historical_state']['capital_authorized']}",
    ]
    return "\n".join(lines)


def main() -> int:
    snap = asyncio.run(build_snapshot())
    print(render(snap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
