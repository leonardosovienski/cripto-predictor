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
from datetime import UTC, datetime, timedelta

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint
from GarimpoInvestimentos.dpl.providers._validation import require_finite

# /ohlc (intradiário): days → granularidade automática (1=30min, 7-30=4h).
_INTERVAL_TO_DAYS = {"30m": 1, "4h": 7}
_DURATIONS = {"30m": timedelta(minutes=30), "4h": timedelta(hours=4)}


def coingecko_auth_headers(api_key: str | None = None) -> dict[str, str]:
    """Header Demo: configuração injetada, ou ambiente para uso isolado da DPL.

    Sobe o rate limit do free tier (evita o 429 que estrangula a coleta diária).
    Vazio se ausente — o endpoint público continua funcionando, só com limite menor.
    O domínio injeta o valor já resolvido do dotenv. None mantém o uso independente
    via ambiente; string vazia explícita desabilita a credencial.
    """
    key = (os.getenv("COINGECKO_API_KEY", "") if api_key is None else api_key).strip()
    return {"x-cg-demo-api-key": key} if key else {}


class CoinGeckoProvider(DataProvider):
    name = "coingecko"

    def __init__(self, symbol_map: dict[str, str] | None = None, *, api_key: str | None = None):
        # CoinGecko já usa IDs canônicos ("bitcoin"); o mapa é opcional e só
        # cobre exceções. Default: identidade.
        self._symbol_map = symbol_map or {}
        self._api_key = api_key

    def _native_symbol(self, symbol: str) -> str:
        return self._symbol_map.get(symbol, symbol)

    @with_retry()
    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        if limit < 1:
            raise ValueError("limit deve ser positivo")
        if interval not in {"1d", *_INTERVAL_TO_DAYS}:
            raise ValueError("coingecko: intervalo não oferecido pelo endpoint Demo OHLC")
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
            resp = await client.get(
                url, params=params, headers=coingecko_auth_headers(self._api_key)
            )
            resp.raise_for_status()
            data = resp.json()
        prices = data.get("prices", [])
        volumes = {int(ts): v for ts, v in data.get("total_volumes", [])}
        if not prices:
            raise RuntimeError(f"coingecko: resposta vazia para {coin_id}")
        points = []
        now = datetime.now(UTC)
        seen = set()
        for ts_ms, price in prices:
            close_at = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
            # market_chart appends a current partial point. Daily observations
            # are midnight UTC; the Demo documentation states a 10 minute lag.
            if close_at.time() != datetime.min.time() or close_at + timedelta(minutes=10) > now:
                continue
            if close_at in seen:
                raise ValueError("coingecko: duplicate daily timestamp")
            seen.add(close_at)
            ts = close_at - timedelta(days=1)
            if int(ts_ms) not in volumes:
                raise ValueError("coingecko: daily volume missing at price timestamp")
            c = require_finite(float(price), field="close", provider=self.name, symbol=symbol)
            vol = require_finite(
                float(volumes.get(int(ts_ms), 0.0)),
                field="volume",
                provider=self.name,
                symbol=symbol,
            )
            points.append(
                MarketDataPoint(
                    symbol=symbol,
                    timestamp=ts,
                    open=c,
                    high=c,
                    low=c,
                    close=c,  # série de fechamento
                    volume=vol,
                    source=self.name,
                    interval="1d",
                    published_at=close_at + timedelta(minutes=10),
                )
            )
        if not points:
            raise RuntimeError("coingecko: no completed daily observations")
        return sorted(points, key=lambda point: point.timestamp)[-limit:]

    async def _fetch_intraday(self, symbol, coin_id, interval, limit) -> list[MarketDataPoint]:
        if interval not in _INTERVAL_TO_DAYS:
            raise ValueError("coingecko: intervalo não oferecido pelo endpoint Demo OHLC")
        days = _INTERVAL_TO_DAYS[interval]
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": str(days)}
        async with get_http_client() as client:
            resp = await client.get(
                url, params=params, headers=coingecko_auth_headers(self._api_key)
            )
            resp.raise_for_status()
            rows = resp.json()
        if not rows:
            raise RuntimeError(f"coingecko: resposta vazia para {coin_id}")
        points = []
        now = datetime.now(UTC)
        duration = _DURATIONS[interval]
        seen = set()
        for ts_ms, o, h, l, c in rows:
            close_at = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
            if close_at > now:
                continue
            if ts_ms % int(duration.total_seconds() * 1000) or close_at in seen:
                raise ValueError("coingecko: invalid OHLC timestamp grid")
            seen.add(close_at)
            ts = close_at - duration
            kw = {"open": float(o), "high": float(h), "low": float(l), "close": float(c)}
            for field, val in kw.items():
                require_finite(val, field=field, provider=self.name, symbol=symbol)
            points.append(
                MarketDataPoint(
                    symbol=symbol,
                    timestamp=ts,
                    volume=0.0,  # /ohlc não fornece volume
                    source=self.name,
                    interval=interval,
                    published_at=close_at,
                    **kw,
                )
            )
        if not points:
            raise RuntimeError("coingecko: no completed OHLC observations")
        return sorted(points, key=lambda point: point.timestamp)[-limit:]

    async def health_check(self) -> bool:
        try:
            async with get_http_client() as client:
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/ping",
                    headers=coingecko_auth_headers(self._api_key),
                )
                return resp.status_code == 200
        except Exception:
            return False
