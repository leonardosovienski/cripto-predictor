"""CryptoDataProvider — a fachada que o domínio enxerga.

Esconde a existência de múltiplos provedores e a lógica de fallback. O domínio
só chama `fetch_ohlcv` / `latest_close`; a montagem (ler sources.json, instanciar
conectores, construir o Router) acontece aqui.
"""
from __future__ import annotations

import json
from pathlib import Path

from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint
from GarimpoInvestimentos.dpl.providers.binance import BinanceProvider
from GarimpoInvestimentos.dpl.providers.coingecko import CoinGeckoProvider
from GarimpoInvestimentos.dpl.router import FallbackRouter

_SOURCES_PATH = Path(__file__).with_name("sources.json")

# Fábrica: nome no sources.json → classe do conector.
_PROVIDER_REGISTRY = {
    "binance": BinanceProvider,
    "coingecko": CoinGeckoProvider,
}


def _build_router(config_path: Path | None = None) -> FallbackRouter:
    path = config_path or _SOURCES_PATH
    config = json.loads(path.read_text(encoding="utf-8"))["crypto_price"]
    providers: list[DataProvider] = []
    for name in config["order"]:
        cls = _PROVIDER_REGISTRY.get(name)
        if cls is None:
            raise ValueError(f"sources.json: provedor desconhecido '{name}'")
        pcfg = config["providers"].get(name, {})
        providers.append(cls(symbol_map=pcfg.get("symbol_map", {})))
    return FallbackRouter(providers)


class CryptoDataProvider:
    """Fachada composta para dados de preço cripto, com fallback transparente."""

    def __init__(self, router: FallbackRouter | None = None, config_path: Path | None = None):
        # router injetável para teste; senão, montado a partir do sources.json.
        self._router = router or _build_router(config_path)

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        return await self._router.fetch_ohlcv(symbol, interval=interval, limit=limit)

    async def latest_close(self, symbol: str, interval: str = "1d") -> float:
        """Atalho: preço de fechamento mais recente, com fallback transparente."""
        points = await self._router.fetch_ohlcv(symbol, interval=interval, limit=1)
        return points[-1].close
