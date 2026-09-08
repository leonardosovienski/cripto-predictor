"""Domínio de ações sobre a DPL — fachada e ingestão.

StocksDataProvider compõe preço (COTAHIST, via FallbackRouter — extensível a uma 2ª
fonte online) e expõe os SignalProviders macro (BCB). A ingestão REUSA a pipeline
genérica (ingest_crypto é domínio-agnóstica: facade.fetch_ohlcv + signal_providers) e
acrescenta o registro de proveniência (auditoria).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.ingest import ingest_crypto
from GarimpoInvestimentos.dpl.providers.cotahist import COTAHISTProvider
from GarimpoInvestimentos.dpl.router import FallbackRouter
from GarimpoInvestimentos.dpl.signals import SignalProvider


class StocksDataProvider:
    """Fachada do domínio de ações. Preço via Router (fallback); macro via signals."""

    def __init__(
        self,
        price_providers: list[DataProvider],
        signal_providers: list[SignalProvider] | None = None,
    ):
        if not price_providers:
            raise ValueError("StocksDataProvider exige ao menos uma fonte de preço")
        self._router = FallbackRouter(price_providers)
        self.signal_providers = signal_providers or []

    @classmethod
    def from_cotahist(
        cls, file_path: str | Path, signal_providers: list[SignalProvider] | None = None
    ):
        return cls([COTAHISTProvider(file_path)], signal_providers)

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        return await self._router.fetch_ohlcv(symbol, interval=interval, limit=limit)


async def ingest_stocks(
    store: FeatureStore,
    facade: StocksDataProvider,
    symbol: str,
    *,
    interval: str = "1d",
    limit: int = 300,
    max_staleness=None,
    run_id: str | None = None,
    code_version: str | None = None,
    ingested_at: datetime | None = None,
) -> list[dict]:
    """Ingestão de um ativo de ações: reusa a pipeline genérica + grava proveniência."""
    aligned = await ingest_crypto(
        store,
        facade,
        symbol,
        interval=interval,
        limit=limit,
        signal_providers=facade.signal_providers,
        max_staleness=max_staleness,
        record_provenance=False,  # proveniência própria (mais rica) logo abaixo
    )
    store.write_provenance(
        source="stocks",
        entity=symbol,
        n_rows=len(aligned),
        ingested_at=ingested_at or datetime.now(UTC),
        run_id=run_id,
        origin="cotahist+bcb",
        code_version=code_version,
    )
    return aligned
