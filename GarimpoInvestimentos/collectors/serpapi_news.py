from GarimpoInvestimentos.config import settings
from predictor_core.net import get_http_client, with_retry

@with_retry()
async def get_news_snippets(query: str, limit: int = 5) -> list[str]:
    """Busca notícias recentes sobre o ativo via SerpAPI (Google News).

    Usa a busca de notícias (`tbm=nws`) com o nome do ativo. O filtro antigo
    `site:news.google.com` zerava os resultados, então foi removido.
    """
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "tbm": "nws",
        "api_key": settings.SERP_API_KEY,
    }
    async with get_http_client() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    # SerpAPI pode responder 200 com um campo "error" (cota esgotada, etc.)
    if data.get("error"):
        return []
    return [n.get("title", "") for n in data.get("news_results", [])[:limit]]
