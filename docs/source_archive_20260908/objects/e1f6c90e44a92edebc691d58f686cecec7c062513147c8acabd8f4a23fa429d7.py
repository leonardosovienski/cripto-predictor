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

from datetime import timedelta
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
from GarimpoInvestimentos.core.cache import load_cache, save_cache
from GarimpoInvestimentos.core.collection_policy import current_policy_json
from GarimpoInvestimentos.core.history import append_history, migrate_csv_to_store, utc_stamp
from GarimpoInvestimentos.core.logger import log_error, log_start, log_success
from GarimpoInvestimentos.dpl import CryptoDataProvider, FeatureStore
from GarimpoInvestimentos.dpl.feature_engineering import to_hard_data
from GarimpoInvestimentos.dpl.feature_store import fonte_label
from GarimpoInvestimentos.dpl.ingest import ingest_crypto
from GarimpoInvestimentos.dpl.providers.fear_greed import FearAndGreedProvider
from GarimpoInvestimentos.output.reporter import export_results

# A Feature Store (core.paths.FEATURE_STORE_DB) é o repositório offline do qual o
# pipeline lê (serving) E o histórico oficial de previsões; a ingestão (rede)
# popula os dados separadamente via `--ingest`.
# Histórico diário coletado na ingestão — suficiente para SMA-200 + change_30d.
INGEST_HISTORY_DAYS = 200
# Fear & Greed é diário; após 2 dias sem atualizar, o Alignment Engine injeta NaN.
SIGNAL_STALENESS = {"fear_greed": timedelta(days=2)}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pipeline de análise de criptoativos com cache, histórico e exportação."
    )
    origem = parser.add_mutually_exclusive_group()
    origem.add_argument(
        "--assets",
        help="Lista de ativos separados por vírgula. Ex: bitcoin,ethereum,solana",
    )
    origem.add_argument(
        "--discover",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="Descobre N candidatos no mercado (CoinGecko: momentum 7d/24h + trending; "
        "filtra stablecoin, wrapped e volume < US$10M) em vez de usar lista fixa. "
        "N padrão: 10, máx: 20 (cota do LLM free tier). Exige --ingest: descoberta "
        "é rede; a análise é offline e lê o universo da Feature Store (ADR merge D3).",
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
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Roda só a INGESTÃO (rede): coleta OHLCV + Fear&Greed, alinha e "
        "materializa na Feature Store local. O pipeline de análise lê dela.",
    )
    parser.add_argument(
        "--mode",
        choices=["fallback", "consensus"],
        default="fallback",
        help="Política de coleta de preço na ingestão: 'fallback' (sequencial "
        "Binance→CoinGecko, padrão) ou 'consensus' (mediana Binance+Kraken). "
        "Só afeta --ingest; o serving é indiferente a quantas fontes geraram o dado.",
    )
    args = parser.parse_args()
    if args.discover is not None and not args.ingest:
        parser.error(
            "--discover exige --ingest (descubra e ingira primeiro; "
            "depois rode a análise offline, que lê o universo da Feature Store)"
        )
    return args


# Mapeia o modo de runtime → bloco de configuração do sources.json.
_MODE_TO_CONFIG = {"fallback": "crypto_price", "consensus": "crypto_price_consensus"}


async def run_ingest(ativos: list[str], mode: str = "fallback") -> tuple[int, int]:
    """Camada de ingestão: única que toca a rede. Popula a Feature Store offline.

    `mode` decide a política de preço (fallback sequencial ou consenso multi-fonte) —
    configuração de runtime, sem reescrita: a fachada instancia o Router certo a
    partir do bloco correspondente no sources.json.
    """
    facade = CryptoDataProvider(config_key=_MODE_TO_CONFIG[mode])
    fear_greed = FearAndGreedProvider()
    print(f"📥 Ingestão ({mode}) → {FEATURE_STORE_DB}")
    succeeded = failed = 0
    with FeatureStore(FEATURE_STORE_DB) as store:
        for i, ativo in enumerate(ativos):
            budget = guard_allow("ingest", "assets", settings.API_GUARD_MAX_INGEST_ASSETS)
            if not budget.allowed:
                emit_event(
                    "previsao_cripto",
                    "api_guard_skipped",
                    metrics={},
                    metadata={"stage": "ingest", "ativo": ativo, "reason": budget.reason},
                )
                print(f"  ⏭️  {ativo.upper()} fora do orçamento de ingestão ({budget.reason})")
                continue
            try:
                aligned = await ingest_crypto(
                    store,
                    facade,
                    ativo,
                    interval="1d",
                    limit=INGEST_HISTORY_DAYS,
                    signal_providers=[fear_greed],
                    max_staleness=SIGNAL_STALENESS,
                )
                print(f"  ✅ {ativo.upper()} — {len(aligned)} candles alinhados e materializados")
                succeeded += 1
            except Exception as e:
                failed += 1
                log_error(ativo, e)
                print(f"  ❌ {ativo.upper()} — falha na ingestão: {e}")
            if i < len(ativos) - 1:
                await asyncio.sleep(1)  # rate limiting entre ativos
    if succeeded == 0:
        raise RuntimeError(f"ingestão não gravou nenhum ativo ({failed} falha(s))")
    return succeeded, failed


