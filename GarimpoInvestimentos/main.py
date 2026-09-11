import argparse
import asyncio
import os

# (O guard de UTF-8 no stdout/stderr para Windows fica em GarimpoInvestimentos/__init__.py,
#  cobrindo qualquer entry-point do pacote.)

# Pré-parse de --output-dir ANTES das importações pesadas: o core/paths.py lê
# GARIMPO_OUTPUT_DIR no momento do import, então a env var precisa estar setada antes.
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--output-dir")
_known, _ = _pre.parse_known_args()
if _known.output_dir:
    os.environ["OUTPUT_DIR"] = _known.output_dir
    os.environ["GARIMPO_OUTPUT_DIR"] = _known.output_dir

from datetime import UTC, datetime, timedelta
from pathlib import Path

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB, OUTPUT_DIR

# Valide imediatamente, antes das demais importações. Se ``core.paths`` já
# estava no cache, aceitar a flag produziria escrita silenciosa no lugar errado.
if _known.output_dir:
    requested_output = Path(_known.output_dir).expanduser().resolve()
    if OUTPUT_DIR.resolve() != requested_output:
        raise RuntimeError(
            "--output-dir foi aplicado depois de core.paths ter sido carregado; "
            "inicie pelo entrypoint 'cripto-predictor' ou importe "
            "GarimpoInvestimentos.main antes de outros módulos do pacote. "
            f"solicitado={requested_output}, ativo={OUTPUT_DIR.resolve()}"
        )

from predictor_core.obs import emit_event

from GarimpoInvestimentos.analyzers.ai_insights import (
    _build_prompt,
    analyze_asset,
    judge_signature,
    provider_for_asset,
)
from GarimpoInvestimentos.analyzers.prefilter import decide as prefilter_decide
from GarimpoInvestimentos.analyzers.score_engine import calculate_final_score, divergence_flag
from GarimpoInvestimentos.collectors.discovery import discover_assets
from GarimpoInvestimentos.collectors.news import get_news_result
from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.api_guard import allow as guard_allow
from GarimpoInvestimentos.core.cache import analysis_fingerprint, load_cache, save_cache
from GarimpoInvestimentos.core.collection_policy import current_policy_json
from GarimpoInvestimentos.core.history import append_history, utc_stamp
from GarimpoInvestimentos.core.logger import log_error, log_start, log_success
from GarimpoInvestimentos.dpl import CryptoDataProvider, FeatureStore
from GarimpoInvestimentos.dpl.feature_engineering import to_hard_data
from GarimpoInvestimentos.dpl.feature_store import fonte_label
from GarimpoInvestimentos.dpl.ingest import ingest_crypto
from GarimpoInvestimentos.dpl.providers.fear_greed import FearAndGreedProvider
from GarimpoInvestimentos.dpl.snapshots import prediction_payload, serving_context
from GarimpoInvestimentos.output.reporter import export_results
from GarimpoInvestimentos.pipeline_results import summarize_outcomes

# A Feature Store (core.paths.FEATURE_STORE_DB) é o repositório offline do qual o
# pipeline lê (serving) E o histórico oficial de previsões; a ingestão (rede)
# popula os dados separadamente via `--ingest`.
# Histórico diário coletado na ingestão — suficiente para SMA-200 + change_30d.
INGEST_HISTORY_DAYS = 200
# Fear & Greed é diário; após 2 dias sem atualizar, o Alignment Engine injeta NaN.
SIGNAL_STALENESS = {"fear_greed": timedelta(days=2)}


from GarimpoInvestimentos.arguments import parse_args

# Mapeia o modo de runtime → bloco de configuração do sources.json.
_MODE_TO_CONFIG = {"fallback": "crypto_price", "consensus": "crypto_price_consensus"}


async def run_ingest(ativos: list[str], mode: str = "fallback") -> tuple[int, int]:
    """Compatibility adapter for callers injecting the historical main services."""
    from GarimpoInvestimentos.ingestion import IngestionServices
    from GarimpoInvestimentos.ingestion import run_ingest as acquire

    services = IngestionServices(
        CryptoDataProvider,
        FearAndGreedProvider,
        FeatureStore,
        FEATURE_STORE_DB,
        settings,
        guard_allow,
        emit_event,
        ingest_crypto,
        log_error,
    )
    return await acquire(ativos, mode, services=services)


