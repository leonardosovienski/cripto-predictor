"""Descoberta de candidatos no mercado (CoinGecko) — gera a lista de ativos do pipeline.

Varre o topo do mercado (/coins/markets) + trending (/search/trending), filtra
stablecoins, wrapped/staked e baixa liquidez, e ranqueia por momentum recente.

⚠️ Isto é GERAÇÃO DE CANDIDATOS, não sinal de trade: momentum 7d/24h é um pré-filtro
heurístico para decidir O QUE analisar (quem pontua é o pipeline LLM + indicadores).
A pré-seleção por momentum enviesa o histórico coletado (só "vencedores recentes"
entram) — o backtest da Fase 2 mede o edge CONDICIONAL a essa pré-seleção, que é
exatamente o processo que rodaria em produção.
"""
from predictor_core.net import get_http_client, with_retry

# Símbolos que nunca são "oportunidade": paridade com fiat (stable) ou espelho de
# outro ativo (wrapped/staked — redundante com o subjacente, que já é elegível).
STABLECOIN_SYMBOLS = {
    "usdt", "usdc", "usds", "usde", "dai", "fdusd", "pyusd", "tusd", "usdd",
    "usdp", "gusd", "frax", "lusd", "susd", "crvusd", "busd", "usd1", "usdt0",
    "usdtb", "rlusd", "eurc", "eurt", "usdy", "usd0",
}
WRAPPED_SYMBOLS = {
    "wbtc", "weth", "wbnb", "steth", "wsteth", "reth", "cbeth", "cbbtc", "weeth",
    "wbeth", "rseth", "ezeth", "meth", "lbtc", "tbtc", "solvbtc", "msol",
    "jitosol", "bnsol", "jupsol", "stsol", "wpol", "wtrx",
}


def _is_stablecoin(row: dict) -> bool:
    if (row.get("symbol") or "").lower() in STABLECOIN_SYMBOLS:
        return True
    # Heurística p/ stables fora da lista (listas envelhecem): cola no $1 e não anda.
    price = row.get("current_price") or 0.0
    change_7d = row.get("price_change_percentage_7d_in_currency") or 0.0
    return 0.97 <= price <= 1.03 and abs(change_7d) < 1.0


def rank_candidates(
    markets: list[dict],
    top_n: int = 10,
    min_volume_usd: float = 10_000_000.0,
    trending_ids: tuple[str, ...] = (),
) -> list[str]:
    """Filtra e ranqueia candidatos. Puro (sem rede/settings) — testável sem .env.

    `markets` são linhas do /coins/markets (id, symbol, current_price, total_volume,
    price_change_percentage_{24h,7d}_in_currency). Ranking: momentum 7d + metade do
    24h (recência desempata sem dominar) + bônus fixo se está no trending (interesse
    de mercado que o momentum puro ainda não capturou). Pesos são heurísticos de
    triagem — calibrá-los "no olho" contra retorno futuro seria overfitting manual.
    """
    trending = set(trending_ids)
    scored: list[tuple[float, str]] = []
    for row in markets:
        coin_id = row.get("id")
        if not coin_id:
            continue
        if (row.get("total_volume") or 0.0) < min_volume_usd:
            continue
        if _is_stablecoin(row) or (row.get("symbol") or "").lower() in WRAPPED_SYMBOLS:
            continue
        change_7d = row.get("price_change_percentage_7d_in_currency") or 0.0
        change_24h = row.get("price_change_percentage_24h_in_currency") or 0.0
        momentum = change_7d + 0.5 * change_24h + (10.0 if coin_id in trending else 0.0)
        scored.append((momentum, coin_id))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [coin_id for _, coin_id in scored[:top_n]]


@with_retry()
async def _fetch_markets(per_page: int = 100) -> list[dict]:
    """Top `per_page` por market cap, com variações 24h/7d — universo da varredura."""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": str(per_page),
        "page": "1",
        "price_change_percentage": "24h,7d",
    }
    async with get_http_client() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


@with_retry()
async def _fetch_trending_ids() -> tuple[str, ...]:
    url = "https://api.coingecko.com/api/v3/search/trending"
    async with get_http_client() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    return tuple(
        item["item"]["id"] for item in data.get("coins", []) if item.get("item", {}).get("id")
    )


async def discover_assets(top_n: int = 10, min_volume_usd: float = 10_000_000.0) -> list[str]:
    """Lista de coin_ids candidatos para o pipeline analisar. Levanta se o mercado falhar;
    trending indisponível só degrada (segue sem o bônus)."""
    markets = await _fetch_markets()
    try:
        trending = await _fetch_trending_ids()
    except Exception:
        trending = ()
    return rank_candidates(markets, top_n=top_n, min_volume_usd=min_volume_usd,
                           trending_ids=trending)
