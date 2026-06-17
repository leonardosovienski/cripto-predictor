from pydantic import BaseModel
from predictor_core.net import get_http_client, with_retry


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
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    market = data["market_data"]
    return CoinData(
        id=data["id"],
        symbol=data["symbol"],
        price_usd=market["current_price"]["usd"],
        volume_usd=market["total_volume"]["usd"],
        change_24h=market["price_change_percentage_24h"] or 0.0,
        change_7d=market["price_change_percentage_7d"] or 0.0,
        change_30d=market["price_change_percentage_30d"] or 0.0,
    )


@with_retry()
async def get_price_series(coin_id: str, days: int = 200) -> list[float]:
    """Closes diários (USD) dos últimos `days` dias — base para os indicadores técnicos.

    CoinGecko free entrega granularidade diária automaticamente para days > 90.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": str(days)}
    async with get_http_client() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return [point[1] for point in data.get("prices", [])]