async def run():
    args = parse_args()
    if not args.ingest and settings.runtime_mode != "analysis":
        raise RuntimeError("analysis requires its own validated runtime configuration")
    # Universo (ADR merge D3): --discover (rede, só na ingestão) | --assets | default.
    # Default difere por modo: ingestão usa DEFAULT_ASSETS; análise lê o que a Feature
    # Store TEM (o resultado de --ingest --discover fica analisável sem redigitar lista).
    if args.discover is not None:
        n = min(args.discover, 20)  # teto: cota free tier do LLM (~20 req/dia)
        print(f"🔭 Varrendo mercado por {n} candidatos (momentum + trending)...")
        ativos = await discover_assets(top_n=n)
        if not ativos:
            raise ValueError(
                "Descoberta não retornou candidatos (mercado indisponível "
                "ou filtros zeraram a lista)."
            )
    elif args.assets:
        ativos = [asset.strip() for asset in args.assets.split(",") if asset.strip()]
    else:
        ativos = None

    if args.ingest:
        ativos = ativos or settings.DEFAULT_ASSETS
        if not ativos:
            raise ValueError(
                "Nenhum ativo válido informado. Use --assets, --discover ou DEFAULT_ASSETS."
            )
        _, failed = await run_ingest(ativos, mode=args.mode)
        print("📦 Ingestão concluída. Rode sem --ingest para analisar com notícias e LLM.")
        if failed:
            raise SystemExit(2)
        return

    score_threshold = args.min_score if args.min_score is not None else settings.LIMIAR_SCORE_MINIMO
    cache_enabled = settings.ENABLE_CACHE and not args.no_cache
    cache = load_cache() if cache_enabled else {}

    # Serving: o pipeline lê dados de mercado já alinhados da Feature Store (offline).
    store = FeatureStore(FEATURE_STORE_DB)

    if ativos is None:
        # Sem --assets: analisa tudo que a Feature Store tem (ADR merge D3).
        ativos = store.list_symbols("1d")
        if not ativos:
            store.close()
            raise ValueError("Feature Store vazia — rode `--ingest` primeiro (ou use --assets).")
        print(f"🗃️ Universo da Feature Store: {', '.join(ativos)}")

    print("🚀 Iniciando pipeline de análise de criptoativos")
    print(f"• Ativos: {', '.join(ativos)}")
    print(f"• Score mínimo destacado: {score_threshold}")
    print(f"• Cache: {'ativo' if cache_enabled else 'desativado'}")

    resultados = []
    outcomes = dict.fromkeys(ativos, "NOT_COMPLETED")
    n_degraded = 0

    for i, ativo in enumerate(ativos):
        log_start(ativo)
        print(f"\n🔎 Analisando {ativo.upper()}...")

        try:
            snapshot = serving_context(store, ativo)
        except ValueError as exc:
            log_error(ativo, exc)
            outcomes[ativo] = "SOURCE_UNAVAILABLE"
            continue
        flat = snapshot["features"]
        fingerprint = analysis_fingerprint(
            {"features": flat, "snapshot_id": snapshot["snapshot_id"]},
            judge_signature(ativo),
            snapshot["source"],
            current_policy_json(),
        )
        if flat and cache.get(ativo, {}).get("input_fingerprint") == fingerprint:
            print(f"🧠 Cache válido — pulando coleta para {ativo}.")
            resultado = cache[ativo]
            outcomes[ativo] = "CACHED"
            resultados.append(resultado)
            if resultado.get("score", 0) >= score_threshold:
                print(f"🏅 {ativo.upper()} está acima do limiar de {score_threshold}.")
            continue

        # Dados de mercado — lidos da Feature Store (offline). Sem dados não há análise.
        if not flat:
            outcomes[ativo] = "SOURCE_UNAVAILABLE"
            log_error(
                ativo,
                RuntimeError("sem dados na Feature Store — rode `--ingest` antes de analisar"),
            )
            continue
        hard_data = to_hard_data(flat)
        if "price_usd" not in hard_data:
            outcomes[ativo] = "SOURCE_UNAVAILABLE"
            log_error(ativo, RuntimeError("Feature Store sem price_usd para o ativo"))
            continue

        prefilter = prefilter_decide(hard_data)
        if not prefilter.selected:
            outcomes[ativo] = "FILTERED"
            emit_event(
                "previsao_cripto",
                "llm_prefilter_skipped",
                metrics={},
                metadata={"ativo": ativo, "reason": prefilter.reason},
            )
            print(
                f"🔎 {ativo.upper()} fora do pre-filtro ({prefilter.reason}) — sem chamada de LLM."
            )
            continue
        llm_budget = guard_allow(
            "llm", provider_for_asset(ativo), settings.API_GUARD_MAX_LLM_CALLS_PER_PROVIDER
        )
        if not llm_budget.allowed:
            outcomes[ativo] = "BUDGET_SKIPPED"
            emit_event(
                "previsao_cripto",
                "api_guard_skipped",
                metrics={},
                metadata={"stage": "llm", "ativo": ativo, "reason": llm_budget.reason},
            )
            print(f"🔎 {ativo.upper()} fora do orçamento de LLM ({llm_budget.reason}).")
            continue

        # Indicadores são features derivadas já materializadas; ausência = série curta.
        ind_ok = "indicadores" in hard_data
        if not ind_ok:
            log_error(
                ativo,
                RuntimeError("indicadores ausentes na Feature Store (histórico insuficiente?)"),
            )

        # Notícias — fallback para lista vazia; o Gemini ainda analisa com dados de mercado
        news_result = await get_news_result(ativo)
        news = news_result.titles
        news_ok = not news_result.degraded

        # Degradação silenciosa INSTRUMENTADA: antes o except engolia a falha e o LLM
        # pontuava com input empobrecido sem ninguém saber. Agora é contada e EMITIDA
        # (o evento entra no JSONL — auditável; o cross-check e o backtest podem
        # estratificar previsões degradadas no futuro).
        faltando = [k for k, ok in (("indicadores", ind_ok), ("noticias", news_ok)) if not ok]
        if faltando:
            n_degraded += 1
            emit_event(
                "previsao_cripto",
                "input_degraded",
                metrics={"n_faltando": len(faltando)},
                metadata={"ativo": ativo, "faltando": faltando},
            )

        # Análise e score
        try:
            started_at = datetime.now(UTC)
            analysis = await analyze_asset(ativo, hard_data, news)
            score = calculate_final_score(analysis)
            resultado = {
                "ativo": ativo,
                "sentimento": analysis["sentiment"],
                "score": score,
                "resumo": analysis["summary"],
                # UTC (convenção jul/2026 — ver history.utc_stamp): o backtest
                # compara maturação contra "hoje" UTC; carimbar em local criava
                # ambiguidade de até 3h.
                "data": utc_stamp(),
                "price_usd": hard_data.get("price_usd", 0),
                # Em modo multi o juiz é por-ativo (partição fixa) — o carimbo
                # identifica QUAL provedor/modelo julgou ESTA previsão.
                "judge": judge_signature(ativo),
                # cross-check flag-only: tagueia contradição LLM-vs-técnico, NÃO muta o score
                "divergencia": divergence_flag(score, hard_data.get("indicadores", {})),
                # carimbo Fonte (ADR merge D2): política de dados desta previsão —
                # o backtest estratifica por ele (trocar fonte = quebra de série).
                "data_source": fonte_label(snapshot["source"]),
                # 0008: persistido na previsão (antes só ia à telemetria) — o
                # backtest estratifica previsões com input empobrecido.
                "input_degradado": 1 if faltando else 0,
                "news_provider": news_result.provider,
                "news_degraded_reason": news_result.degraded_reason,
                "collection_policy": current_policy_json(),
                "input_fingerprint": fingerprint,
                # 0009: carimbo estrutural de fallback do LLM — a linha entra no
                # histórico mas o backtest a EXCLUI (não é análise real).
                "llm_fallback": 1 if analysis.get("llm_fallback") else 0,
            }
            resultado["input_snapshot"] = prediction_payload(
                snapshot,
                hard_data=hard_data,
                news_result=news_result,
                prompt=_build_prompt(ativo, hard_data, news),
                analysis=analysis,
                judge=resultado["judge"],
                policy=resultado["collection_policy"],
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
            append_history([resultado], store)
            outcomes[ativo] = "DEGRADED" if resultado["llm_fallback"] else "SUCCEEDED"
            resultados.append(resultado)
            # Fallback NÃO entra no cache: erro transitório do LLM não pode
            # "valer por 6h" — a reexecução no mesmo dia deve tentar de novo
            # (a linha fallback persiste no histórico, carimbada, mas o cache
            # guardá-la impediria a análise real de substituí-la).
            if not resultado["llm_fallback"]:
                cache[ativo] = resultado
            log_success(ativo, score)
            if score >= score_threshold:
                print(f"🏅 {ativo.upper()} está acima do limiar de {score_threshold}.")
        except Exception as e:
            outcomes[ativo] = "FAILED"
            log_error(ativo, e)

        # Rate limiting: pausa entre ativos para respeitar o limite POR MINUTO do LLM
        # (Gemini free ~10/min). O gargalo é o LLM, não o CoinGecko — só espaça quem
        # de fato chamou o modelo (os cacheados dão `continue` antes daqui).
        if i < len(ativos) - 1:
            await asyncio.sleep(settings.LLM_PACING_SECONDS)

    if n_degraded:
        print(
            f"⚠️  {n_degraded}/{len(ativos)} ativo(s) com input degradado "
            f"(indicador/notícia faltando) — score do LLM saiu empobrecido; ver events.jsonl."
        )
    # Every new prediction is durable before fallible cache/export I/O.
    store.close()
    receipt = summarize_outcomes(outcomes)
    emit_event("previsao_cripto", "analysis.completed", metrics=receipt["counts"], metadata=receipt)
    if receipt["run_status"] == "FAILED":
        raise RuntimeError(
            "analysis failed for every eligible asset; inspect analysis.completed receipt"
        )
    # Cache só é regravado quando habilitado (--no-cache não toca no cache.json)
    if cache_enabled:
        save_cache(cache)
    export_results(resultados)
    print(
        f"📊 Histórico oficial atualizado na Feature Store ({FEATURE_STORE_DB.name}, tabela predictions)"
    )

    if args.summary:
        destaques = [r for r in resultados if r.get("score", 0) >= score_threshold]
        print(f"\n===== RESUMO (score ≥ {score_threshold}) =====")
        if destaques:
            for r in sorted(destaques, key=lambda x: x.get("score", 0), reverse=True):
                print(f"  🏅 {r.get('ativo', '').upper():<10} score {r.get('score', 0)}")
        else:
            print("  (nenhum ativo acima do limiar)")
    if receipt["run_status"] == "PARTIAL":
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(run())