async def run():
    args = parse_args()
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
        await run_ingest(ativos, mode=args.mode)
        print("📦 Ingestão concluída. Rode sem --ingest para analisar (offline).")
        return

    score_threshold = args.min_score if args.min_score is not None else settings.LIMIAR_SCORE_MINIMO
    cache_enabled = settings.ENABLE_CACHE and not args.no_cache
    cache = load_cache() if cache_enabled else {}

    # Serving: o pipeline lê dados de mercado já alinhados da Feature Store (offline).
    store = FeatureStore(FEATURE_STORE_DB)

    # Histórico oficial = Feature Store (passo 4). CSV legado, se existir, é
    # absorvido aqui (idempotente — upsert por (ativo, ts)); o arquivo não é tocado.
    n_migrated = migrate_csv_to_store(store)
    if n_migrated:
        print(f"🗄️ Histórico legado absorvido na Feature Store: {n_migrated} linha(s) do CSV.")

    if ativos is None:
        # Sem --assets: analisa tudo que a Feature Store tem (ADR merge D3).
        ativos = store.list_symbols("1d")
        if not ativos:
            raise ValueError("Feature Store vazia — rode `--ingest` primeiro (ou use --assets).")
        print(f"🗃️ Universo da Feature Store: {', '.join(ativos)}")

    print("🚀 Iniciando pipeline de análise de criptoativos")
    print(f"• Ativos: {', '.join(ativos)}")
    print(f"• Score mínimo destacado: {score_threshold}")
    print(f"• Cache: {'ativo' if cache_enabled else 'desativado'}")

    resultados = []
    n_degraded = 0

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

        # Dados de mercado — lidos da Feature Store (offline). Sem dados não há análise.
        flat = store.latest_features(ativo, "1d")
        if not flat:
            log_error(
                ativo,
                RuntimeError("sem dados na Feature Store — rode `--ingest` antes de analisar"),
            )
            continue
        hard_data = to_hard_data(flat)
        if "price_usd" not in hard_data:
            log_error(ativo, RuntimeError("Feature Store sem price_usd para o ativo"))
            continue

        prefilter = prefilter_decide(hard_data)
        if not prefilter.selected:
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
                "data_source": fonte_label(store.latest_source(ativo, "1d")),
                # 0008: persistido na previsão (antes só ia à telemetria) — o
                # backtest estratifica previsões com input empobrecido.
                "input_degradado": 1 if faltando else 0,
                "news_provider": news_result.provider,
                "news_degraded_reason": news_result.degraded_reason,
                "collection_policy": current_policy_json(),
                # 0009: carimbo estrutural de fallback do LLM — a linha entra no
                # histórico mas o backtest a EXCLUI (não é análise real).
                "llm_fallback": 1 if analysis.get("llm_fallback") else 0,
            }
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
    # Cache só é regravado quando habilitado (--no-cache não toca no cache.json)
    if cache_enabled:
        save_cache(cache)
    export_results(resultados)
    # A store fecha DEPOIS do append: o histórico oficial vive nela (passo 4).
    # (Um close prematuro aqui já engoliu previsões em silêncio — pego pela
    # conferência de 2026-07-02; o teste de integração cobre a ordem agora.)
    append_history(resultados, store)
    store.close()
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


if __name__ == "__main__":
    asyncio.run(run())
