"""Validação de INSTRUMENTO (não de performance): o score do LLM mede algo além
dos técnicos que recebe no prompt?

Somente leitura conceitual: roda o pipeline real para um corte transversal de ativos,
captura (score, indicadores técnicos, direção técnica, direção implícita do LLM) e mede
a REDUNDÂNCIA do score em relação aos técnicos.

LIMITE HONESTO: a atribuição PREDITIVA (Modelo A só-técnicos vs Modelo B técnicos+score,
qual prevê melhor o retorno futuro) é IMPOSSÍVEL hoje — o forward test tem ~1 ponto, sem
retornos maturados. Aqui se responde a versão MECÂNICA, que é a de validade do instrumento:
  "o score é, na sua construção, uma reformulação dos técnicos, ou carrega informação
   independente (notícias, priors do LLM)?"

Mede:
  - taxa de concordância direção_técnica × direção_LLM (entre não-neutros);
  - correlação de Spearman do score com cada técnico (sma200, macd, rsi);
  - fração não explicada (1 − concordância) como proxy de informação independente.

NÃO conclui sobre poder preditivo — só sobre o que o score reflete. Usa as MESMAS funções
do pipeline (technical_direction, llm_direction) para não inventar critério.
"""
import asyncio
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "vendor"))

from GarimpoInvestimentos.collectors.coingecko_api import get_coin_data, get_price_series
from GarimpoInvestimentos.analyzers.indicators import compute_indicators
from GarimpoInvestimentos.analyzers.ai_insights import analyze_asset
from GarimpoInvestimentos.analyzers.score_engine import (
    calculate_final_score, technical_direction, llm_direction)
from predictor_core.stats import spearman

# Conjunto diverso e ESPAÇADO (25s) para respeitar o rate-limit do CoinGecko free —
# coletar em rajada retorna 429 e inviabiliza o corte transversal.
ASSETS = ["bitcoin", "ethereum", "solana", "ripple", "cardano",
          "dogecoin", "chainlink", "litecoin", "polkadot", "tron"]


async def _one(asset):
    try:
        coin = await get_coin_data(asset)
        hard = coin.model_dump()
        series = await get_price_series(asset, days=200)
        ind = compute_indicators(series)
        hard["indicadores"] = ind
        analysis = await analyze_asset(asset, hard, [])   # SEM notícias: isola técnicos vs LLM
        score = calculate_final_score(analysis)
        return {
            "asset": asset, "score": score,
            "td": technical_direction(ind), "ld": llm_direction(score),
            "sma200": ind.get("preco_vs_sma200_pct"),
            "macd": ind.get("macd_histogram"),
            "rsi": ind.get("rsi_14"),
        }
    except Exception as e:
        print(f"  {asset}: ERRO {e}")
        return None


async def run():
    rows = []
    for a in ASSETS:
        r = await _one(a)
        if r:
            rows.append(r)
            print(f"  {r['asset']:<14} score={r['score']:>5}  téc={str(r['td']):<7} "
                  f"llm={r['ld']:<7}  sma200%={r['sma200']}  macd={r['macd']}  rsi={r['rsi']}")
        await asyncio.sleep(25)   # espaçamento anti-429 do CoinGecko free

    print(f"\nn={len(rows)} ativos com dado completo\n")
    if len(rows) < 4:
        print("amostra insuficiente para atribuição.")
        return

    # 1) Concordância direcional técnica × LLM (entre não-neutros dos dois lados)
    pares = [(r["td"], r["ld"]) for r in rows
             if r["td"] in ("bull", "bear") and r["ld"] in ("bull", "bear")]
    if pares:
        conc = sum(1 for td, ld in pares if td == ld) / len(pares)
        print(f"CONCORDÂNCIA direção técnica × LLM (não-neutros, n={len(pares)}): {conc*100:.0f}%")
        print(f"  → fração DIVERGENTE (info potencialmente independente): {(1-conc)*100:.0f}%")
    else:
        print("CONCORDÂNCIA: sem pares não-neutros suficientes.")

    # 2) Spearman do score contínuo vs cada técnico
    def col(k):
        return [r["score"] for r in rows if r[k] is not None], [r[k] for r in rows if r[k] is not None]
    for k, nome in (("sma200", "preço_vs_SMA200"), ("macd", "MACD_hist"), ("rsi", "RSI")):
        s, x = col(k)
        if len(s) >= 4:
            rho = spearman(s, x)
            print(f"Spearman(score, {nome}): {rho:+.3f} (n={len(s)})" if rho is not None
                  else f"Spearman(score, {nome}): variância nula")

    print("\nLEITURA: concordância ~100% + |Spearman| alto ⇒ score ≈ reformulação dos técnicos")
    print("(redundante). Concordância intermediária + Spearman baixo ⇒ o score carrega algo")
    print("além dos técnicos (notícias/priors do LLM) — o que NÃO prova ser sinal, só prova")
    print("que NÃO é puro técnico. Atribuição preditiva real exige o forward test maduro.")


if __name__ == "__main__":
    asyncio.run(run())
