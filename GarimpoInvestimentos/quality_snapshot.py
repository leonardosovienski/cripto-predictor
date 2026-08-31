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
from pathlib import Path

from predictor_core.stats import spearman_block_ci

from GarimpoInvestimentos.analyzers.backtest import (
    H6_LIVE_FONTE,
    H6_MIN_N,
    H6_POWER_TARGET_N,
    H6_TRIAL_NAME,
    PRIMARY_HORIZON,
    _load_rows,
    enrich_with_realized_prices,
    h6_power_context,
    h6_spearman_verdict,
    overlap_block_length,
)
from GarimpoInvestimentos.core.paths import OUTPUT_DIR
from GarimpoInvestimentos.governance import SCIENTIFIC_STATE_CHARTER
from GarimpoInvestimentos.phase1_watchdog import check_phase1_health

# Histórico append-only da própria saúde científica do projeto — NUNCA sobrescrito
# nem truncado, só append (mesmo princípio de predictions_archive/migração 0016).
# Não altera modelo nem H6; é só uma série temporal do que o snapshot já calcula,
# pra enxergar evolução (n crescendo, accuracy oscilando, fallback rate) sem
# precisar rodar o painel e guardar prints manualmente.
HISTORY_PATH = OUTPUT_DIR / "quality_snapshot_history.jsonl"

# Estado da H6 em arquivo VERSIONADO — ao lado de trials.json, mesma convenção
# ("viaja com o repositório"). Existe por um motivo específico: o n real da H6 é
# calculado a partir do feature_store.db, que vive em OUTPUT_DIR e é gitignored.
# Logo, ninguém fora da máquina de produção consegue vê-lo — nem uma revisão, nem
# um handoff, nem o cron semanal "Watch H6 n>=30", que só enxerga o que está
# commitado. Sem este artefato, o único n visível de fora é o número escrito à mão
# em docs/HYPOTHESES.md, que envelhece em silêncio. Este arquivo é a ponte
# produção -> git: gerado aqui, commitado por quem roda o painel.
#
# NÃO é fonte científica: não substitui trials.json nem o gate de
# h6_spearman_verdict, e não autoriza nada. É observação de estado, publicada.
H6_STATUS_PATH = Path(__file__).resolve().parent / "h6_status.json"

# Anchor público da cadeia de hash do predictions_archive (migração 0017 +
# dpl/hash_chain.py): mesma convenção do h6_status.json — commitado à mão
# quando muda. Quem guarda o manifest de ontem prova que nada anterior foi
# adulterado (commit-and-reveal de operação solo).
CHAIN_MANIFEST_PATH = Path(__file__).resolve().parent / "chain_manifest.json"


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


# Estágios de maturidade da amostra — monitoramento apenas, NUNCA substitui o
# gate oficial de H6 (H6_MIN_N, verificado por h6_spearman_verdict). Serve só
# pra evitar formar opinião com n=3/n=8/n=12 sem perceber o quão cedo ainda é.
#
# São RÓTULOS OPERACIONAIS, não níveis de confiança científica: n=100 pode
# continuar fraco se houver forte dependência temporal, baixa diversidade de
# ativos/providers, ou efeito concentrado num único regime. O n cresce sozinho;
# a confiança real só vem das métricas ao lado (Spearman, baseline, by_provider).
_MATURITY_STAGES = (
    (10, "VERY_EARLY"),
    (30, "IMMATURE"),
    (100, "PRELIMINARY"),
    (300, "DEVELOPING_EVIDENCE"),
)


def _maturity_stage(n: int) -> str:
    for threshold, label in _MATURITY_STAGES:
        if n < threshold:
            return label
    return "SUBSTANTIAL_SAMPLE"


_SCORE_BUCKETS = ((0, 20), (20, 40), (40, 60), (60, 80), (80, 100))


