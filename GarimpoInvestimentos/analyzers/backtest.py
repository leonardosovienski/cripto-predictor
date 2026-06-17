"""Backtesting de performance das previsões (Fase 2 — esqueleto).

Lê o histórico (`output/garimpo_historico.csv`), e para cada previsão busca o
preço real do ativo em D+1, D+7 e D+30 via CoinGecko, calcula a variação
percentual e a correlação de Spearman entre o `Score` do Gemini e a variação.

LIMITAÇÃO IMPORTANTE: o valor preditivo só amadurece com o tempo. Uma previsão
feita hoje só terá preço em D+7 daqui a 7 dias. Logo, este módulo só produz
correlação significativa depois de acumular previsões reais ao longo de semanas.
Linhas de fallback (sem análise real) são ignoradas.

Uso:
    python -m GarimpoInvestimentos.analyzers.backtest
"""
import asyncio
import csv
from datetime import datetime, timedelta, timezone

from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.http_client import get_http_client
from GarimpoInvestimentos.core.paths import OUTPUT_DIR
from GarimpoInvestimentos.core.retry import with_retry
from predictor_core.stats import spearman_block_ci
from predictor_core.obs import emit_event

HIST_CSV = OUTPUT_DIR / "garimpo_historico.csv"
BACKTEST_CSV = OUTPUT_DIR / "garimpo_backtest.csv"
PRIMARY_HORIZON = settings.SCORE_HORIZON_DAYS  # horizonte ao qual o score se refere
HORIZONS = sorted({1, 7, 30, PRIMARY_HORIZON})
FALLBACK_MARKER = "fallback aplicado"


# Spearman + block bootstrap vivem em core/stats.py (puro, testável sem .env) —
# importados acima. A significância (IC) entra no _report.


# ---------- CoinGecko histórico ----------
@with_retry()
async def _fetch_price(client, coin_id: str, day: datetime) -> float | None:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history"
    params = {"date": day.strftime("%d-%m-%Y"), "localization": "false"}
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    return data.get("market_data", {}).get("current_price", {}).get("usd")


async def _price_on(client, coin_id: str, day: datetime) -> float | None:
    """Preço em USD num dia específico; None se não houver dado (após retry de transitórios)."""
    try:
        return await _fetch_price(client, coin_id, day)
    except Exception:
        return None


