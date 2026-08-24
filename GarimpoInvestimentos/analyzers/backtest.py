"""Backtesting de performance das previsões.

Lê o histórico OFICIAL (Feature Store, tabela `predictions` — o CSV legado é
absorvido de forma idempotente se existir), e para cada previsão busca o
preço real do ativo em D+1, D+7 e D+30 via CoinGecko, calcula a variação
percentual e a correlação de Spearman entre o `Score` do LLM e a variação,
com IC95% (block bootstrap), estratificação por divergência e por Fonte,
e DSR contra as tentativas registradas em trials.json.

LIMITAÇÃO IMPORTANTE: o valor preditivo só amadurece com o tempo. Uma previsão
feita hoje só terá preço em D+7 daqui a 7 dias. Logo, este módulo só produz
correlação significativa depois de acumular previsões reais ao longo de semanas.
Linhas de fallback (sem análise real) são ignoradas.

Uso:
    python -m GarimpoInvestimentos.analyzers.backtest
"""

import asyncio
import csv
import math
from datetime import UTC, datetime, timedelta

from predictor_core.net import get_http_client, with_retry
from predictor_core.obs import emit_event
from predictor_core.stats import spearman_block_ci

from GarimpoInvestimentos.analyzers.trials import deflated_sharpe_ratio, load_trials, register_trial
from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.history import migrate_csv_to_store
from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB, OUTPUT_DIR
from GarimpoInvestimentos.dpl import FeatureStore
from GarimpoInvestimentos.dpl.providers.coingecko import coingecko_auth_headers

BACKTEST_CSV = OUTPUT_DIR / "garimpo_backtest.csv"
PRIMARY_HORIZON = settings.SCORE_HORIZON_DAYS  # horizonte ao qual o score se refere
HORIZONS = sorted({1, 7, 30, PRIMARY_HORIZON})
FALLBACK_MARKER = "fallback aplicado"

# Cadência de emissão assumida da coleta prospectiva (garimpo_fase1.py roda uma vez
# por dia UTC). Auditoria de 2026-08-19: block_length=5 (default de spearman_block_ci)
# era MENOR que o horizonte de 7 dias da H5/H6 — um bloco de 5 observações
# consecutivas não cobre a janela inteira de overlap entre previsões diárias com
# horizonte D+7, subestimando a dependência serial e produzindo IC95% mais estreito
# do que o real. Ver docs/HYPOTHESES.md (limitação histórica registrada).
EMISSION_INTERVAL_DAYS = 1


