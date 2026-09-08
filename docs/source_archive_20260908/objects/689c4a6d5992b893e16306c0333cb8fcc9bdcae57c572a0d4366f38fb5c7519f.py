"""CryptoDataProvider — a fachada que o domínio enxerga.

Esconde a existência de múltiplos provedores e a política (fallback ou agregação).
A montagem (ler sources.json, instanciar conectores, escolher o Router, anexar
Circuit Breakers) acontece aqui. O domínio só chama `fetch_ohlcv` / `latest_close`.
"""

from __future__ import annotations

import json
from pathlib import Path

from GarimpoInvestimentos.dpl.circuit_breaker import CircuitBreaker
from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint
from GarimpoInvestimentos.dpl.providers.binance import BinanceProvider
from GarimpoInvestimentos.dpl.providers.coingecko import CoinGeckoProvider
from GarimpoInvestimentos.dpl.providers.kraken import KrakenProvider
from GarimpoInvestimentos.dpl.router import AggregationRouter, FallbackRouter

_SOURCES_PATH = Path(__file__).with_name("sources.json")

# Fábrica: nome no sources.json → classe do conector.
_PROVIDER_REGISTRY = {
    "binance": BinanceProvider,
    "kraken": KrakenProvider,
    "coingecko": CoinGeckoProvider,
}


def _load_config(config_path: Path | None = None) -> dict:
    path = config_path or _SOURCES_PATH
    return json.loads(path.read_text(encoding="utf-8"))


_DOMAIN = "previsao_cripto"  # esta fachada É o domínio cripto: injeta seu rótulo na camada DPL


def _build_router(
    config_key: str = "crypto_price", config_path: Path | None = None, with_breakers: bool = True
):
    cfg = _load_config(config_path)
    block = cfg[config_key]
    # As definições dos providers (symbol_map) vivem sempre em crypto_price; blocos
    # derivados (ex.: crypto_price_consensus) reusam-nas.
    defs = cfg["crypto_price"]["providers"]
    providers: list[DataProvider] = []
    for name in block["order"]:
        klass = _PROVIDER_REGISTRY.get(name)
        if klass is None:
            raise ValueError(f"sources.json: provedor desconhecido '{name}'")
        providers.append(klass(symbol_map=defs.get(name, {}).get("symbol_map", {})))

    breakers = (
        {p.name: CircuitBreaker(p.name, domain=_DOMAIN) for p in providers}
        if with_breakers
        else None
    )
    policy = block.get("policy", "fallback")
    if policy == "fallback":
        return FallbackRouter(providers, breakers=breakers, domain=_DOMAIN)
    return AggregationRouter(providers, policy=policy, breakers=breakers, domain=_DOMAIN)


class CryptoDataProvider:
    """Fachada composta para dados de preço cripto.

    `config_key` seleciona o modo no sources.json: "crypto_price" (fallback
    sequencial, padrão) ou "crypto_price_consensus" (mediana Binance+Kraken).
    """

    def __init__(
        self,
        router=None,
        config_key: str = "crypto_price",
        config_path: Path | None = None,
        with_breakers: bool = True,
    ):
        # router injetável para teste; senão, montado a partir do sources.json.
        self._router = router or _build_router(config_key, config_path, with_breakers)

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        return await self._router.fetch_ohlcv(symbol, interval=interval, limit=limit)

    async def latest_close(self, symbol: str, interval: str = "1d") -> float:
        """Atalho: preço de fechamento mais recente, com fallback/agregação transparente."""
        points = await self._router.fetch_ohlcv(symbol, interval=interval, limit=1)
        return points[-1].close