def _score_buckets(enriched: list[dict], horizon: int) -> list[dict]:
    """score -> retorno realizado, em buckets fixos. Não decide nada sozinho
    (n por bucket tende a ser pequeno por muito tempo) — é pra visualizar a
    forma da relação, não pra tirar conclusão de um bucket isolado."""
    key = f"var_d{horizon}_pct"
    mature = [r for r in enriched if r.get(key) is not None]
    out = []
    for lo, hi in _SCORE_BUCKETS:
        in_bucket = [
            r for r in mature if lo <= r["score"] < hi or (hi == 100 and r["score"] == 100)
        ]
        if not in_bucket:
            out.append({"range": f"{lo}-{hi}", "n": 0, "avg_return": None, "pct_positive": None})
            continue
        rets = [r[key] for r in in_bucket]
        out.append(
            {
                "range": f"{lo}-{hi}",
                "n": len(in_bucket),
                "avg_return": sum(rets) / len(rets),
                "pct_positive": sum(1 for x in rets if x > 0) / len(rets),
            }
        )
    return out


def _by_provider_quality(enriched: list[dict], horizon: int) -> dict[str, dict]:
    """Accuracy/Spearman por juiz (provider:modelo:hash) no horizonte principal —
    monitoramento, nunca seleção: a coorte continua coletando todos os providers
    igualmente enquanto estiver aberta (ver auditoria sobre Gemini em H5)."""
    juizes: list[str] = sorted({j for r in enriched if (j := r.get("juiz"))})
    out = {}
    for juiz in juizes:
        sub = [r for r in enriched if r.get("juiz") == juiz]
        d = _directional_stats(sub, horizon)
        sp = _spearman_stats(sub, horizon)
        out[juiz] = {
            "n_total": len(sub),
            "n_mature": d["n"],
            "accuracy": d["accuracy"],
            "spearman": sp["rho"] if sp else None,
        }
    return out


def _majority_baseline(enriched: list[dict], horizon: int) -> dict | None:
    """Baseline mais barato possível: prever sempre a direção majoritária
    observada NA PRÓPRIA amostra madura (não é um baseline causal/prospectivo —
    é só a régua mínima que qualquer sinal real precisa bater: se o LLM não
    supera nem isso, ele não está adicionando informação).

    Este é o PRIMEIRO baseline, não o único que vai importar. Quando a amostra
    crescer o suficiente (momentum/mean-reversion exigem buscar preço histórico
    adicional por linha — custo real, não faz sentido com n pequeno), os
    próximos baselines que precisam entrar são momentum simples e mean-reversion
    simples: um predictor de mercado tem que bater não só "sempre a direção
    majoritária", mas heurísticas triviais de mercado."""
    key = f"var_d{horizon}_pct"
    mature = [r for r in enriched if r.get(key) is not None]
    if len(mature) < 4:
        return None
    n_up = sum(1 for r in mature if r[key] > 0)
    majority_is_up = n_up >= (len(mature) - n_up)
    hits = sum(1 for r in mature if (r[key] > 0) == majority_is_up)
    return {
        "n": len(mature),
        "accuracy": hits / len(mature),
        "majority_direction": "up" if majority_is_up else "down",
    }


def _fmt_pct(value: float | None) -> str:
    return f"{value * 100:.1f}%" if value is not None else "NOT_AVAILABLE"


