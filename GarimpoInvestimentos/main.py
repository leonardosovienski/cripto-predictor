import argparse
import asyncio
import logging
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
from GarimpoInvestimentos.store.logger import log_start, log_success, log_error, run_logging_setup
from GarimpoInvestimentos.store.paths import LOGS_DIR
from GarimpoInvestimentos.store.cache import load_cache, save_cache
from GarimpoInvestimentos.store.history import append_history
from predictor_core.obs import emit_event

_DOMAIN = "previsao_cripto"
_log = logging.getLogger("previsao_cripto")


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


_FALLBACK_MARKER = "fallback aplicado"
_GEMINI_QUOTA_ALERT_RATIO = 0.20  # alerta se > 20% dos ativos saírem em fallback LLM
_MAX_CONCURRENT_REQUESTS = 5      # Semaphore: máx requisições simultâneas ao LLM


async def _analyze_ativo(
    ativo: str,
    cache: dict,
    score_threshold: float,
    sem: asyncio.Semaphore,
) -> tuple[dict | None, bool, bool]:
    """
    Analisa um único ativo com controle de concorrência via Semaphore.

    Retorna: (resultado | None, llm_fallback, degraded_input)
    - resultado=None  : coleta de dados falhou (ativo pulado)
    - llm_fallback=True : LLM retornou fallback (cota esgotada ou erro)
    - degraded_input=True : indicadores ou notícias falharam
    """
    log_start(ativo)

    if ativo in cache:
        _log.info("[cache] %s — pulando coleta.", ativo.upper())
        resultado = cache[ativo]
        if resultado.get("score", 0) >= score_threshold:
            _log.info("[destaque] %s acima do limiar de %s.", ativo.upper(), score_threshold)
        return resultado, False, False

    # Dados de mercado — sem isso não há análise
    try:
        coin = await get_coin_data(ativo)
        hard_data = coin.model_dump()
    except Exception as e:
        log_error(ativo, e)
        return None, False, False

    # Indicadores técnicos — opcionais
    ind_ok = True
    try:
        series = await get_price_series(ativo, days=200)
        indicadores = compute_indicators(series)
        if indicadores:
            hard_data["indicadores"] = indicadores
    except Exception as e:
        log_error(ativo, e)
        ind_ok = False

    # Notícias — fallback para lista vazia
    news_ok = True
    try:
        news = await get_news_snippets(ativo)
    except Exception as e:
        log_error(ativo, e)
        news = []
        news_ok = False

    degraded_input = not ind_ok or not news_ok
    if degraded_input:
        faltando = [k for k, ok in (("indicadores", ind_ok), ("noticias", news_ok)) if not ok]
        emit_event(_DOMAIN, "input_degraded",
                   metrics={"n_faltando": len(faltando)},
                   metadata={"ativo": ativo, "faltando": faltando})

    # Análise LLM com controle de concorrência
    llm_fallback = False
    try:
        async with sem:
            analysis = await analyze_asset(ativo, hard_data, news)
        score = calculate_final_score(analysis)
        # Detecta fallback do LLM (cota esgotada ou erro de parsing)
        if _FALLBACK_MARKER in (analysis.get("summary") or ""):
            llm_fallback = True
            emit_event(_DOMAIN, "fallback_triggered",
                       metrics={"score": float(score)},
                       metadata={"ativo": ativo, "provider": settings.LLM_PROVIDER,
                                 "fallback_reason": "llm_error_or_quota"})
        resultado = {
            "ativo": ativo,
            "sentimento": analysis["sentiment"],
            "score": score,
            "resumo": analysis["summary"],
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "price_usd": hard_data.get("price_usd", 0),
            "judge": judge_signature(),
            "divergencia": divergence_flag(score, hard_data.get("indicadores", {})),
        }
        cache[ativo] = resultado
        emit_event(_DOMAIN, "signal",
                   metrics={"score": float(score)},
                   metadata={"ativo": ativo, "sentimento": analysis["sentiment"],
                             "opportunity_score": analysis.get("opportunity_score"),
                             "judge": resultado["judge"], "data": resultado["data"],
                             "divergencia": resultado["divergencia"],
                             "llm_fallback": llm_fallback})
        log_success(ativo, score)
        if score >= score_threshold:
            _log.info("[destaque] %s acima do limiar de %s.", ativo.upper(), score_threshold)
        return resultado, llm_fallback, degraded_input
    except Exception as e:
        log_error(ativo, e)
        return None, True, degraded_input


