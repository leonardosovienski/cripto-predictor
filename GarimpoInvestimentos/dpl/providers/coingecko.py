"""CoinGeckoProvider — conector REST (fonte secundária / fallback de preço).

Usa o módulo de rede do core (`predictor_core.net`): httpx async + retry/backoff,
SSL verificado.

Para o intervalo diário ("1d") usa /market_chart?interval=daily, que entrega uma
série longa de closes + volume (base dos indicadores de 200 dias do domínio). Como
o /market_chart não traz OHLC completo, sintetizamos o candle com open=high=low=close
(série baseada em fechamento — os indicadores do domínio são todos sobre closes).
Para intervalos intradiários usa /ohlc (OHLC real, sem volume).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint
from GarimpoInvestimentos.dpl.providers._validation import require_finite

# /ohlc (intradiário): days → granularidade automática (1=30min, 7-30=4h).
_INTERVAL_TO_DAYS = {"1m": 1, "5m": 1, "15m": 1, "1h": 1, "4h": 7}


def coingecko_auth_headers() -> dict[str, str]:
    """Header da chave Demo do CoinGecko, se COINGECKO_API_KEY estiver no ambiente.

    Sobe o rate limit do free tier (evita o 429 que estrangula a coleta diária).
    Vazio se ausente — o endpoint público continua funcionando, só com limite menor.
    Lê do env direto (não do config do domínio) p/ a DPL seguir promovível ao core.
    """
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    return {"x-cg-demo-api-key": key} if key else {}


class CoinGeckoProvider(DataProvider):
    name = "coingecko"

    def __init__(self, symbol_map: dict[str, str] | None = None):
        # CoinGecko já usa IDs canônicos ("bitcoin"); o mapa é opcional e só
        # cobre exceções. Default: identidade.
        self._symbol_map = symbol_map or {}

    def _native_symbol(self, symbol: str) -> str:
        return self._symbol_map.get(symbol, symbol)

    @with_retry()
    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        coin_id = self._native_symbol(symbol)
        if interval == "1d":
            return await self._fetch_daily(symbol, coin_id, limit)
        return await self._fetch_intraday(symbol, coin_id, interval, limit)

    async def _fetch_daily(self, symbol, coin_id, limit) -> list[MarketDataPoint]:
        # days >= 2 com interval=daily devolve 1 ponto/dia; pedimos `limit` dias.
        days = max(limit, 2)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": str(days), "interval": "daily"}
        async with get_http_client() as client:
            resp = await client.get(url, params=params, headers=coingecko_auth_headers())
            resp.raise_for_status()
            data = resp.json()
        prices = data.get("prices", [])
        volumes = {int(ts): v for ts, v in data.get("total_volumes", [])}
        if not prices:
            raise RuntimeError(f"coingecko: resposta vazia para {coin_id}")
        points = []
        for ts_ms, price in prices[-limit:]:
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            c = require_finite(float(price), field="close", provider=self.name, symbol=symbol)
            vol = require_finite(float(volumes.get(int(ts_ms), 0.0)),
                                 field="volume", provider=self.name, symbol=symbol)
            points.append(
                MarketDataPoint(
                    symbol=symbol, timestamp=ts,
                    open=c, high=c, low=c, close=c,  # série de fechamento
                    volume=vol,
                    source=self.name, interval="1d", published_at=ts,
                )
            )
        return points

    async def _fetch_intraday(self, symbol, coin_id, interval, limit) -> list[MarketDataPoint]:
        days = _INTERVAL_TO_DAYS.get(interval, 1)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": str(days)}
        async with get_http_client() as client:
            resp = await client.get(url, params=params, headers=coingecko_auth_headers())
            resp.raise_for_status()
            rows = resp.json()
        if not rows:
            raise RuntimeError(f"coingecko: resposta vazia para {coin_id}")
        points = []
        for ts_ms, o, h, l, c in rows[-limit:]:
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            kw = {"open": float(o), "high": float(h), "low": float(l), "close": float(c)}
            for field, val in kw.items():
                require_finite(val, field=field, provider=self.name, symbol=symbol)
            points.append(
                MarketDataPoint(
                    symbol=symbol, timestamp=ts,
                    volume=0.0,  # /ohlc não fornece volume
                    source=self.name, interval=interval, published_at=ts,
                    **kw,
                )
            )
        return points

    async def health_check(self) -> bool:
        try:
            async with get_http_client() as client:
                resp = await client.get("https://api.coingecko.com/api/v3/ping",
                                        headers=coingecko_auth_headers())
                return resp.status_code == 200
        except Exception:
            return False
