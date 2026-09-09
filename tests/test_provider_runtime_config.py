"""Configuration must reach the outbound transport, not just validate on startup."""

import asyncio

import httpx

from GarimpoInvestimentos.config import Settings
from GarimpoInvestimentos.dpl.facade import CryptoDataProvider
from GarimpoInvestimentos.dpl.providers.coingecko import CoinGeckoProvider, coingecko_auth_headers


def test_dotenv_key_reaches_facade_and_collectors(monkeypatch, tmp_path):
    from GarimpoInvestimentos import config
    from GarimpoInvestimentos.collectors import coingecko_api, discovery
    from GarimpoInvestimentos.dpl.providers import coingecko

    secret = "synthetic-demo-key-from-dotenv"
    env_file = tmp_path / "provider.env"
    env_file.write_text(f"COINGECKO_API_KEY={secret}\n", encoding="utf-8")
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    configured = Settings(_env_file=env_file)
    for module in (config, coingecko_api, discovery):
        monkeypatch.setattr(module, "settings", configured)
    seen = []

    def transport(request):
        seen.append(request)
        assert request.headers["x-cg-demo-api-key"] == secret
        if request.url.path.endswith("market_chart"):
            return httpx.Response(
                200,
                json={
                    "prices": [[1704067200000, 42000]],
                    "total_volumes": [[1704067200000, 1000000]],
                },
            )
        return httpx.Response(200, json=[])

    def client():
        return httpx.AsyncClient(transport=httpx.MockTransport(transport))

    for module in (coingecko, coingecko_api, discovery):
        monkeypatch.setattr(module, "get_http_client", client)
    provider = CryptoDataProvider(with_breakers=False)
    # Force the real facade's fallback connector without a public network call.
    connector = next(p for p in provider._router._providers if isinstance(p, CoinGeckoProvider))
    assert asyncio.run(connector.fetch_ohlcv("bitcoin", limit=2))[0].close == 42000
    assert asyncio.run(connector.health_check())
    assert asyncio.run(coingecko_api.get_price_series("bitcoin")) == [42000]
    assert len(seen) == 3


def test_standalone_key_precedence_and_explicit_anonymous(monkeypatch):
    monkeypatch.setenv("COINGECKO_API_KEY", "synthetic-process-key")
    assert coingecko_auth_headers() == {"x-cg-demo-api-key": "synthetic-process-key"}
    assert coingecko_auth_headers("injected") == {"x-cg-demo-api-key": "injected"}
    assert coingecko_auth_headers("") == {}


def test_ccxt_delivers_200_closed_candles_and_sma200(monkeypatch):
    from datetime import UTC, datetime, timedelta

    from GarimpoInvestimentos.dpl.feature_engineering import derive_features
    from GarimpoInvestimentos.dpl.providers.binance import BinanceProvider

    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = [
        [int((today - timedelta(days=200 - i)).timestamp() * 1000), 100, 100, 100, 100, 2]
        for i in range(201)
    ]

    class Client:
        async def fetch_ohlcv(self, pair, timeframe, limit):
            return rows[-limit:]

        async def close(self):
            pass

    provider = BinanceProvider({"bitcoin": "BTC/USDT"})
    monkeypatch.setattr(provider, "_client", Client)
    points = asyncio.run(provider.fetch_ohlcv("bitcoin", limit=200))
    assert len(points) == 200
    assert all(p.published_at <= today for p in points)
    assert derive_features(points)["sma_200"] == 100
