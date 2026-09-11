"""Acquisition composition, independently loadable from analysis/LLM modules."""

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

INGEST_HISTORY_DAYS = 200
SIGNAL_STALENESS = {"fear_greed": timedelta(days=2)}
_MODE_TO_CONFIG = {"fallback": "crypto_price", "consensus": "crypto_price_consensus"}


@dataclass(frozen=True)
class IngestionServices:
    provider_factory: Any
    signal_factory: Any
    store_factory: Any
    database: Any
    settings: Any
    guard: Any
    emit: Any
    ingest: Any
    log_error: Any


def configured_services():
    from predictor_core.obs import emit_event

    from GarimpoInvestimentos.config import settings
    from GarimpoInvestimentos.core.api_guard import allow
    from GarimpoInvestimentos.core.logger import log_error
    from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
    from GarimpoInvestimentos.dpl import CryptoDataProvider, FeatureStore
    from GarimpoInvestimentos.dpl.ingest import ingest_crypto
    from GarimpoInvestimentos.dpl.providers.fear_greed import FearAndGreedProvider

    return IngestionServices(
        CryptoDataProvider,
        FearAndGreedProvider,
        FeatureStore,
        FEATURE_STORE_DB,
        settings,
        allow,
        emit_event,
        ingest_crypto,
        log_error,
    )


async def run_ingest(
    ativos: list[str], mode: str = "fallback", *, services=None
) -> tuple[int, int]:
    """Coleta de mercado pela rede e persistência na Feature Store local.

    `mode` decide a política de preço (fallback sequencial ou consenso multi-fonte) —
    configuração de runtime, sem reescrita: a fachada instancia o Router certo a
    partir do bloco correspondente no sources.json.
    """
    if services is None:
        services = configured_services()
    CryptoDataProvider = services.provider_factory
    FearAndGreedProvider = services.signal_factory
    FeatureStore = services.store_factory
    FEATURE_STORE_DB = services.database
    settings = services.settings
    guard_allow = services.guard
    emit_event = services.emit
    ingest_crypto = services.ingest
    log_error = services.log_error
    facade = CryptoDataProvider(config_key=_MODE_TO_CONFIG[mode])
    fear_greed = FearAndGreedProvider()
    print(f"📥 Ingestão ({mode}) → {FEATURE_STORE_DB}")
    succeeded = failed = 0
    with FeatureStore(FEATURE_STORE_DB) as store:
        for i, ativo in enumerate(ativos):
            budget = guard_allow("ingest", "assets", settings.API_GUARD_MAX_INGEST_ASSETS)
            if not budget.allowed:
                failed += 1
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
                print(f"  ❌ {ativo.upper()} — falha na ingestão: {type(e).__name__}")
            if i < len(ativos) - 1:
                await asyncio.sleep(1)  # rate limiting entre ativos
    if succeeded == 0:
        raise RuntimeError(f"ingestão não gravou nenhum ativo ({failed} falha(s))")
    return succeeded, failed