def _load_rows() -> list[dict]:
    """Lê o histórico, descartando linhas de fallback e sem preço/data válidos."""
    if not HIST_CSV.exists():
        return []
    rows = []
    seen = set()  # dedup defensivo por (Ativo, Data) — não enviesar o n do Spearman
    with open(HIST_CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if FALLBACK_MARKER in (r.get("Resumo") or ""):
                continue
            key = (r.get("Ativo", ""), r.get("Data", ""))
            if key in seen:
                continue
            seen.add(key)
            try:
                pred_date = datetime.strptime(r["Data"], "%Y-%m-%d %H:%M:%S")
                price = float(r["price_usd"])
                score = float(r["Score"])
            except (KeyError, ValueError, TypeError):
                continue
            if price <= 0:
                continue
            rows.append({
                "ativo": (r.get("Ativo") or "").lower(),
                "score": score,
                "pred_date": pred_date,
                "pred_price": price,
                "divergencia": 1 if str(r.get("Divergencia", "")).strip() in ("1", "True", "true") else 0,
            })
    return rows


async def run():
    rows = _load_rows()
    if not rows:
        print("⚠️ Nenhuma previsão válida em garimpo_historico.csv (só fallback ou vazio).")
        return

    today = datetime.now(timezone.utc).replace(tzinfo=None)
    enriched = []
    async with get_http_client() as client:
        for row in rows:
            out = dict(row)
            for h in HORIZONS:
                target = row["pred_date"] + timedelta(days=h)
                if target > today:
                    out[f"price_d{h}"] = None
                    out[f"var_d{h}_pct"] = None
                    continue
                price = await _price_on(client, row["ativo"], target)
                out[f"price_d{h}"] = price
                out[f"var_d{h}_pct"] = (
                    round((price - row["pred_price"]) / row["pred_price"] * 100, 2)
                    if price else None
                )
                await asyncio.sleep(1.5)  # respeita o rate limit do free tier
            enriched.append(out)

    _write(enriched)
    _report(enriched)
    _metrics(enriched, PRIMARY_HORIZON)


def _write(enriched: list[dict]) -> None:
    cols = ["ativo", "score", "pred_date", "pred_price",
            "price_d1", "var_d1_pct", "price_d7", "var_d7_pct", "price_d30", "var_d30_pct"]
    with open(BACKTEST_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in enriched:
            w.writerow({c: row.get(c, "") for c in cols})
    print(f"💾 Backtest gravado em {BACKTEST_CSV}")


def _report(enriched: list[dict]) -> None:
    for h in HORIZONS:
        # pairs em ORDEM TEMPORAL (enriched preserva a ordem do histórico) — o block
        # bootstrap depende disso para capturar a dependência serial dos horizontes.
        pairs = [(r["score"], r[f"var_d{h}_pct"]) for r in enriched if r.get(f"var_d{h}_pct") is not None]
        n = len(pairs)
        marca = "  ← horizonte principal" if h == PRIMARY_HORIZON else ""
        if n < 4:
            print(f"D+{h}: dados insuficientes ({n} ponto(s) com preço) — "
                  f"aguarde previsões maduras.{marca}")
            continue
        rho, lo, hi = spearman_block_ci(pairs)
        if rho is None:
            print(f"D+{h}: variância nula em score/retorno (n={n}) — sem correlação.{marca}")
            continue
        if lo is None:
            print(f"D+{h}: Spearman = {rho:+.3f} (n={n}) — IC indisponível.{marca}")
            continue
        # IC que NÃO cruza zero = sinal; cruza zero = ainda é ruído (transforma
        # história convincente em decisão defensável — a régua dos domínios irmãos).
        veredito = "validado (IC não cruza 0)" if (lo > 0 or hi < 0) else "RUÍDO (IC cruza 0)"
        print(f"D+{h}: Spearman(Score, variação) = {rho:+.3f}  "
              f"[IC95% {lo:+.3f} a {hi:+.3f}]  (n={n}) — {veredito}{marca}")
        # Estratificação por divergência LLM-vs-técnico (só no horizonte principal):
        # a matemática prova se as previsões tagueadas (alucinação?) perdem alpha.
        if h == PRIMARY_HORIZON:
            key = f"var_d{h}_pct"
            aligned = [(r["score"], r[key]) for r in enriched
                       if r.get(key) is not None and not r.get("divergencia")]
            flagged = [(r["score"], r[key]) for r in enriched
                       if r.get(key) is not None and r.get("divergencia")]
            for label, sub in (("alinhadas (LLM≈técnico)", aligned),
                               ("divergentes (LLM×técnico)", flagged)):
                if len(sub) >= 4:
                    rs, los, his = spearman_block_ci(sub)
                    if rs is not None and los is not None:
                        print(f"      └ {label}: Spearman {rs:+.3f} "
                              f"[IC95% {los:+.3f} a {his:+.3f}] (n={len(sub)})")
            # PAYOFF: o cripto nasce emitindo o evento estruturado do pedágio (Modo B
            # validado). ic_lower nas métricas; a divergência (alucinação?) nos metadados.
            emit_event(
                "cripto", "toll_passed",
                metrics={"spearman": round(rho, 4), "ic_lower": round(lo, 4),
                         "ic_upper": round(hi, 4), "n": n},
                metadata={"horizon_days": h, "veredito": veredito,
                          "n_divergentes": len(flagged), "n_alinhadas": len(aligned)})


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
        print(f"  Acurácia direcional: {hits}/{len(directional)} = {hits / len(directional) * 100:.1f}%")

    # Hit rate dos sinais fortes (score >= limiar): % que fechou positivo
    strong = [r for r in mature if r["score"] >= threshold]
    if strong:
        pos = sum(1 for r in strong if r[key] > 0)
        print(f"  Hit rate (score ≥ {threshold}): {pos}/{len(strong)} positivos = {pos / len(strong) * 100:.1f}%")

        # Estratégia fictícia: comprar os sinais fortes; retorno médio + Sharpe simplificado
        rets = [r[key] for r in strong]
        avg = sum(rets) / len(rets)
        line = f"  Estratégia (score ≥ {threshold}): retorno médio {avg:+.2f}%"
        if len(rets) >= 2:
            std = (sum((x - avg) ** 2 for x in rets) / (len(rets) - 1)) ** 0.5
            if std:
                line += f" | Sharpe simpl. {avg / std:.2f}"
        print(line)
    else:
        print(f"  Hit rate (score ≥ {threshold}): nenhum sinal forte ainda")

    # Benchmark: Bitcoin buy & hold (média das previsões de bitcoin no mesmo horizonte)
    btc = [r[key] for r in mature if r["ativo"] == "bitcoin"]
    if btc:
        print(f"  Benchmark BTC (buy & hold): retorno médio {sum(btc) / len(btc):+.2f}%")


if __name__ == "__main__":
    asyncio.run(run())
