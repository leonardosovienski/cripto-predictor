import logging

from pydantic import BaseModel
from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.providers.coingecko import coingecko_auth_headers

_log = logging.getLogger("previsao_cripto.coingecko")


class CoinData(BaseModel):
    id: str
    symbol: str
    price_usd: float
    volume_usd: float
    change_24h: float
    change_7d: float
    change_30d: float


@with_retry()
async def get_coin_data(coin_id: str) -> CoinData:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    async with get_http_client() as client:
        resp = await client.get(url, headers=coingecko_auth_headers())
        resp.raise_for_status()
        data = resp.json()

    market = data["market_data"]
    coin = CoinData(
        id=data["id"],
        symbol=data["symbol"],
        price_usd=market["current_price"]["usd"],
        volume_usd=market["total_volume"]["usd"],
        change_24h=market["price_change_percentage_24h"] or 0.0,
        change_7d=market["price_change_percentage_7d"] or 0.0,
        change_30d=market["price_change_percentage_30d"] or 0.0,
    )
    _log.debug("coingecko: %s preco=%.2f vol=%.0f", coin_id, coin.price_usd, coin.volume_usd)
    return coin


@with_retry()
async def get_price_series(coin_id: str, days: int = 200) -> list[float]:
    """Closes diários (USD) dos últimos `days` dias — base para os indicadores técnicos.

    CoinGecko free entrega granularidade diária automaticamente para days > 90.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": str(days)}
    async with get_http_client() as client:
        resp = await client.get(url, params=params, headers=coingecko_auth_headers())
        resp.raise_for_status()
        data = resp.json()
    closes = [point[1] for point in data.get("prices", [])]
    _log.debug("coingecko: %s serie de %d closes (%d dias pedidos)", coin_id, len(closes), days)
    return closes