def _fmt_majority_baseline(baseline: dict | None) -> str:
    if baseline is None:
        return "NOT_AVAILABLE"
    return (
        f"{_fmt_pct(baseline['accuracy'])} "
        f"(sempre '{baseline['majority_direction']}', n={baseline['n']})"
    )


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
    # Contexto de LEITURA, calculado fora de h6_spearman_verdict de proposito
    # (ver print_h6_power_context em analyzers/backtest.py): tabela estatica
    # publicada em docs/HYPOTHESES.md B12, nao uma simulacao nova a cada
    # execucao. Nao muda o veredito nem o gate — so qualifica quem le.
    h6_power = h6_power_context(h6_result["n"]) if h6_result else None

    score_buckets = _score_buckets(with_price, PRIMARY_HORIZON)
    by_provider_quality = _by_provider_quality(with_price, PRIMARY_HORIZON)
    majority_baseline = _majority_baseline(with_price, PRIMARY_HORIZON)

    state = {}
    if SCIENTIFIC_STATE_CHARTER.exists():
        state = json.loads(SCIENTIFIC_STATE_CHARTER.read_text(encoding="utf-8"))

    return {
        "checked_at": stamp.isoformat(),
        # Resultado canônico bruto da H6. Antes daqui só o `n` sobrevivia em
        # sample.h6_valid_n — o que basta enquanto n < gate (a função devolve
        # rho/IC como None de propósito), mas descartaria o VEREDITO no dia em
        # que o gate abrisse. Guardado inteiro para o artefato versionado.
        "h6": h6_result,
        "h6_power": h6_power,
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
            "h6_power_target_n": H6_POWER_TARGET_N,
            "h6_power_adequate": (h6_result["n"] if h6_result else 0) >= H6_POWER_TARGET_N,
            "capital_evaluation_eligible": False,
            "h6_fonte_esperada": H6_LIVE_FONTE,
            "maturity_stage": _maturity_stage(len(rows_real)),
        },
        "predictive_quality": {
            "accuracy_d1": d1["accuracy"],
            "accuracy_d7": d7["accuracy"],
            "balanced_accuracy_d1": d1["balanced_accuracy"],
            "balanced_accuracy_d7": d7["balanced_accuracy"],
            "spearman_d7": spearman_primary,
            "majority_baseline_d7": majority_baseline,
            "score_buckets_d7": score_buckets,
        },
        "by_asset": dict(by_asset),
        "by_provider": dict(by_juiz),
        "by_provider_quality_d7": by_provider_quality,
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
        f"  Maturity stage:                 {s['maturity_stage']}",
        f"  Mature D+1 predictions:         {s['mature_d1']}",
        f"  Mature D+{PRIMARY_HORIZON} predictions:         {s['mature_d7']}",
        f"  H6 valid n (fonte={s['h6_fonte_esperada']}, pred_date>registered_at): {s['h6_valid_n']}",
        f"  H6 gate:                        {s['h6_valid_n']} / {s['h6_gate']}",
    ]
    poder = snap.get("h6_power")
    if poder is not None:
        pd_ = poder["poder"]
        lines.append(
            f"  H6 poder aprox. (n_ref={poder['n_referencia']}, B12):  "
            f"rho=0,2 -> {pd_[0.2]:.0%}  |  rho=0,3 -> {pd_[0.3]:.0%}"
        )
    lines += [
        "",
        "Predictive quality",
        "-------------------",
        f"  Accuracy D+1:              {_fmt_pct(q['accuracy_d1'])}",
        f"  Accuracy D+{PRIMARY_HORIZON}:              {_fmt_pct(q['accuracy_d7'])}",
        f"  Balanced accuracy D+1:     {_fmt_pct(q['balanced_accuracy_d1'])}",
        f"  Balanced accuracy D+{PRIMARY_HORIZON}:     {_fmt_pct(q['balanced_accuracy_d7'])}",
        f"  Spearman(score, D+{PRIMARY_HORIZON}):      {_fmt_rho(q['spearman_d7'])}",
        f"  Majority-class baseline D+{PRIMARY_HORIZON}:  {_fmt_majority_baseline(q['majority_baseline_d7'])}",
        "",
        f"  Score buckets (D+{PRIMARY_HORIZON}):",
    ]
    for bucket in q["score_buckets_d7"]:
        if bucket["n"] == 0:
            lines.append(f"    {bucket['range']:>7s}: n=0")
        else:
            lines.append(
                f"    {bucket['range']:>7s}: n={bucket['n']:<3d} "
                f"retorno médio={bucket['avg_return']:+.2f}% "
                f"%positivo={bucket['pct_positive'] * 100:.0f}%"
            )
    lines += [
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
        f"Quality by provider (D+{PRIMARY_HORIZON}, monitoramento — nunca seleção enquanto a coorte estiver aberta)",
        "-----------------------------------------------------------------------------------------",
    ]
    if not snap["by_provider_quality_d7"]:
        lines.append("  (sem dados ainda)")
    else:
        for juiz, pq in snap["by_provider_quality_d7"].items():
            spearman_txt = (
                f"{pq['spearman']:+.3f}" if pq["spearman"] is not None else "NOT_AVAILABLE"
            )
            lines.append(
                f"  {juiz:45s} n_total={pq['n_total']:<3d} n_mature={pq['n_mature']:<3d} "
                f"accuracy={_fmt_pct(pq['accuracy'])} spearman={spearman_txt}"
            )
    lines += [
        "",
        "Historical state",
        "-----------------",
        f"  H5:  {snap['historical_state']['H5']}",
        f"  H6:  {snap['historical_state']['H6']}",
        f"  V3/HMM frozen families: {snap['historical_state']['V3_frozen_families']}",
        f"  Capital authorized: {snap['historical_state']['capital_authorized']}",
    ]
    return "\n".join(lines)