async def run():
    args = parse_args()
    ativos = [asset.strip() for asset in args.assets.split(",") if asset.strip()] if args.assets else settings.DEFAULT_ASSETS
    if not ativos:
        raise ValueError("Nenhum ativo válido informado. Use --assets ou DEFAULT_ASSETS.")

    score_threshold = args.min_score if args.min_score is not None else settings.LIMIAR_SCORE_MINIMO
    cache_enabled = settings.ENABLE_CACHE and not args.no_cache

    run_logging_setup(LOGS_DIR)
    cache = load_cache() if cache_enabled else {}

    _log.info("Iniciando pipeline de analise de criptoativos")
    _log.info("Ativos: %s", ", ".join(ativos))
    _log.info("Score minimo destacado: %s", score_threshold)
    _log.info("Cache: %s", "ativo" if cache_enabled else "desativado")
    emit_event(_DOMAIN, "batch_start",
               metrics={"n_ativos": float(len(ativos))},
               metadata={"ativos": ativos, "cache_enabled": cache_enabled,
                         "score_threshold": score_threshold})

    sem = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)
    tasks = [_analyze_ativo(ativo, cache, score_threshold, sem) for ativo in ativos]
    outcomes = await asyncio.gather(*tasks)

    resultados = []
    n_degraded_input = 0
    n_llm_fallback = 0
    for resultado, llm_fallback, degraded_input in outcomes:
        if resultado is not None:
            resultados.append(resultado)
        if degraded_input:
            n_degraded_input += 1
        if llm_fallback:
            n_llm_fallback += 1

    # Alerta de cota LLM: se muitos ativos saíram em fallback, o backtest fica
    # enviesado com score=50 (incerteza) em vez de análise real.
    n_analisados = len(ativos)
    if n_llm_fallback > 0:
        ratio = n_llm_fallback / n_analisados
        is_alert = ratio > _GEMINI_QUOTA_ALERT_RATIO
        emit_event(_DOMAIN, "llm_quota_alert",
                   metrics={"n_fallback": float(n_llm_fallback),
                            "n_total": float(n_analisados),
                            "fallback_ratio": ratio},
                   metadata={"alerta": is_alert, "provider": settings.LLM_PROVIDER})
        msg = (f"%d/%d ativos com fallback LLM (score=50 ficticio) — "
               f"cota esgotada ou erro de API. Ver events.jsonl.")
        if is_alert:
            _log.warning("[ALERTA COTA LLM] " + msg, n_llm_fallback, n_analisados)
        else:
            _log.info("[aviso LLM] " + msg, n_llm_fallback, n_analisados)

    if n_degraded_input:
        _log.warning("[aviso] %d/%d ativo(s) com input degradado "
                     "(indicador/noticia faltando) — ver events.jsonl.",
                     n_degraded_input, n_analisados)

    if cache_enabled:
        save_cache(cache)
    export_results(resultados)
    append_history(resultados)
    _log.info("Historico atualizado em output/garimpo_historico.csv")
    emit_event(_DOMAIN, "batch_success",
               metrics={"n_resultados": float(len(resultados)),
                        "n_llm_fallback": float(n_llm_fallback),
                        "n_degraded_input": float(n_degraded_input)},
               metadata={"n_ativos": n_analisados})

    if args.summary:
        destaques = [r for r in resultados if r.get("score", 0) >= score_threshold]
        _log.info("===== RESUMO (score >= %s) =====", score_threshold)
        if destaques:
            for r in sorted(destaques, key=lambda x: x.get("score", 0), reverse=True):
                _log.info("  %-10s score %s", r.get("ativo", "").upper(), r.get("score", 0))
        else:
            _log.info("  (nenhum ativo acima do limiar)")


if __name__ == "__main__":
    asyncio.run(run())