def overlap_block_length(
    horizon_days: int, *, emission_interval_days: int = EMISSION_INTERVAL_DAYS
) -> int:
    """Tamanho de bloco mínimo defensável para o block bootstrap de Spearman.

    Regra: com emissão a cada `emission_interval_days` e horizonte de `horizon_days`,
    cada retorno realizado contamina até `ceil(horizon_days / emission_interval_days)`
    previsões vizinhas (overlap span). O bloco do bootstrap precisa ser >= esse span
    para capturar a dependência serial inteira — um bloco mais curto que o overlap
    deixa vazar autocorrelação não modelada para fora do bloco, estreitando o IC.
    `spearman_block_ci` já satura o bloco em `n//3` para amostras pequenas; aqui só
    definimos o PISO metodológico, nunca um valor menor que o overlap real.
    """
    if emission_interval_days <= 0:
        raise ValueError("emission_interval_days deve ser positivo")
    overlap_span = -(-horizon_days // emission_interval_days)  # ceil sem importar math
    return max(1, overlap_span)


# Spearman + block bootstrap vivem em core/stats.py (puro, testável sem .env) —
# importados acima. A significância (IC) entra no _report. block_length é sempre
# passado explicitamente (overlap_block_length), nunca o default da função (5).


# ---------- CoinGecko histórico ----------
@with_retry()
async def _fetch_price(client, coin_id: str, day: datetime) -> float | None:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history"
    params = {"date": day.strftime("%d-%m-%Y"), "localization": "false"}
    resp = await client.get(url, params=params, headers=coingecko_auth_headers())
    resp.raise_for_status()
    data = resp.json()
    return data.get("market_data", {}).get("current_price", {}).get("usd")


async def _price_on(client, coin_id: str, day: datetime) -> float | None:
    """Preço em USD num dia específico; None se não houver dado (após retry de transitórios)."""
    try:
        return await _fetch_price(client, coin_id, day)
    except Exception:
        return None


async def _realized_price(
    store, client, ativo: str, fonte: str, day: datetime
) -> tuple[float | None, str | None]:
    """Preço realizado com régua OFFLINE-FIRST: primeiro a Feature Store (mesma
    família de fontes da previsão — a equivalência mediu até 7.8pp de diff entre
    fontes; medir noutra régua adiciona ruído), fallback CoinGecko via rede só
    quando a store não tem o dia. Retorna (preço, carimbo_da_medição):
    'store:<source>' | 'coingecko' | None. O sleep de rate limit só acontece
    quando a rede foi de fato usada."""
    hit = store.close_on(ativo, "1d", day, prefer_consensus=(fonte == "dpl:consensus"))
    if hit:
        return hit[0], f"store:{hit[1]}"
    price = await _price_on(client, ativo, day)
    await asyncio.sleep(1.5)  # respeita o rate limit do free tier (só no caminho de rede)
    return price, ("coingecko" if price is not None else None)


def _load_rows() -> list[dict]:
    """Lê o histórico OFICIAL (Feature Store, tabela predictions — passo 4),
    absorvendo antes o CSV legado se existir (idempotente; fonte vazia → 'direct').
    Descarta linhas de fallback de LLM e sem preço/data válidos. Dedup é estrutural
    (PK ativo+ts na store)."""
    with FeatureStore(FEATURE_STORE_DB) as store:
        n = migrate_csv_to_store(store)
        if n:
            print(f"🗄️ Histórico legado absorvido na Feature Store: {n} linha(s) do CSV.")
        preds = store.read_predictions()
    rows = []
    for r in preds:
        # Exclusão de fallback do LLM: carimbo estrutural (0009) para linhas novas;
        # marcador no resumo cobre o legado (llm_fallback NULL = pré-flag).
        if r.get("llm_fallback") == 1:
            continue
        if FALLBACK_MARKER in (r.get("resumo") or ""):
            continue
        try:
            pred_date = datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")
            price = float(r["price_usd"])
            score = float(r["score"])
        except (KeyError, ValueError, TypeError):
            continue
        if price <= 0:
            continue
        rows.append(
            {
                "ativo": (r.get("ativo") or "").lower(),
                "score": score,
                "pred_date": pred_date,
                "pred_price": price,
                "divergencia": 1 if r.get("divergencia") else 0,
                # estratificação obrigatória: a equivalência mediu até 7.8pp de diff
                # nos change_* entre fontes — poolar sem estratificar contamina o n.
                "fonte": (r.get("fonte") or "").strip() or "direct",
                # 1 = LLM pontuou com input empobrecido; 0 = completo; None = pré-0008
                # (não medido na época) — o _report estratifica 1 vs 0.
                "degradado": r.get("input_degradado"),
                # Carimbo do juiz (provider:modelo:hash) — no modo multi cada ativo
                # tem o seu; o _report estratifica para nunca poolar calibrações.
                "juiz": (r.get("juiz") or "").strip(),
                # 0010/0011: fontes de notícias e seleção são populações
                # distintas. NULL do legado não pode fingir equivalência.
                "news_provider": (r.get("news_provider") or "legacy:unknown").strip(),
                "collection_policy": (r.get("collection_policy") or "legacy:unknown").strip(),
            }
        )
    return rows


async def enrich_with_realized_prices(rows: list[dict]) -> list[dict]:
    """Busca o preço realizado em D+1/D+7/D+30 (+PRIMARY_HORIZON) pra cada previsão
    e calcula var_d{h}_pct. ÚNICA fonte de verdade desse cálculo — `run()` (backtest
    oficial) e qualquer painel/relatório derivado (ex. quality_snapshot.py) DEVEM
    reusar esta função, nunca reimplementar o loop de _realized_price: divergir
    daqui seria ter dois critérios de maturidade diferentes no mesmo projeto."""
    today = datetime.now(UTC).replace(tzinfo=None)
    enriched = []
    async with get_http_client() as client:
        with FeatureStore(FEATURE_STORE_DB) as store:
            for row in rows:
                out = dict(row)
                for h in HORIZONS:
                    target = row["pred_date"] + timedelta(days=h)
                    if target > today:
                        out[f"price_d{h}"] = None
                        out[f"var_d{h}_pct"] = None
                        out[f"medida_d{h}"] = None
                        continue
                    price, medida = await _realized_price(
                        store, client, row["ativo"], row["fonte"], target
                    )
                    out[f"price_d{h}"] = price
                    out[f"medida_d{h}"] = medida  # régua usada: store:<src> | coingecko
                    out[f"var_d{h}_pct"] = (
                        round((price - row["pred_price"]) / row["pred_price"] * 100, 2)
                        if price is not None  # era `if price` — falsy-check engoliria 0.0
                        else None
                    )
                enriched.append(out)
    return enriched


async def run():
    rows = _load_rows()
    if not rows:
        print(
            "⚠️ Nenhuma previsão válida no histórico oficial "
            "(Feature Store, tabela predictions — só fallback ou vazio)."
        )
        return

    enriched = await enrich_with_realized_prices(rows)

    _write(enriched)
    _report(enriched)
    _metrics(enriched, PRIMARY_HORIZON)
    close_trial_sharpes(enriched, PRIMARY_HORIZON)
    close_h6_inverted_signal(enriched, PRIMARY_HORIZON)
    h6_result = h6_spearman_verdict(enriched, PRIMARY_HORIZON)
    if h6_result is not None:
        print_h6_power_context(h6_result["n"], h6_result.get("veredito"))


def _write(enriched: list[dict]) -> None:
    cols = [
        "ativo",
        "score",
        "pred_date",
        "pred_price",
        "fonte",
        "juiz",
        "news_provider",
        "collection_policy",
        "degradado",
        "price_d1",
        "var_d1_pct",
        "medida_d1",
        "price_d7",
        "var_d7_pct",
        "medida_d7",
        "price_d30",
        "var_d30_pct",
        "medida_d30",
    ]
    with open(BACKTEST_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in enriched:
            w.writerow({c: row.get(c, "") for c in cols})
    print(f"💾 Backtest gravado em {BACKTEST_CSV}")


def _ranks(xs: list[float]) -> list[float]:
    """Ranks com média para empates (Spearman clássico), stdlib puro."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _spearman_rho(xs: list[float], ys: list[float]) -> float | None:
    """Spearman ponto-estimado sem numpy/scipy. None se variância nula."""
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return cov / (vx * vy) ** 0.5


# Monitor de estabilidade do sinal (recomendação de pesquisa externa
# 2026-08-24): a réplica de Baker-Wurgler (2002-2023) mostra proxies de
# sentimento TROCANDO de direção entre regimes — e a H6 é uma hipótese de
# sinal invertido. Sem monitoramento contínuo, o sinal pode virar e ninguém
# nota até o próximo gate. Janela rolante sobre os pares em ORDEM TEMPORAL.
ROLLING_WINDOW = 60
ROLLING_MIN_N = 30


def rolling_flip_check(enriched: list[dict], horizon: int) -> tuple[float, float, int] | None:
    """Compara o Spearman da janela recente (últimos ROLLING_WINDOW pontos)
    com o da amostra toda no horizonte dado. Retorna (rho_geral, rho_recente,
    n_janela) quando ambos são computáveis — o chamador decide o alarme."""
    key = f"var_d{horizon}_pct"
    rows = [
        (r.get("pred_date") or datetime.min, r["score"], r[key])
        for r in enriched
        if r.get(key) is not None and r.get("score") is not None
    ]
    rows.sort(key=lambda t: t[0])
    if len(rows) < ROLLING_MIN_N + 10:
        return None
    overall = _spearman_rho([s for _, s, _ in rows], [v for _, _, v in rows])
    tail = rows[-ROLLING_WINDOW:]
    if len(tail) < ROLLING_MIN_N:
        return None
    recent = _spearman_rho([s for _, s, _ in tail], [v for _, _, v in tail])
    if overall is None or recent is None:
        return None
    return overall, recent, len(tail)


def _report(enriched: list[dict]) -> None:
    for h in HORIZONS:
        # pairs em ORDEM TEMPORAL (enriched preserva a ordem do histórico) — o block
        # bootstrap depende disso para capturar a dependência serial dos horizontes.
        pairs = [
            (r["score"], r[f"var_d{h}_pct"]) for r in enriched if r.get(f"var_d{h}_pct") is not None
        ]
        n = len(pairs)
        marca = "  ← horizonte principal" if h == PRIMARY_HORIZON else ""
        if n < 4:
            print(
                f"D+{h}: dados insuficientes ({n} ponto(s) com preço) — "
                f"aguarde previsões maduras.{marca}"
            )
            continue
        rho, lo, hi = spearman_block_ci(pairs, block_length=overlap_block_length(h))
        if rho is None:
            print(f"D+{h}: variância nula em score/retorno (n={n}) — sem correlação.{marca}")
            continue
        if lo is None or hi is None:
            print(f"D+{h}: Spearman = {rho:+.3f} (n={n}) — IC indisponível.{marca}")
            continue
        # IC que NÃO cruza zero = sinal; cruza zero = ainda é ruído (transforma
        # história convincente em decisão defensável — a régua dos domínios irmãos).
        veredito = "validado (IC não cruza 0)" if (lo > 0 or hi < 0) else "RUÍDO (IC cruza 0)"
        print(
            f"D+{h}: Spearman(Score, variação) = {rho:+.3f}  "
            f"[IC95% {lo:+.3f} a {hi:+.3f}]  (n={n}) — {veredito}{marca}"
        )
        flip = rolling_flip_check(enriched, h)
        if flip is not None:
            geral, recente, nj = flip
            if (geral > 0) != (recente > 0):
                print(
                    f"  ⚠️  FLIP DE SINAL em D+{h}: janela recente (n={nj}) "
                    f"rho={recente:+.3f} vs amostra toda rho={geral:+.3f} — "
                    "o sinal pode ter invertido de regime (documentado em "
                    "Baker-Wurgler); investigue antes de confiar no veredito."
                )
        # Estratificação por divergência LLM-vs-técnico (só no horizonte principal):
        # a matemática prova se as previsões tagueadas (alucinação?) perdem alpha.
        if h == PRIMARY_HORIZON:
            key = f"var_d{h}_pct"
            aligned = [
                (r["score"], r[key])
                for r in enriched
                if r.get(key) is not None and not r.get("divergencia")
            ]
            flagged = [
                (r["score"], r[key])
                for r in enriched
                if r.get(key) is not None and r.get("divergencia")
            ]
            for label, sub in (
                ("alinhadas (LLM≈técnico)", aligned),
                ("divergentes (LLM×técnico)", flagged),
            ):
                if len(sub) >= 4:
                    rs, los, his = spearman_block_ci(sub, block_length=overlap_block_length(h))
                    if rs is not None and los is not None:
                        print(
                            f"      └ {label}: Spearman {rs:+.3f} "
                            f"[IC95% {los:+.3f} a {his:+.3f}] (n={len(sub)})"
                        )
            # Estratificação por INPUT DEGRADADO (0008): previsões em que o LLM
            # pontuou sem indicadores/notícias são população distinta — poolar
            # esconderia perda de alpha. NULL (pré-flag) fica fora dos estratos.
            completas = [
                (r["score"], r[key])
                for r in enriched
                if r.get(key) is not None and r.get("degradado") == 0
            ]
            degradadas = [
                (r["score"], r[key])
                for r in enriched
                if r.get(key) is not None and r.get("degradado") == 1
            ]
            if degradadas:
                for label, sub in (("input completo", completas), ("input DEGRADADO", degradadas)):
                    if len(sub) >= 4:
                        rs, los, his = spearman_block_ci(sub, block_length=overlap_block_length(h))
                        if rs is not None and los is not None:
                            print(
                                f"      └ {label}: Spearman {rs:+.3f} "
                                f"[IC95% {los:+.3f} a {his:+.3f}] (n={len(sub)})"
                            )
                    elif sub:
                        print(f"      └ {label}: n={len(sub)} (insuficiente p/ IC)")
            # Estratificação por FONTE de dados (obrigatória — equivalência mediu
            # até 7.8pp de diff nos change_* entre fontes; fontes distintas =
            # calibrações distintas do LLM, nunca poolar sem mostrar os estratos).
            fontes = sorted({r.get("fonte", "direct") for r in enriched})
            fonte_counts = {}
            for fonte in fontes:
                sub = [
                    (r["score"], r[key])
                    for r in enriched
                    if r.get(key) is not None and r.get("fonte", "direct") == fonte
                ]
                fonte_counts[fonte] = len(sub)
                if len(sub) >= 4:
                    rs, los, his = spearman_block_ci(sub, block_length=overlap_block_length(h))
                    if rs is not None and los is not None:
                        print(
                            f"      └ fonte={fonte}: Spearman {rs:+.3f} "
                            f"[IC95% {los:+.3f} a {his:+.3f}] (n={len(sub)})"
                        )
                    elif sub:
                        print(f"      └ fonte={fonte}: n={len(sub)} (insuficiente p/ IC)")
            # Notícias e filtros/budgets não são detalhes operacionais: mudam
            # o input ou a população. Reportar o estrato impede consenso falso.
            news_counts = {}
            for provider in sorted({r.get("news_provider", "legacy:unknown") for r in enriched}):
                sub = [
                    (r["score"], r[key])
                    for r in enriched
                    if r.get(key) is not None and r.get("news_provider") == provider
                ]
                news_counts[provider] = len(sub)
                if len(sub) >= 4:
                    rs, los, his = spearman_block_ci(sub, block_length=overlap_block_length(h))
                    if rs is not None and los is not None:
                        print(
                            f"      └ news_provider={provider}: Spearman {rs:+.3f} "
                            f"[IC95% {los:+.3f} a {his:+.3f}] (n={len(sub)})"
                        )
                elif sub:
                    print(f"      └ news_provider={provider}: n={len(sub)} (insuficiente p/ IC)")
            policy_counts = {}
            for policy in sorted({r.get("collection_policy", "legacy:unknown") for r in enriched}):
                sub = [
                    (r["score"], r[key])
                    for r in enriched
                    if r.get(key) is not None and r.get("collection_policy") == policy
                ]
                policy_counts[policy] = len(sub)
                label = policy if policy == "legacy:unknown" else "configured"
                if len(sub) >= 4:
                    rs, los, his = spearman_block_ci(sub, block_length=overlap_block_length(h))
                    if rs is not None and los is not None:
                        print(
                            f"      └ collection_policy={label}: Spearman {rs:+.3f} "
                            f"[IC95% {los:+.3f} a {his:+.3f}] (n={len(sub)})"
                        )
                elif sub:
                    print(f"      └ collection_policy={label}: n={len(sub)} (insuficiente p/ IC)")
            # Estratificação por JUIZ (H5 / modo multi): cada provedor:modelo é uma
            # calibração distinta — o Sharpe agregado da trial multi só é interpretável
            # ao lado dos estratos por juiz (um juiz individual só se julga com o n
            # mínimo no SEU estrato, ver critério da H5).
            juizes = sorted({r.get("juiz", "") for r in enriched if r.get("juiz")})
            if len(juizes) > 1:
                for juiz in juizes:
                    sub = [
                        (r["score"], r[key])
                        for r in enriched
                        if r.get(key) is not None and r.get("juiz") == juiz
                    ]
                    if len(sub) >= 4:
                        rs, los, his = spearman_block_ci(sub, block_length=overlap_block_length(h))
                        if rs is not None and los is not None:
                            print(
                                f"      └ juiz={juiz}: Spearman {rs:+.3f} "
                                f"[IC95% {los:+.3f} a {his:+.3f}] (n={len(sub)})"
                            )
                    elif sub:
                        print(f"      └ juiz={juiz}: n={len(sub)} (insuficiente p/ IC)")
            # PAYOFF: o cripto nasce emitindo o evento estruturado do pedágio (Modo B
            # validado). ic_lower nas métricas; a divergência (alucinação?) nos metadados.
            emit_event(
                "previsao_cripto",
                "toll_passed",
                metrics={
                    "spearman": round(rho, 4),
                    "ic_lower": round(lo, 4),
                    "ic_upper": round(hi, 4),
                    "n": n,
                },
                metadata={
                    "horizon_days": h,
                    "veredito": veredito,
                    "n_divergentes": len(flagged),
                    "n_alinhadas": len(aligned),
                    "n_por_fonte": fonte_counts,
                    "n_por_news_provider": news_counts,
                    "n_por_collection_policy": policy_counts,
                },
            )


def close_trial_sharpes(
    enriched: list[dict], horizon: int, *, trials_path=None, threshold: float | None = None
) -> dict[str, float]:
    """Fecha o ciclo do Experiment Registry: grava em trials.json o Sharpe
    POR-TRADE observado de cada estrato de Fonte com n≥3 sinais fortes maduros.

    Antes era manual (as trials v1/v2 aguardavam alguém copiar o número) — e
    denominador que depende de disciplina humana esquece. A trial casada é a que
    tem params.fonte == fonte do estrato e params.horizonte_dias == horizon;
    o Sharpe usa os MESMOS retornos da 'Estratégia' de _metrics (score ≥ limiar),
    na mesma unidade por-período que o DSR consome. Sem trial casada ou n<3, o
    estrato é pulado (nunca cria trial nova — criar tentativa é decisão humana).

    ERAS: quando MAIS DE UMA trial casa (fonte, horizonte) — ex.: a
    v2-dpl-gemini-h7 encerrada e a v2-dpl-multi-h7 sucessora têm os mesmos
    params de casamento — o estrato é dividido por época: cada previsão pertence
    à trial vigente na sua data (fronteira = registered_at da trial seguinte;
    a primeira absorve a pré-história, cobrindo registros retroativos). Cada era
    matura a SUA trial — o Sharpe da encerrada congela com os dados dela, e a
    sucessora nunca herda dados do juiz anterior.
    Retorna {name: sharpe} do que foi atualizado."""
    thr = settings.LIMIAR_SCORE_MINIMO if threshold is None else threshold
    key = f"var_d{horizon}_pct"
    trials = load_trials(trials_path)
    updated: dict[str, float] = {}

    def _registered_at(t: dict) -> datetime:
        raw = (t.get("registered_at") or "").replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw).replace(tzinfo=None)
        except ValueError:
            return datetime.min

    fontes = {r.get("fonte", "direct") for r in enriched}
    for fonte in sorted(fontes):
        matching = [
            t
            for t in trials
            if t.get("params", {}).get("fonte") == fonte
            and t.get("params", {}).get("horizonte_dias") == horizon
        ]
        if not matching:
            continue
        matching.sort(key=_registered_at)
        for i, t in enumerate(matching):
            start = _registered_at(t) if i > 0 else datetime.min
            end = _registered_at(matching[i + 1]) if i + 1 < len(matching) else datetime.max
            rets = [
                r[key] / 100
                for r in enriched
                if r.get(key) is not None
                and r.get("fonte", "direct") == fonte
                and r["score"] >= thr
                and start <= r.get("pred_date", datetime.min) < end
            ]
            if len(rets) < 3:
                continue
            avg = sum(rets) / len(rets)
            std = (sum((x - avg) ** 2 for x in rets) / (len(rets) - 1)) ** 0.5
            if not std:
                continue
            sharpe = round(avg / std, 4)
            p = t.get("params", {})
            register_trial(
                t["name"],
                params=p,
                sharpe=sharpe,
                notes=t.get("notes", ""),
                path=trials_path,
                **{k: t[k] for k in ("features_used", "train_period", "test_period") if k in t},
            )
            updated[t["name"]] = sharpe
            print(
                f"📒 trials.json: sharpe por-trade de '{t['name']}' "
                f"atualizado → {sharpe:+.4f} (fonte={fonte}, n={len(rets)}, "
                f"era {i + 1}/{len(matching)})"
            )
    return updated


H6_TRIAL_NAME = "h6-sinal-invertido-d7"
H6_LIVE_FONTE = "dpl:fallback"  # fonte real da coleta em curso (H5/multi-juiz)
H6_MIN_N = 30  # n mínimo do critério pré-registrado (idêntico ao H4/H5)

#: Referência ESTÁTICA publicada em docs/HYPOTHESES.md (B12), medida em
#: 2026-08-21 com o critério canônico (spearman_block_ci + overlap_block_length,
#: n_sim=150, n_boot=400 — reproduz a medição de referência com n_boot=10.000
#: dentro do ruído de simulação, o que valida a redução). NÃO é recalculada em
#: runtime: Monte Carlo novo a cada noite teria ruído de simulação próprio, e
#: um "poder" que oscila de execução em execução confundiria mais do que
#: ajudaria — isto é contexto de leitura, não uma medição científica nova.
#: Para recalcular do zero (outro horizonte, outra grade de rho), use
#: `GarimpoInvestimentos.analyzers.gate_power.power_table()` diretamente.
H6_PUBLISHED_POWER_TABLE: dict[int, dict[float, float]] = {
    30: {0.0: 0.067, 0.1: 0.113, 0.2: 0.147, 0.3: 0.293, 0.5: 0.620},
    60: {0.0: 0.060, 0.1: 0.113, 0.2: 0.233, 0.3: 0.473, 0.5: 0.933},
    120: {0.0: 0.073, 0.1: 0.247, 0.2: 0.593, 0.3: 0.827, 0.5: 1.000},
    250: {0.0: 0.060, 0.1: 0.347, 0.2: 0.813, 0.3: 1.000, 0.5: 1.000},
    500: {0.0: 0.080, 0.1: 0.653, 0.2: 0.973, 0.3: 1.000, 0.5: 1.000},
}


def h6_power_context(n: int) -> dict | None:
    """Poder aproximado no `n` atual — NÃO muda o gate, NÃO decide o veredito,
    só qualifica a leitura de quem olhar o resultado. Lê `H6_PUBLISHED_POWER_
    TABLE` pelo maior `n` tabulado que seja <= n (leitura CONSERVADORA: nunca
    superestima o poder que o `n` atual de fato tem). Devolve None abaixo de
    n=30 — nenhum ponto tabulado alcançável ainda."""
    aplicaveis = [k for k in H6_PUBLISHED_POWER_TABLE if k <= n]
    if not aplicaveis:
        return None
    referencia = max(aplicaveis)
    return {
        "n_referencia": referencia,
        "poder": dict(H6_PUBLISHED_POWER_TABLE[referencia]),
        "fonte": "docs/HYPOTHESES.md B12 (tabela estatica, nao recalculada em runtime)",
    }


def print_h6_power_context(n: int, veredito: str | None = None) -> dict | None:
    """Imprime o poder aproximado do gate no `n` atual, AO LADO do veredito que
    `h6_spearman_verdict` já imprimiu — nunca de dentro dela. Esta função fica
    deliberadamente fora do bloco que `scripts/freeze_h6_definition.py`
    congela: enriquecer a LEITURA de um resultado nunca deveria forçar
    re-congelar a definição científica da H6 (threshold, horizonte, fonte,
    trava anti-data-snooping) — são preocupações independentes. Devolve o
    contexto de poder (ou None abaixo de n=30), para quem quiser reaproveitar
    o valor em vez de só o texto impresso."""
    poder = h6_power_context(n)
    if poder is None:
        return None
    p_ = poder["poder"]
    print(
        f"   poder aprox. (n_ref={poder['n_referencia']}, tabela estática "
        f"docs/HYPOTHESES.md B12): rho=0,2 → {p_[0.2]:.0%}  |  "
        f"rho=0,3 → {p_[0.3]:.0%}"
    )
    if veredito and veredito.startswith("RUIDO"):
        print(
            f"   lembrete: em n={n}, RUÍDO pode ser ausência de evidência, "
            f"não evidência de ausência — poder para rho=0,2 é só "
            f"{p_[0.2]:.0%} aqui (docs/HYPOTHESES.md B12)."
        )
    return poder


def close_h6_inverted_signal(
    enriched: list[dict], horizon: int, *, trials_path=None, threshold: float | None = None
) -> float | None:
    """H6 (docs/HYPOTHESES.md): as 3 encarnações anteriores da família
    'score do LLM prevê retorno D+7' mostraram correlação NEGATIVA e
    significativa — esta função testa a leitura INVERTIDA (score BAIXO =
    sinal de alta) sem tocar em coleta, prompt ou modelo: só reinterpreta o
    score que já é gravado.

    Pré-registrada com `params.fonte` deliberadamente reservado
    (nunca casa com `predictions.fonte` real), então NÃO passa pelo
    casamento genérico de `close_trial_sharpes` — essa função é o mecanismo
    explícito e separado, com uma trava anti-data-snooping que o casamento
    genérico não tem: só conta previsões com `pred_date` POSTERIOR ao
    `registered_at` da própria trial H6 (dado genuinamente novo, nunca
    reaproveita o histórico que já inspirou a hipótese). Sinal invertido =
    score ≤ (100 − limiar), espelho exato do limiar original (mesma
    distância do centro 50). Atualiza trials.json só com n≥3; nunca cria
    trial nova (se H6 não estiver registrada nesta instância, é no-op).
    Retorna o sharpe ou None."""
    trials = load_trials(trials_path)
    h6 = next((t for t in trials if t.get("name") == H6_TRIAL_NAME), None)
    if h6 is None:
        return None

    raw = (h6.get("registered_at") or "").replace("Z", "+00:00")
    try:
        registered_at = datetime.fromisoformat(raw).replace(tzinfo=None)
    except ValueError:
        return None

    thr = settings.LIMIAR_SCORE_MINIMO if threshold is None else threshold
    inverted_thr = 100 - thr
    key = f"var_d{horizon}_pct"
    rets = [
        r[key] / 100
        for r in enriched
        if r.get(key) is not None
        and r.get("fonte", "direct") == H6_LIVE_FONTE
        and r["score"] <= inverted_thr
        and r.get("pred_date", datetime.min) > registered_at
    ]
    if len(rets) < 3:
        return None
    avg = sum(rets) / len(rets)
    std = (sum((x - avg) ** 2 for x in rets) / (len(rets) - 1)) ** 0.5
    if not std:
        return None
    sharpe = round(avg / std, 4)
    register_trial(
        H6_TRIAL_NAME,
        params=h6["params"],
        sharpe=sharpe,
        notes=h6.get("notes", ""),
        path=trials_path,
    )
    print(
        f"📒 trials.json: sharpe (sinal invertido) de '{H6_TRIAL_NAME}' "
        f"atualizado → {sharpe:+.4f} (n={len(rets)}, score≤{inverted_thr:.0f}, "
        f"só dado após {registered_at.isoformat()})"
    )
    return sharpe


def h6_spearman_verdict(enriched: list[dict], horizon: int, *, trials_path=None) -> dict | None:
    """Critério de veredito PRÉ-REGISTRADO da H6 (docs/HYPOTHESES.md), idêntico
    ao do H4/H5 mas sobre a leitura INVERTIDA do score: Spearman IC95 (block
    bootstrap) não cruzando zero, positivo, com n >= H6_MIN_N previsões
    maduras. O `sharpe` que `close_h6_inverted_signal` grava é auxiliar
    (P&L de um corte por limiar) — este é o critério que de fato decide
    VALIDADO/RUIDO, e não existia cálculo automatizado até aqui: o resto do
    módulo só computa Spearman para a leitura ORIGINAL do score (_report).

    Leitura invertida = `100 - score` (mesmo espelhamento em torno de 50 que
    `inverted_thr` usa para o limiar), correlacionado com o retorno cru —
    matematicamente equivale a negar o Spearman(score, retorno) original, mas
    calculado explicitamente para reaproveitar a MESMA regra de veredito do
    juiz da Fase 1 (`lo > 0 or hi < 0`), sem depender de inverter o sinal do
    IC de cabeça.

    Mesma trava anti-data-snooping do `close_h6_inverted_signal`: só conta
    `pred_date` POSTERIOR ao `registered_at` da própria trial H6, só
    `fonte == H6_LIVE_FONTE`. NÃO grava nada em trials.json — o veredito em
    prosa desta família sempre foi curadoria humana (ver notes de
    v2-dpl-multi-h7), não escrita automática; esta função só reporta e emite
    evento, como `_report` já faz para o critério principal.

    Abaixo de H6_MIN_N deliberadamente NÃO imprime rho/IC (só a contagem):
    expor uma correlação prévia ao n mínimo convidaria exatamente o erro que
    o pré-registro existe para prevenir (tratar um número imaturo como sinal).

    Retorna None se a H6 não estiver registrada (no-op); senão um dict com
    n, rho, ic_lower, ic_upper e veredito."""
    trials = load_trials(trials_path)
    h6 = next((t for t in trials if t.get("name") == H6_TRIAL_NAME), None)
    if h6 is None:
        return None

    raw = (h6.get("registered_at") or "").replace("Z", "+00:00")
    try:
        registered_at = datetime.fromisoformat(raw).replace(tzinfo=None)
    except ValueError:
        return None

    key = f"var_d{horizon}_pct"
    pairs = [
        (100 - r["score"], r[key])
        for r in enriched
        if r.get(key) is not None
        and r.get("fonte", "direct") == H6_LIVE_FONTE
        and r.get("pred_date", datetime.min) > registered_at
    ]
    n = len(pairs)
    if n < H6_MIN_N:
        print(
            f"📊 H6 (sinal invertido, Spearman/IC95): n={n} de {H6_MIN_N} "
            f"— sem veredito ainda (critério pré-registrado exige n>={H6_MIN_N})."
        )
        return {
            "n": n,
            "rho": None,
            "ic_lower": None,
            "ic_upper": None,
            "veredito": f"aguardando n>={H6_MIN_N} (n={n})",
        }

    rho, lo, hi = spearman_block_ci(pairs, block_length=overlap_block_length(horizon))
    if rho is None or lo is None or hi is None:
        print(
            f"📊 H6 (sinal invertido, Spearman/IC95): n={n}, IC indisponível "
            f"(variância nula em score/retorno)."
        )
        return {"n": n, "rho": rho, "ic_lower": lo, "ic_upper": hi, "veredito": "IC indisponivel"}

    veredito = "validado (IC nao cruza 0)" if (lo > 0 or hi < 0) else "RUIDO (IC cruza 0)"
    print(
        f"📊 H6 (sinal invertido, Spearman/IC95) D+{horizon}: "
        f"rho={rho:+.3f}  [IC95% {lo:+.3f} a {hi:+.3f}]  (n={n}) — {veredito}"
    )
    emit_event(
        "previsao_cripto",
        "h6_spearman_verdict",
        metrics={
            "spearman": round(rho, 4),
            "ic_lower": round(lo, 4),
            "ic_upper": round(hi, 4),
            "n": n,
        },
        metadata={"horizon_days": horizon, "veredito": veredito, "trial": H6_TRIAL_NAME},
    )
    return {"n": n, "rho": rho, "ic_lower": lo, "ic_upper": hi, "veredito": veredito}


def _metrics(enriched: list[dict], horizon: int) -> None:
    """Precisão direcional, hit rate e estratégia vs benchmark BTC no horizonte principal.

    Nota: ignora custos de transação e usa amostra pequena — interpretar com cautela
    até o n crescer.
    """
    threshold = settings.LIMIAR_SCORE_MINIMO
    key = f"var_d{horizon}_pct"
    mature = [r for r in enriched if r.get(key) is not None]
    n = len(mature)
    print(f"\n===== Métricas (horizonte D+{horizon}, n={n}) =====")
    if n < 3:
        print("  dados insuficientes — aguarde previsões maduras.")
        return

    # Acurácia direcional: score > 50 prevê alta; score < 50 prevê queda
    directional = [r for r in mature if r["score"] != 50]
    if directional:
        hits = sum(1 for r in directional if (r["score"] > 50) == (r[key] > 0))
        print(
            f"  Acurácia direcional: {hits}/{len(directional)} = {hits / len(directional) * 100:.1f}%"
        )

    # Hit rate dos sinais fortes (score >= limiar): % que fechou positivo
    strong = [r for r in mature if r["score"] >= threshold]
    if strong:
        pos = sum(1 for r in strong if r[key] > 0)
        print(
            f"  Hit rate (score ≥ {threshold}): {pos}/{len(strong)} positivos = {pos / len(strong) * 100:.1f}%"
        )

        # Estratégia fictícia: comprar os sinais fortes; retorno médio + Sharpe simplificado
        rets = [r[key] for r in strong]
        avg = sum(rets) / len(rets)
        line = f"  Estratégia (score ≥ {threshold}): retorno médio {avg:+.2f}%"
        if len(rets) >= 2:
            std = (sum((x - avg) ** 2 for x in rets) / (len(rets) - 1)) ** 0.5
            if std:
                line += f" | Sharpe simpl. {avg / std:.2f}"
        print(line)
        # DSR: o Sharpe acima contra o MÁXIMO esperado por sorte dado o nº de
        # configurações já tentadas (trials.json). Sem isso, testar N configs e
        # reportar a melhor fabrica significância — o desconto que ninguém media.
        trials = load_trials()
        if trials and len(rets) >= 3:
            # Trials abertas têm sharpe=null (ex.: H6 aguardando gate) — não
            # entram no denominador do máximo-por-sorte (auditoria externa).
            d = deflated_sharpe_ratio(
                [x / 100 for x in rets],
                [t["sharpe"] for t in trials if t.get("sharpe") is not None],
            )
            if not math.isnan(d["dsr"]):  # NaN check legível (era d != d)
                print(
                    f"  DSR (N={d['n_trials']} tentativas registradas): "
                    f"P(SR > máx-por-sorte) = {d['dsr']:.2f} | SR0 = {d['sr0']:.3f} "
                    f"— {'passa' if d['dsr'] >= 0.95 else 'NÃO passa'} o corte 0.95"
                )
    else:
        print(f"  Hit rate (score ≥ {threshold}): nenhum sinal forte ainda")

    # Benchmark: Bitcoin buy & hold (média das previsões de bitcoin no mesmo horizonte)
    btc = [r[key] for r in mature if r["ativo"] == "bitcoin"]
    if btc:
        print(f"  Benchmark BTC (buy & hold): retorno médio {sum(btc) / len(btc):+.2f}%")


if __name__ == "__main__":
    asyncio.run(run())