def _history_record(snap: dict) -> dict:
    """Registro compacto de UMA execução — o que o usuário pediu pra rastrear
    ao longo do tempo: n, mature_n, accuracy, baseline_accuracy, spearman,
    fallback_rate, providers, H6_progress. Deriva tudo do snap já calculado,
    não recalcula nada."""
    q = snap["predictive_quality"]
    return {
        "checked_at": snap["checked_at"],
        "n": snap["sample"]["total_predictions"],
        "maturity_stage": snap["sample"]["maturity_stage"],
        "mature_n_d7": snap["sample"]["mature_d7"],
        "accuracy_d7": q["accuracy_d7"],
        "balanced_accuracy_d7": q["balanced_accuracy_d7"],
        "majority_baseline_accuracy_d7": (
            q["majority_baseline_d7"]["accuracy"] if q["majority_baseline_d7"] else None
        ),
        "spearman_d7": q["spearman_d7"]["rho"] if q["spearman_d7"] else None,
        "spearman_d7_ic_lower": q["spearman_d7"]["ic_lower"] if q["spearman_d7"] else None,
        "spearman_d7_ic_upper": q["spearman_d7"]["ic_upper"] if q["spearman_d7"] else None,
        "fallback_rate_recent": snap["pipeline"]["llm_fallbacks_recent"],
        "pipeline_status": snap["pipeline"]["status"],
        "providers": snap["by_provider"],
        "h6_valid_n": snap["sample"]["h6_valid_n"],
        "h6_gate": snap["sample"]["h6_gate"],
    }


