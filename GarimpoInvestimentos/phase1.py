"""Orquestrador da Fase 1 do Garimpo — coleta diária automatizada da H5 (Multi-Juiz).

Automatiza o fluxo manual: ingestão (rede) → montagem de contexto → inferência dos
4 juízes (Gemini, Groq, Cerebras, Mistral, partição fixa por ativo) → gravação na
Feature Store. Desenhado para o Windows Task Scheduler via run_garimpo_fase1.bat.

Garantias:
  1. Single instance — garantido pelo lock público de predictor_ops que envolve
     TODO o subprocesso (ver run_garimpo_fase1.bat, --task GarimpoFase1). Este script
     não tem mais lock próprio: até 2026-07-17 reimplementava um segundo lock
     (garimpo.lock, O_EXCL + detecção de PID órfão) redundante com o do runner —
     auditoria hostil removeu a duplicação depois de confirmar
     que o .bat de produção já envolve garimpo_fase1.py inteiro no runner.
  2. Idempotência — antes de qualquer chamada de LLM, consulta a tabela
     `predictions` (PK ativo,ts) e pula os ativos cujo JUIZ já tem previsão real
     (não-fallback) gravada no dia UTC corrente.
  3. Resiliência — ingestão com retry + backoff exponencial; falha de UM juiz
     (timeout, rate limit, cota) vira WARNING e o loop segue para o próximo
     ativo/juiz. Fallback neutro do LLM NÃO é persistido aqui: a reexecução no
     mesmo dia tenta de novo (idempotência continua valendo para os que deram certo).
  4. Gravação segura — upsert por (ativo, ts) via FeatureStore.write_predictions,
     com o carimbo do juiz (`juiz` = provider:modelo:hash-do-prompt, o
     judge_signature canônico) e timestamp UTC (`ts` = utc_stamp(), a convenção
     published-at do histórico oficial).

Não altera prompt nem contrato do core — apenas orquestra o que já existe.
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from predictor_core.kernel.timeindex import iso_z
from predictor_core.obs import emit_event

from GarimpoInvestimentos.analyzers.ai_insights import (
    analyze_asset,
    judge_signature,
    provider_for_asset,
)
from GarimpoInvestimentos.analyzers.prefilter import decide as prefilter_decide
from GarimpoInvestimentos.analyzers.score_engine import calculate_final_score, divergence_flag
from GarimpoInvestimentos.collectors.news import get_news_result
from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.api_guard import allow as guard_allow
from GarimpoInvestimentos.core.collection_policy import current_policy_json
from GarimpoInvestimentos.core.history import append_history, utc_stamp
from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB, LOGS_DIR
from GarimpoInvestimentos.dpl import CryptoDataProvider, FeatureStore
from GarimpoInvestimentos.dpl.feature_engineering import to_hard_data
from GarimpoInvestimentos.dpl.feature_store import fonte_label
from GarimpoInvestimentos.dpl.ingest import ingest_crypto
from GarimpoInvestimentos.dpl.providers.fear_greed import FearAndGreedProvider
from GarimpoInvestimentos.security.redaction import safe_redact_text

INGEST_HISTORY_DAYS = 200  # mesmo valor do main.py (SMA-200 + change_30d)
INGEST_RETRIES = 3  # tentativas da coleta base (rede)
INGEST_BACKOFF_BASE = 5.0  # 5s, 10s, 20s

log = logging.getLogger("garimpo_fase1")


class _RedactSecrets(logging.Filter):
    """Adaptador logging.Filter -> predictor_ops.redaction (fonte canônica,
    Onda 4 da reintegração do ecossistema). Não mantém regex nem lista de
    nomes sensíveis própria: delega toda a redação a safe_redact_text, que
    além dos valores conhecidos passados aqui também cobre padrões genéricos
    (chave=valor, Authorization, Bearer, URLs com query param sensível — o
    que cobre, por exemplo, a chave SerpAPI viajando como query param em logs
    de libs de terceiros como httpx/httpcore)."""

    def __init__(self, secrets: list[str]):
        super().__init__()
        self._secrets = [s for s in secrets if s and len(s) >= 8]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        redacted = safe_redact_text(msg, self._secrets)
        if redacted != msg:
            record.msg, record.args = redacted, None
        return True


def _setup_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOGS_DIR / f"garimpo_fase1_{datetime.now(UTC):%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # httpx/httpcore em INFO logam a URL completa de cada request — com a chave
    # SerpAPI no query string. WARNING silencia; o filtro abaixo é o cinto de
    # segurança para qualquer outro caminho de log.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    redactor = _RedactSecrets(
        [
            settings.SERP_API_KEY,
            settings.GEMINI_API_KEY,
            settings.OPENAI_API_KEY,
            settings.GROQ_API_KEY,
            settings.CEREBRAS_API_KEY,
            settings.MISTRAL_API_KEY,
            settings.OPENROUTER_API_KEY,
            settings.COINGECKO_API_KEY,
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(redactor)


def order_by_staleness(ativos: list[str], store: FeatureStore) -> list[str]:
    """Ordena o universo por previsão real mais ANTIGA primeiro (nunca previsto
    vem antes de tudo; desempate alfabético = determinístico). Sem api_guard é
    inócuo (todos rodam); com orçamento menor que o universo, faz o corte girar
    entre os ativos em vez de furar sempre os mesmos do fim da lista — buraco
    sistemático numa série por-ativo com juiz fixo."""
    last = store.last_prediction_ts_by_asset()
    return sorted(ativos, key=lambda a: (last.get(a.lower(), ""), a.lower()))


def judges_done_today(store: FeatureStore, today_utc: str) -> set[tuple[str, str]]:
    """Pares (ativo, juiz) já previstos HOJE (UTC) — só previsões reais: linha de
    fallback (llm_fallback=1) não conta como coletada e será refeita. Compara o
    judge_signature COMPLETO (provider:modelo:hash): se o modelo/prompt mudar no
    meio do dia, o ativo NÃO é pulado como se fosse o mesmo juiz."""
    return {(ativo.lower(), juiz) for ativo, juiz in store.predictions_on(today_utc)}


async def run_ingest_with_retry(ativos: list[str]) -> bool:
    """Coleta base (DPL: OHLCV + Fear&Greed) com backoff exponencial.
    True se ao menos um ativo foi ingerido; False = coleta base indisponível."""
    for attempt in range(1, INGEST_RETRIES + 1):
        ok = 0
        try:
            facade = CryptoDataProvider(config_key="crypto_price")
            fear_greed = FearAndGreedProvider()
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
                        log.info(
                            "guarda de API: ingestão de %s pulada (%s)",
                            ativo.upper(),
                            budget.reason,
                        )
                        continue
                    try:
                        aligned = await ingest_crypto(
                            store,
                            facade,
                            ativo,
                            interval="1d",
                            limit=INGEST_HISTORY_DAYS,
                            signal_providers=[fear_greed],
                        )
                        ok += 1
                        log.info("ingestão %s: %d candles alinhados", ativo.upper(), len(aligned))
                    except Exception as e:
                        log.warning(
                            "ingestão %s falhou: %s: %s", ativo.upper(), type(e).__name__, e
                        )
                    if i < len(ativos) - 1:
                        await asyncio.sleep(1)  # rate limiting entre ativos
            if ok:
                return True
            raise RuntimeError("nenhum ativo ingerido nesta tentativa")
        except Exception as e:
            if attempt >= INGEST_RETRIES:
                log.error("coleta base esgotou %d tentativas: %s", INGEST_RETRIES, e)
                return False
            delay = INGEST_BACKOFF_BASE * (2 ** (attempt - 1))
            log.warning(
                "coleta base falhou (tentativa %d/%d): %s — backoff %.0fs",
                attempt,
                INGEST_RETRIES,
                e,
                delay,
            )
            await asyncio.sleep(delay)
    return False


async def analyze_pending(store: FeatureStore, pending: list[str]) -> tuple[int, int]:
    """Inferência dos juízes com isolamento de falha por ativo/juiz.
    Persiste CADA sucesso imediatamente (um crash tardio não perde os anteriores)."""
    n_ok = n_fail = 0
    for i, ativo in enumerate(pending):
        provider = provider_for_asset(ativo)
        try:
            flat = store.latest_features(ativo, "1d")
            if not flat:
                raise RuntimeError("sem features na Feature Store (ingestão falhou?)")
            hard_data = to_hard_data(flat)
            if "price_usd" not in hard_data:
                raise RuntimeError("Feature Store sem price_usd")

            prefilter = prefilter_decide(hard_data)
            if not prefilter.selected:
                emit_event(
                    "previsao_cripto",
                    "llm_prefilter_skipped",
                    metrics={},
                    metadata={"ativo": ativo, "reason": prefilter.reason},
                )
                log.info(
                    "pre-filtro: %s fora (%s) — sem chamada de LLM", ativo.upper(), prefilter.reason
                )
                continue
            llm_budget = guard_allow("llm", provider, settings.API_GUARD_MAX_LLM_CALLS_PER_PROVIDER)
            if not llm_budget.allowed:
                emit_event(
                    "previsao_cripto",
                    "api_guard_skipped",
                    metrics={},
                    metadata={"stage": "llm", "ativo": ativo, "reason": llm_budget.reason},
                )
                log.info("guarda de API: LLM de %s pulado (%s)", ativo.upper(), llm_budget.reason)
                continue

            news_result = await get_news_result(ativo)
            news = news_result.titles
            if news_result.degraded:
                log.warning(
                    "notícias de %s indisponíveis (%s) — prossegue degradado",
                    ativo,
                    news_result.degraded_reason,
                )

            analysis = await analyze_asset(ativo, hard_data, news)
            if analysis.get("llm_fallback"):
                # Falha do juiz JÁ capturada dentro de analyze_asset — não persiste
                # o neutro: a reexecução do dia deve tentar este juiz de novo.
                n_fail += 1
                log.warning(
                    "juiz %s FALHOU para %s (fallback neutro descartado)", provider, ativo.upper()
                )
            else:
                score = calculate_final_score(analysis)
                resultado = {
                    "ativo": ativo,
                    "sentimento": analysis["sentiment"],
                    "score": score,
                    "resumo": analysis["summary"],
                    "data": utc_stamp(),  # published_at UTC do histórico
                    "price_usd": hard_data.get("price_usd", 0),
                    "judge": judge_signature(ativo),  # provider:modelo:hash
                    "divergencia": divergence_flag(score, hard_data.get("indicadores", {})),
                    "data_source": fonte_label(store.latest_source(ativo, "1d")),
                    "input_degradado": 0 if news else 1,
                    "news_provider": news_result.provider,
                    "news_degraded_reason": news_result.degraded_reason,
                    "collection_policy": current_policy_json(),
                    "llm_fallback": 0,
                }
                append_history([resultado], store)
                n_ok += 1
                log.info(
                    "juiz %s OK para %s (score %.1f) — gravado no SQLite",
                    provider,
                    ativo.upper(),
                    resultado["score"],
                )
        except Exception as e:
            n_fail += 1
            log.warning(
                "falha isolada em %s (juiz %s): %s: %s — seguindo para o próximo",
                ativo.upper(),
                provider,
                type(e).__name__,
                e,
            )
        if i < len(pending) - 1:
            await asyncio.sleep(settings.LLM_PACING_SECONDS)
    return n_ok, n_fail


async def main() -> int:
    run_started = iso_z(datetime.now(UTC))  # timestamp canônico do core
    today_utc = run_started[:10]
    log.info("=== garimpo_fase1 iniciado em %s (DB: %s) ===", run_started, FEATURE_STORE_DB)

    if settings.LLM_PROVIDER != "multi":
        log.warning(
            "LLM_PROVIDER=%s (esperado 'multi' para a H5) — carimbos de juiz "
            "seguirão o provedor global",
            settings.LLM_PROVIDER,
        )

    # 1) Coleta base (rede) — retry com backoff; degrada para análise offline se falhar.
    with FeatureStore(FEATURE_STORE_DB) as store:
        universo = store.list_symbols("1d") or settings.DEFAULT_ASSETS
        universo = order_by_staleness(universo, store)
    if not await run_ingest_with_retry(universo):
        log.warning(
            "coleta base indisponível — prosseguindo com dados já materializados "
            "(análise offline usa o último snapshot da Feature Store)"
        )

    # 2) Idempotência + 3) inferência isolada por juiz + 4) gravação.
    store = FeatureStore(FEATURE_STORE_DB)
    try:
        universo = store.list_symbols("1d") or settings.DEFAULT_ASSETS
        universo = order_by_staleness(universo, store)
        done = judges_done_today(store, today_utc)
        by_provider: dict[str, set[str]] = {}
        for ativo, juiz in done:
            by_provider.setdefault(juiz.split(":", 1)[0] or "desconhecido", set()).add(ativo)
        for provider, ativos_done in sorted(by_provider.items()):
            log.info(
                "idempotência: juiz %s já tem %d previsão(ões) hoje — pulando: %s",
                provider,
                len(ativos_done),
                ", ".join(sorted(ativos_done)),
            )
        pending = [a for a in universo if (a.lower(), judge_signature(a)) not in done]

        if not pending:
            log.info("todos os juízes já coletados hoje (%s) — nada a fazer", today_utc)
            return 0

        log.info(
            "pendentes hoje: %d ativo(s) → %s",
            len(pending),
            ", ".join(f"{a}({provider_for_asset(a)})" for a in pending),
        )
        n_ok, n_fail = await analyze_pending(store, pending)
    finally:
        store.close()

    log.info(
        "=== concluído: %d gravado(s) na Feature Store, %d falha(s) isolada(s) ===", n_ok, n_fail
    )
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    # Single-instance já é garantido pelo lock público de predictor_ops que
    # envolve este processo inteiro (ver run_garimpo_fase1.bat) — não há mais
    # lock próprio aqui (ver nota na docstring do módulo).
    _setup_logging()
    try:
        sys.exit(asyncio.run(main()))
    except Exception:
        log.exception("erro fatal no orquestrador")
        sys.exit(1)
