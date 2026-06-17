import argparse
import asyncio
import os
from datetime import datetime

# (O guard de UTF-8 no stdout/stderr para Windows fica em GarimpoInvestimentos/__init__.py,
#  cobrindo qualquer entry-point do pacote.)

# Pré-parse de --output-dir ANTES das importações pesadas: o core/paths.py lê
# GARIMPO_OUTPUT_DIR no momento do import, então a env var precisa estar setada antes.
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--output-dir")
_known, _ = _pre.parse_known_args()
if _known.output_dir:
    os.environ["GARIMPO_OUTPUT_DIR"] = _known.output_dir

from GarimpoInvestimentos.collectors.coingecko_api import get_coin_data, get_price_series
from GarimpoInvestimentos.collectors.serpapi_news import get_news_snippets
from GarimpoInvestimentos.analyzers.ai_insights import analyze_asset, judge_signature
from GarimpoInvestimentos.analyzers.indicators import compute_indicators
from GarimpoInvestimentos.analyzers.score_engine import calculate_final_score, divergence_flag
from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.output.reporter import export_results
from GarimpoInvestimentos.core.logger import log_start, log_success, log_error
from GarimpoInvestimentos.core.cache import load_cache, save_cache
from GarimpoInvestimentos.core.history import append_history


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pipeline de análise de criptoativos com cache, histórico e exportação."
    )
    parser.add_argument(
        "--assets",
        help="Lista de ativos separados por vírgula. Ex: bitcoin,ethereum,solana",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Score mínimo para destacar oportunidades fortes (escala 0-100).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignorar cache local e forçar nova coleta.",
    )
    parser.add_argument(
        "--output-dir",
        help="Diretório onde gravar CSV/XLSX (sobrescreve o padrão do projeto).",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Ao final, imprime apenas os ativos com score acima do limiar.",
    )
    return parser.parse_args()


async def run():
    args = parse_args()
    ativos = [asset.strip() for asset in args.assets.split(",") if asset.strip()] if args.assets else settings.DEFAULT_ASSETS
    if not ativos:
        raise ValueError("Nenhum ativo válido informado. Use --assets ou DEFAULT_ASSETS.")

    score_threshold = args.min_score if args.min_score is not None else settings.LIMIAR_SCORE_MINIMO
    cache_enabled = settings.ENABLE_CACHE and not args.no_cache
    cache = load_cache() if cache_enabled else {}

    print("🚀 Iniciando pipeline de análise de criptoativos")
    print(f"• Ativos: {', '.join(ativos)}")
    print(f"• Score mínimo destacado: {score_threshold}")
    print(f"• Cache: {'ativo' if cache_enabled else 'desativado'}")

    resultados = []

    for i, ativo in enumerate(ativos):
        log_start(ativo)
        print(f"\n🔎 Analisando {ativo.upper()}...")

        if ativo in cache:
            print(f"🧠 Cache válido — pulando coleta para {ativo}.")
            resultado = cache[ativo]
            resultados.append(resultado)
            if resultado.get("score", 0) >= score_threshold:
                print(f"🏅 {ativo.upper()} está acima do limiar de {score_threshold}.")
            continue

        # Dados de mercado — sem isso não há análise
        try:
            coin = await get_coin_data(ativo)
            hard_data = coin.model_dump()
        except Exception as e:
            log_error(ativo, e)
            continue  # pula o ativo; sem dados reais não faz sentido invocar o LLM

        # Indicadores técnicos — opcionais; se a série falhar, segue sem eles
        try:
            series = await get_price_series(ativo, days=200)
            indicadores = compute_indicators(series)
            if indicadores:
                hard_data["indicadores"] = indicadores
        except Exception as e:
            log_error(ativo, e)

        # Notícias — fallback para lista vazia; o Gemini ainda analisa com dados de mercado
        try:
            news = await get_news_snippets(ativo)
        except Exception as e:
            log_error(ativo, e)
            news = []

        # Análise e score
        try:
            analysis = await analyze_asset(ativo, hard_data, news)
            score = calculate_final_score(analysis)
            resultado = {
                "ativo": ativo,
                "sentimento": analysis["sentiment"],
                "score": score,
                "resumo": analysis["summary"],
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "price_usd": hard_data.get("price_usd", 0),
                "judge": judge_signature(),
                # cross-check flag-only: tagueia contradição LLM-vs-técnico, NÃO muta o score
                "divergencia": divergence_flag(score, hard_data.get("indicadores", {})),
            }
            resultados.append(resultado)
            cache[ativo] = resultado
            log_success(ativo, score)
            if score >= score_threshold:
                print(f"🏅 {ativo.upper()} está acima do limiar de {score_threshold}.")
        except Exception as e:
            log_error(ativo, e)

        # Rate limiting: 1s entre ativos — adequado para CoinGecko free tier com 3 ativos
        if i < len(ativos) - 1:
            await asyncio.sleep(1)

    # Cache só é regravado quando habilitado (--no-cache não toca no cache.json)
    if cache_enabled:
        save_cache(cache)
    export_results(resultados)
    append_history(resultados)
    print("📊 Histórico atualizado em output/garimpo_historico.csv")

    if args.summary:
        destaques = [r for r in resultados if r.get("score", 0) >= score_threshold]
        print(f"\n===== RESUMO (score ≥ {score_threshold}) =====")
        if destaques:
            for r in sorted(destaques, key=lambda x: x.get("score", 0), reverse=True):
                print(f"  🏅 {r.get('ativo', '').upper():<10} score {r.get('score', 0)}")
        else:
            print("  (nenhum ativo acima do limiar)")


if __name__ == "__main__":
    asyncio.run(run())