def append_history(snap: dict, path=HISTORY_PATH) -> None:
    """Append-only: nunca lê nem reescreve linhas existentes. Uma linha JSON
    por execução — igual em espírito ao predictions_archive (migração 0016),
    mas em arquivo, porque isso é observação de processo, não dado científico
    que precise de trigger SQL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(_history_record(snap), sort_keys=True) + "\n")


def h6_status_payload(snap: dict, *, observed_at: str | None = None) -> dict:
    """Estado publicável da H6. Espelha o resultado canônico sem recalcular nada.

    `rho`/`ic_*`/`veredito` só têm valor quando n >= gate: abaixo disso
    h6_spearman_verdict devolve None de propósito, para não expor uma
    correlação prematura como se fosse sinal. Este payload preserva esse
    silêncio em vez de contorná-lo.
    """
    h6 = snap.get("h6") or {}
    poder = snap.get("h6_power")
    return {
        "trial": H6_TRIAL_NAME,
        "observed_at": observed_at or snap["checked_at"],
        "n": snap["sample"]["h6_valid_n"],
        "gate": snap["sample"]["h6_gate"],
        "gate_atingido": snap["sample"]["h6_valid_n"] >= snap["sample"]["h6_gate"],
        "fonte_esperada": snap["sample"]["h6_fonte_esperada"],
        "rho": h6.get("rho"),
        "ic_lower": h6.get("ic_lower"),
        "ic_upper": h6.get("ic_upper"),
        "veredito": h6.get("veredito"),
        "predictive_verdict": h6.get("predictive_verdict", h6.get("veredito")),
        "economic_verdict": h6.get("economic_verdict", "NOT_EVALUATED"),
        "cost_model_status": h6.get("cost_model_status", "GROSS_RETURNS_ONLY"),
        "capital_authorized": False,
        # Contexto de LEITURA (tabela estatica publicada, docs/HYPOTHESES.md
        # B12) — nunca decide o veredito nem o gate. None abaixo de n=30.
        # {"n_referencia": int, "poder": {rho: taxa}, "fonte": str} ou None.
        "poder": poder,
    }


# Resultados de write_h6_status. String nomeada em vez de bool porque "não
# gravei" tem duas causas com significados opostos: nada mudou (rotina) e me
# RECUSEI a apagar um estado publicado (incidente). Um bool colapsaria as duas.
H6_WRITTEN = "written"
H6_UNCHANGED = "unchanged"
H6_REFUSED_REGRESSION = "refused_regression"


def _h6_regride(atual: dict, novo: dict) -> bool:
    """O novo estado PERDE informação em relação ao publicado?

    As previsões são append-only (migração 0016), então o `n` elegível da H6 não
    diminui por evolução legítima do dado. Ele diminui quando a EXECUÇÃO foi
    degradada: banco vazio ou apontado para o lugar errado, ou falha de coleta de
    preço que derruba as previsões maduras (`enrich_with_realized_prices` depende
    de rede). Nesses casos o painel calcula n=0 sem erro nenhum.
    """
    if not isinstance(atual.get("n"), int):
        return False
    if novo["n"] < atual["n"]:
        return True
    # Cinto e suspensório: um veredito publicado nunca vira None em silêncio.
    return atual.get("veredito") is not None and novo["veredito"] is None


def write_h6_status(
    snap: dict, path: Path = H6_STATUS_PATH, *, allow_regression: bool = False
) -> str:
    """Publica o estado da H6. Devolve H6_WRITTEN, H6_UNCHANGED ou
    H6_REFUSED_REGRESSION.

    Idempotência: o painel roda todo dia, mas um arquivo versionado que muda
    diariamente só no timestamp produz commit de ruído e treina quem revisa a
    ignorá-lo. Por isso `observed_at` é preservado enquanto o estado for o mesmo
    — ele marca quando aquele estado foi visto PELA PRIMEIRA VEZ, não a última
    execução (essa fica no histórico append-only, que é local).

    NÃO-REGRESSÃO: este arquivo é a única janela externa para o n da H6. Uma
    execução degradada (banco vazio, path errado, falha de preço engolida) produz
    n=0 sem levantar exceção — e, sem esta trava, sobrescreveria um `n=31 /
    validado` já publicado com `n=0 / veredito=null`, resetaria `observed_at` e
    ainda pediria commit. O veredito sumiria sem deixar rastro. Regressão é
    recusada e reportada; um reset deliberado se faz apagando o arquivo (ou com
    allow_regression=True, que existe para tornar a intenção explícita).

    Falha de ESCRITA propaga de propósito: não conseguir publicar é exatamente o
    tipo de coisa que precisa ser barulhenta (mesma postura fail-fast do resto do
    projeto). Só a LEITURA do arquivo antigo é tolerante — arquivo corrompido é
    reescrito em vez de travar o painel.
    """
    novo = h6_status_payload(snap)
    if path.exists():
        try:
            atual = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # ValueError cobre json.JSONDecodeError E UnicodeDecodeError (bytes
            # não-UTF-8): ambos significam "não dá pra confiar no que está lá".
            atual = None
        if isinstance(atual, dict):
            comparavel = {k: v for k, v in novo.items() if k != "observed_at"}
            if {k: v for k, v in atual.items() if k != "observed_at"} == comparavel:
                return H6_UNCHANGED
            if not allow_regression and _h6_regride(atual, novo):
                return H6_REFUSED_REGRESSION
    path.write_text(json.dumps(novo, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return H6_WRITTEN


def main(*, chain_manifest_path: Path | None = None, feature_store_db: Path | None = None) -> int:
    manifest_path = chain_manifest_path or CHAIN_MANIFEST_PATH
    snap = asyncio.run(build_snapshot())
    print(render(snap))
    append_history(snap)
    # Selo diário da cadeia de hash do ledger de previsões + manifest público.
    # Falha de verificação é ALTA VISIBILIDADE por design (adulteração do
    # histórico invalida toda a ciência downstream) — mas não derruba o painel.
    ledger_integrity_ok = True
    try:
        from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
        from GarimpoInvestimentos.dpl.feature_store import FeatureStore
        from GarimpoInvestimentos.dpl.hash_chain import (
            chain_manifest,
            seal_chain,
            verify_chain,
        )

        ledger_db = feature_store_db or FEATURE_STORE_DB
        with FeatureStore(ledger_db) as _store:
            sealed = seal_chain(_store._conn)
            report = verify_chain(_store._conn)
            manifest = chain_manifest(_store._conn)
        if not report.ok:
            ledger_integrity_ok = False
            print(
                f"\n*** CADEIA DE HASH DO LEDGER QUEBRADA: {report.detail}\n"
                "    O histórico de previsões pode ter sido adulterado — "
                "NÃO confie em backtests até investigar."
            )
        anterior = None
        if manifest_path.exists():
            try:
                anterior = json.loads(manifest_path.read_text(encoding="utf-8"))
            except ValueError:
                anterior = None
        if not anterior or anterior.get("head") != manifest.get("head"):
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(
                f"(ledger: {sealed} nova(s) linha(s) selada(s) -> "
                f"{manifest_path.name} atualizado; commite-o junto com o h6_status.json)"
            )
    except Exception as _chain_exc:  # noqa: BLE001 — painel não pode cair por causa do selo
        ledger_integrity_ok = False
        print(f"\n*** Selo da cadeia de hash FALHOU: {type(_chain_exc).__name__}: {_chain_exc}")
    print(f"\n(histórico registrado em {HISTORY_PATH})")
    # Capturado ANTES da escrita: a trava de nao-regressao so age quando ha um
    # estado publicado para comparar, entao a PRIMEIRA publicacao e o unico
    # momento em que um n degradado passa sem ser questionado. Como o artefato
    # nunca foi commitado (verificado em 2026-08-21, git log --all vazio), essa
    # primeira vez e o caso que todo mundo vai encontrar.
    primeira_publicacao = not H6_STATUS_PATH.exists()
    # Caminho passado explicitamente: o default de write_h6_status e vinculado
    # na definicao da funcao, entao so o argumento explicito faz main() e a
    # escrita concordarem sobre QUAL arquivo esta em jogo.
    if not ledger_integrity_ok:
        print("\n*** Publicação de h6_status.json BLOQUEADA por falha de integridade do ledger.")
        return 3
    resultado = write_h6_status(snap, H6_STATUS_PATH)
    if resultado == H6_WRITTEN and primeira_publicacao:
        print(
            f"(primeira publicacao da H6 -> {H6_STATUS_PATH.name} criado; "
            f"commite-o para que o acompanhamento externo enxergue o n)"
        )
        if snap["sample"]["h6_valid_n"] == 0:
            # Mesmo nome que _load_rows() usa de fato (ver build_snapshot).
            import GarimpoInvestimentos.analyzers.backtest as _backtest_module

            print(
                "\n*** CONFIRA ANTES DE COMMITAR: n=0 na primeira publicacao.\n"
                "    Pode ser legitimo (nenhuma previsao madura posterior ao\n"
                "    registro da H6 ainda), mas e tambem o que um banco vazio ou\n"
                "    apontado para o lugar errado produz — e, sem estado anterior,\n"
                "    a trava de nao-regressao nao tem com o que comparar. Confira\n"
                f"    o caminho do banco: {_backtest_module.FEATURE_STORE_DB}"
            )
    elif resultado == H6_WRITTEN:
        print(
            f"(estado da H6 MUDOU -> {H6_STATUS_PATH.name} atualizado; "
            f"commite-o para que o acompanhamento externo enxergue o n)"
        )
    elif resultado == H6_REFUSED_REGRESSION:
        print(
            f"\n*** {H6_STATUS_PATH.name} NÃO foi tocado: esta execução viu MENOS\n"
            f"    previsões maduras da H6 do que as já publicadas. Previsões são\n"
            f"    append-only, então isso indica execução degradada (banco vazio ou\n"
            f"    errado, falha de coleta de preço), não perda real de dado.\n"
            f"    Investigue antes de confiar no painel acima. Reset deliberado:\n"
            f"    apague {H6_STATUS_PATH.name} e rode de novo."
        )
    else:
        print(f"(estado da H6 inalterado — {H6_STATUS_PATH.name} não foi tocado)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
