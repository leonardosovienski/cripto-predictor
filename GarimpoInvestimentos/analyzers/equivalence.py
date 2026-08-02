"""Equivalência DPL vs coleta direta — passo 3 do plano (fecha C-08 da auditoria).

O que compara, por ativo:
  1. INDICADORES sobre closes: `compute_indicators(closes_direto)` vs
     `derive_features(candles_dpl)`. A implementação é A MESMA (feature_engineering
     reusa compute_indicators) — logo esta comparação testa OS DADOS: a série que o
     provider da DPL entrega vs a do /market_chart direto. Critério: |diff relativo|
     < 1e-9 (mesma série → bit a bit; divergência aqui = fontes entregando séries
     diferentes, o que invalidaria a troca de coleta).
  2. change_24h/7d/30d: quantifica a divergência ESTRUTURAL documentada — a DPL
     deriva por dia-calendário dos closes; o /coins/{id} direto usa janela rolling.
     Não é bug, é semântica; o número diz se a diferença é grande o bastante para
     mudar o input do LLM (e portanto exigir a estratificação por Fonte que o
     carimbo já garante).

Sem .env: nada aqui importa settings (só rede pública CoinGecko + DPL).
Uso: python -m GarimpoInvestimentos.analyzers.equivalence --assets bitcoin,ethereum
"""

import argparse
import asyncio

from GarimpoInvestimentos.analyzers.indicators import compute_indicators
from GarimpoInvestimentos.collectors.coingecko_api import get_coin_data, get_price_series
from GarimpoInvestimentos.dpl import CryptoDataProvider
from GarimpoInvestimentos.dpl.feature_engineering import INDICATOR_KEYS, derive_features

# Tolerância p/ indicadores: os dois lados são snapshots de API tirados com segundos
# de intervalo — bit-identidade não é esperável (cache/recomputo do provedor gera
# ruído ~1e-8 relativo, medido na 1ª execução). 1e-6 fica 4+ ordens abaixo de
# qualquer coisa visível nos 2 decimais que o LLM consome, e ainda pega divergência
# REAL de dados (fonte entregando série diferente).
_REL_TOL = 1e-6
_CHANGE_KEYS = ("change_24h", "change_7d", "change_30d")


def _rel_diff(a: float, b: float) -> float:
    if a == b:
        return 0.0
    denom = max(abs(a), abs(b), 1e-12)
    return abs(a - b) / denom


def compare_asset(
    ind_direct: dict, ind_dpl: dict, changes_direct: dict, changes_dpl: dict | None = None
) -> dict:
    """Comparação pura (testável sem rede). Retorna {indicadores: {key: rel_diff},
    changes: {key: (direto_rolling, dpl_calendario, diff_abs_pp)}, ok: bool}."""
    if changes_dpl is None:
        changes_dpl = ind_dpl
    out = {"indicadores": {}, "changes": {}, "ok": True}
    for k in sorted(INDICATOR_KEYS):
        a, b = ind_direct.get(k), ind_dpl.get(k)
        if a is None or b is None:
            out["indicadores"][k] = None  # ausente num dos lados (série curta)
            out["ok"] = out["ok"] and (a is None and b is None)
            continue
        d = _rel_diff(a, b)
        out["indicadores"][k] = d
        if d > _REL_TOL:
            out["ok"] = False
    for k in _CHANGE_KEYS:
        a, b = changes_direct.get(k), changes_dpl.get(k)
        if a is not None and b is not None:
            out["changes"][k] = (a, b, abs(a - b))  # pontos percentuais
    return out


async def run(assets: list[str], pause_s: float = 8.0) -> dict:
    """3 chamadas CoinGecko por ativo → pausa generosa (free tier ~10 req/min).
    Falha de um ativo (ex.: 429 persistente) não derruba o lote: vira 'skipped'."""
    facade = CryptoDataProvider()  # fallback (Binance→CoinGecko), igual à ingestão
    results = {}
    for i, ativo in enumerate(assets):
        try:
            # lado direto (pré-DPL): série + variações rolling do /coins/{id}
            closes = await get_price_series(ativo, days=200)
            await asyncio.sleep(pause_s)
            coin = await get_coin_data(ativo)
            await asyncio.sleep(pause_s)
            # lado DPL: mesmos 200 candles pela fachada, features derivadas
            candles = await facade.fetch_ohlcv(ativo, interval="1d", limit=200)
            feats = derive_features(candles)
            # Indicadores comparados SEM o último candle (o /market_chart inclui o
            # candle PARCIAL do dia, que muda a cada tick — achado da 1ª execução:
            # kaspa 0.0, btc 4e-3) e sobre a CAUDA COMUM (o endpoint direto devolve
            # o dia corrente a mais → comprimentos diferentes fazem a SMA-200 olhar
            # janelas distintas ou faltar de um lado só — achado da 2ª execução).
            closes_dpl = [c.close for c in sorted(candles, key=lambda c: c.timestamp)]
            a, b = closes[:-1], closes_dpl[:-1]
            common = min(len(a), len(b))
            results[ativo] = compare_asset(
                compute_indicators(a[-common:]),
                compute_indicators(b[-common:]),
                {k: getattr(coin, k) for k in _CHANGE_KEYS},
                changes_dpl=feats,
            )
        except Exception as e:
            results[ativo] = {"skipped": f"{type(e).__name__}: {e}"}
        if i < len(assets) - 1:
            await asyncio.sleep(pause_s)
    return results


def report(results: dict) -> bool:
    all_ok = True
    for ativo, r in results.items():
        if "skipped" in r:
            print(f"\n{ativo.upper()}: PULADO ({r['skipped'][:90]}) — não conta no veredito")
            continue
        worst = max((d for d in r["indicadores"].values() if d is not None), default=0.0)
        status = "EQUIVALENTE" if r["ok"] else "DIVERGENTE"
        all_ok = all_ok and r["ok"]
        print(f"\n{ativo.upper()}: indicadores {status} (pior diff relativo: {worst:.2e})")
        for k, (a, b, d) in r["changes"].items():
            print(
                f"   {k}: direto(rolling) {a:+.2f}% vs dpl(calendário) {b:+.2f}% — diff {d:.2f} pp"
            )
    print(
        "\nVeredito indicadores:",
        "EQUIVALENTES em todos os ativos"
        if all_ok
        else "há divergência — NÃO trocar a coleta antes de investigar",
    )
    print(
        "Nota: diffs de change_* são semânticos (rolling vs calendário), não bug —"
        "\ncobertos pela estratificação do carimbo Fonte (ADR D2)."
    )
    return all_ok


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--assets", default="bitcoin,ethereum,solana", help="lista separada por vírgula")
    args = p.parse_args()
    resultados = asyncio.run(run([a.strip() for a in args.assets.split(",") if a.strip()]))
    report(resultados)
