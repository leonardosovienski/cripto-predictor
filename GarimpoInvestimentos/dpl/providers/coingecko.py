"""CoinGeckoProvider — conector REST (fonte secundária / fallback de preço).

Usa o módulo de rede do core (`predictor_core.net`): httpx async + retry/backoff,
SSL verificado. O endpoint /ohlc não traz volume; preenchemos com 0.0 (o piloto da
Fase 1 valida redundância de PREÇO — volume consolidado fica para a agregação da
Fase 3).
"""
from __future__ import annotations

from datetime import datetime, timezone

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint

# CoinGecko /ohlc aceita days; a granularidade é derivada automaticamente
# (days=1 → velas de 30min). Mapeamos o intervalo do domínio para um days mínimo.
_INTERVAL_TO_DAYS = {"1m": 1, "5m": 1, "15m": 1, "1h": 1, "4h": 7, "1d": 30}


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
        days = _INTERVAL_TO_DAYS.get(interval, 1)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": str(days)}
        async with get_http_client() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            rows = resp.json()
        if not rows:
            raise RuntimeError(f"coingecko: resposta vazia para {coin_id}")
        points = []
        for ts_ms, o, h, l, c in rows[-limit:]:
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            points.append(
                MarketDataPoint(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=0.0,  # /ohlc não fornece volume
                    source=self.name,
                    interval=interval,
                    published_at=ts,
                )
            )
        return points

    async def health_check(self) -> bool:
        try:
            async with get_http_client() as client:
                resp = await client.get("https://api.coingecko.com/api/v3/ping")
                return resp.status_code == 200
        except Exception:
            return False
