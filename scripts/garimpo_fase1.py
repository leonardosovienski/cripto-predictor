"""Orquestrador da Fase 1 do Garimpo — coleta diária automatizada da H5 (Multi-Juiz).

Automatiza o fluxo manual: ingestão (rede) → montagem de contexto → inferência dos
4 juízes (Gemini, Groq, Cerebras, Mistral, partição fixa por ativo) → gravação na
Feature Store. Desenhado para o Windows Task Scheduler via run_garimpo_fase1.bat.

Garantias:
  1. Single instance — arquivo garimpo.lock na raiz do projeto (criação atômica
     com O_EXCL); instância concorrente loga WARNING e aborta. try/finally remove.
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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Raiz do projeto = pasta que contém o pacote GarimpoInvestimentos.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from GarimpoInvestimentos.collectors.serpapi_news import get_news_snippets
from GarimpoInvestimentos.analyzers.ai_insights import (
    analyze_asset, judge_signature, provider_for_asset,
)
from GarimpoInvestimentos.analyzers.score_engine import calculate_final_score, divergence_flag
from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.history import append_history, utc_stamp
from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB, LOGS_DIR
from GarimpoInvestimentos.dpl import CryptoDataProvider, FeatureStore
from GarimpoInvestimentos.dpl.feature_store import fonte_label
from GarimpoInvestimentos.dpl.feature_engineering import to_hard_data
from GarimpoInvestimentos.dpl.ingest import ingest_crypto
from GarimpoInvestimentos.dpl.providers.fear_greed import FearAndGreedProvider
from predictor_core.kernel.timeindex import iso_z

LOCK_FILE = ROOT / "garimpo.lock"
INGEST_HISTORY_DAYS = 200          # mesmo valor do main.py (SMA-200 + change_30d)
INGEST_RETRIES = 3                 # tentativas da coleta base (rede)
INGEST_BACKOFF_BASE = 5.0          # 5s, 10s, 20s

log = logging.getLogger("garimpo_fase1")


def _setup_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOGS_DIR / f"garimpo_fase1_{datetime.now(timezone.utc):%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def acquire_lock() -> bool:
    """Cria garimpo.lock atomicamente (O_EXCL). False = já existe outra instância."""
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"pid={os.getpid()} started={iso_z(datetime.now(timezone.utc))}\n")
    return True


def release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def judges_done_today(store: FeatureStore, today_utc: str) -> dict[str, set[str]]:
    """Ativos já previstos HOJE (UTC), agrupados por juiz — só previsões reais:
    linha de fallback (llm_fallback=1) não conta como coletada e será refeita."""
    cur = store._conn.execute(
        """SELECT ativo, juiz FROM predictions
           WHERE ts LIKE ? AND COALESCE(llm_fallback, 0) = 0""",
        (f"{today_utc}%",),
    )
    done: dict[str, set[str]] = {}
    for ativo, juiz in cur:
        provider = (juiz or "").split(":", 1)[0] or "desconhecido"
        done.setdefault(provider, set()).add(ativo.lower())
    return done


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
                    try:
                        aligned = await ingest_crypto(
                            store, facade, ativo, interval="1d",
                            limit=INGEST_HISTORY_DAYS,
                            signal_providers=[fear_greed],
                        )
                        ok += 1
                        log.info("ingestão %s: %d candles alinhados", ativo.upper(), len(aligned))
                    except Exception as e:
                        log.warning("ingestão %s falhou: %s: %s", ativo.upper(), type(e).__name__, e)
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
            log.warning("coleta base falhou (tentativa %d/%d): %s — backoff %.0fs",
                        attempt, INGEST_RETRIES, e, delay)
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

            try:
                news = await get_news_snippets(ativo)
            except Exception as e:
                log.warning("notícias de %s indisponíveis (%s) — prossegue degradado", ativo, e)
                news = []

            analysis = await analyze_asset(ativo, hard_data, news)
            if analysis.get("llm_fallback"):
                # Falha do juiz JÁ capturada dentro de analyze_asset — não persiste
                # o neutro: a reexecução do dia deve tentar este juiz de novo.
                n_fail += 1
                log.warning("juiz %s FALHOU para %s (fallback neutro descartado)",
                            provider, ativo.upper())
            else:
                score = calculate_final_score(analysis)
                resultado = {
                    "ativo": ativo,
                    "sentimento": analysis["sentiment"],
                    "score": score,
                    "resumo": analysis["summary"],
                    "data": utc_stamp(),               # published_at UTC do histórico
                    "price_usd": hard_data.get("price_usd", 0),
                    "judge": judge_signature(ativo),   # provider:modelo:hash
                    "divergencia": divergence_flag(score, hard_data.get("indicadores", {})),
                    "data_source": fonte_label(store.latest_source(ativo, "1d")),
                    "input_degradado": 0 if news else 1,
                    "llm_fallback": 0,
                }
                append_history([resultado], store)
                n_ok += 1
                log.info("juiz %s OK para %s (score %.1f) — gravado no SQLite",
                         provider, ativo.upper(), resultado["score"])
        except Exception as e:
            n_fail += 1
            log.warning("falha isolada em %s (juiz %s): %s: %s — seguindo para o próximo",
                        ativo.upper(), provider, type(e).__name__, e)
        if i < len(pending) - 1:
            await asyncio.sleep(settings.LLM_PACING_SECONDS)
    return n_ok, n_fail


async def main() -> int:
    run_started = iso_z(datetime.now(timezone.utc))   # timestamp canônico do core
    today_utc = run_started[:10]
    log.info("=== garimpo_fase1 iniciado em %s (DB: %s) ===", run_started, FEATURE_STORE_DB)

    if settings.LLM_PROVIDER != "multi":
        log.warning("LLM_PROVIDER=%s (esperado 'multi' para a H5) — carimbos de juiz "
                    "seguirão o provedor global", settings.LLM_PROVIDER)

    # 1) Coleta base (rede) — retry com backoff; degrada para análise offline se falhar.
    with FeatureStore(FEATURE_STORE_DB) as store:
        universo = store.list_symbols("1d") or settings.DEFAULT_ASSETS
    if not await run_ingest_with_retry(universo):
        log.warning("coleta base indisponível — prosseguindo com dados já materializados "
                    "(análise offline usa o último snapshot da Feature Store)")

    # 2) Idempotência + 3) inferência isolada por juiz + 4) gravação.
    store = FeatureStore(FEATURE_STORE_DB)
    try:
        universo = store.list_symbols("1d") or settings.DEFAULT_ASSETS
        done = judges_done_today(store, today_utc)
        for provider, ativos_done in sorted(done.items()):
            log.info("idempotência: juiz %s já tem %d previsão(ões) hoje — pulando: %s",
                     provider, len(ativos_done), ", ".join(sorted(ativos_done)))
        done_assets = {a for s in done.values() for a in s}
        pending = [a for a in universo if a.lower() not in done_assets]

        if not pending:
            log.info("todos os juízes já coletados hoje (%s) — nada a fazer", today_utc)
            return 0

        log.info("pendentes hoje: %d ativo(s) → %s", len(pending),
                 ", ".join(f"{a}({provider_for_asset(a)})" for a in pending))
        n_ok, n_fail = await analyze_pending(store, pending)
    finally:
        store.close()

    log.info("=== concluído: %d gravado(s) na Feature Store, %d falha(s) isolada(s) ===",
             n_ok, n_fail)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    _setup_logging()
    if not acquire_lock():
        log.warning("garimpo.lock existe (%s) — outra instância em execução ou lock "
                    "órfão de crash; abortando. Se for órfão, remova o arquivo.", LOCK_FILE)
        sys.exit(2)
    try:
        sys.exit(asyncio.run(main()))
    except Exception:
        log.exception("erro fatal no orquestrador")
        sys.exit(1)
    finally:
        release_lock()
