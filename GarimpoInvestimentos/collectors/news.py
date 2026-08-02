"""Roteamento auditável de fontes de notícias.

Cada ativo consulta uma fonte primária estável (hash do nome) e tenta as demais
somente quando a primeira está indisponível. Alterar ``NEWS_PROVIDERS`` muda o
input do LLM e exige uma nova trial forward.
"""

from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote_plus

from predictor_core.net import get_http_client

from GarimpoInvestimentos.collectors.serpapi_news import get_news_snippets as _serpapi
from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.api_guard import allow as guard_allow

_log = logging.getLogger("previsao_cripto.news")

# Catálogo curado a partir da lista RSS ativa da CoinDesk Data API. URLs versionadas
# evitam que uma troca editorial altere silenciosamente o experimento.
CURATED_RSS_FEEDS = {
    # A barra antes do "?" virou redirect 308 permanente para a MESMA rota sem
    # barra (achado 2026-07-25, mesmo modo de falha do blockworks abaixo):
    # get_http_client() nao segue redirect, entao raise_for_status() derrubava
    # TODA chamada que hasheasse para "coindesk" — 5 previsoes por noite desde
    # 21/07, deterministicamente. Confirmado por requisicao real: 200 + RSS
    # valido sem a barra, 308 com ela.
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss?outputType=xml",
    # blockworks.co -> blockworks.com: domínio migrou (308 permanente, achado
    # 2026-07-20 ao ativar o fallback pela 1ª vez); o cliente HTTP do núcleo
    # não segue redirect (get_http_client() é follow_redirects=False por
    # padrão), então a URL antiga derrubava esta fonte em TODA chamada que
    # hasheasse para "blockworks" — confirmado por reprodução real (200 direto
    # no domínio novo, Atom válido).
    "blockworks": "https://blockworks.com/feed/",
    "decrypt": "https://decrypt.co/feed",
    "cointelegraph": "https://cointelegraph.com/rss",
    "cryptopotato": "https://cryptopotato.com/category/crypto-news/feed/",
}


@dataclass(frozen=True)
class NewsResult:
    titles: list[str]
    provider: str
    degraded_reason: str | None = None

    @property
    def degraded(self) -> bool:
        return self.degraded_reason is not None


class NewsProvider(Protocol):
    name: str

    async def fetch(self, query: str, limit: int) -> list[str]: ...


class SerpApiProvider:
    name = "serpapi"

    async def fetch(self, query: str, limit: int) -> list[str]:
        return await _serpapi(query, limit)


class CryptoPanicProvider:
    name = "cryptopanic"
    URL = "https://cryptopanic.com/api/free/v1/posts/"

    async def fetch(self, query: str, limit: int) -> list[str]:
        if not settings.CRYPTOPANIC_AUTH_TOKEN:
            raise RuntimeError("CryptoPanic sem CRYPTOPANIC_AUTH_TOKEN")
        params = {"auth_token": settings.CRYPTOPANIC_AUTH_TOKEN, "public": "true", "kind": "news"}
        async with get_http_client() as client:
            response = await client.get(self.URL, params=params)
            response.raise_for_status()
            data = response.json()
        titles = [str(item.get("title", "")) for item in data.get("results", [])]
        return _matching_titles(titles, query, limit)


class NewsApiAiProvider:
    """Event Registry / NewsAPI.ai, com a chave somente no corpo POST."""

    name = "newsapi_ai"
    URL = "https://eventregistry.org/api/v1/article/getArticles"

    async def fetch(self, query: str, limit: int) -> list[str]:
        if not settings.NEWSAPIAI_API_KEY:
            raise RuntimeError("NewsAPI.ai sem NEWSAPIAI_API_KEY")
        payload = {
            "action": "getArticles",
            "keyword": query,
            "articlesPage": 1,
            "articlesCount": min(limit, 100),
            "articlesSortBy": "date",
            "articlesSortByAsc": False,
            "dataType": ["news"],
            "resultType": "articles",
            "apiKey": settings.NEWSAPIAI_API_KEY,
        }
        async with get_http_client() as client:
            response = await client.post(self.URL, json=payload)
            response.raise_for_status()
            data = response.json()
        articles = data.get("articles", {}).get("results", [])
        titles = [str(item.get("title", "")) for item in articles]
        return _matching_titles(titles, query, limit)


class MediastackProvider:
    name = "mediastack"
    URL = "https://api.mediastack.com/news"

    async def fetch(self, query: str, limit: int) -> list[str]:
        if not settings.MEDIASTACK_API_KEY:
            raise RuntimeError("Mediastack sem MEDIASTACK_API_KEY")
        params = {
            "access_key": settings.MEDIASTACK_API_KEY,
            "keywords": query,
            "languages": "en",
            "sort": "published_desc",
            "limit": min(limit, 100),
        }
        async with get_http_client() as client:
            response = await client.get(self.URL, params=params)
            response.raise_for_status()
            data = response.json()
        if data.get("error"):
            raise RuntimeError("Mediastack retornou erro da API")
        titles = [str(item.get("title", "")) for item in data.get("data", [])]
        return _matching_titles(titles, query, limit)


def _rss_titles(payload: bytes) -> list[str]:
    """Extrai títulos de RSS 2.0 ou Atom sem dependência externa."""
    root = ET.fromstring(payload)
    titles = [
        title.strip()
        for title in (item.findtext("title") for item in root.findall(".//item"))
        if title and title.strip()
    ]
    if not titles:
        atom = "{http://www.w3.org/2005/Atom}"
        titles = [
            title.strip()
            for title in (
                entry.findtext(f"{atom}title") for entry in root.findall(f".//{atom}entry")
            )
            if title and title.strip()
        ]
    return titles


def _matching_titles(titles: list[str], query: str, limit: int) -> list[str]:
    tokens = [part for part in query.lower().replace("-", " ").split() if len(part) > 2]
    return [title for title in titles if any(token in title.lower() for token in tokens)][:limit]


class GoogleNewsRssProvider:
    name = "google_news_rss"

    async def fetch(self, query: str, limit: int) -> list[str]:
        url = (
            "https://news.google.com/rss/search?q="
            + quote_plus(query)
            + "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        )
        async with get_http_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            return _rss_titles(response.content)[:limit]


class CuratedRssProvider:
    name = "curated_rss"

    async def fetch(self, query: str, limit: int) -> list[str]:
        keys = sorted(CURATED_RSS_FEEDS)
        digest = hashlib.sha256(query.strip().lower().encode("utf-8")).digest()
        source = keys[int.from_bytes(digest[:4], "big") % len(keys)]
        async with get_http_client() as client:
            try:
                response = await client.get(CURATED_RSS_FEEDS[source])
                response.raise_for_status()
                return _matching_titles(_rss_titles(response.content), query, limit)
            except Exception as exc:
                # Carimba QUAL feed falhou. O disjuntor (_OPEN_CIRCUITS) e por
                # PROVIDER, entao sem isto a queda de um unico feed aparece so
                # como "curated_rss indisponivel" — foi o que escondeu o 308 do
                # coindesk por 4 noites.
                exc.feed_source = source  # type: ignore[attr-defined]
                raise


_PROVIDERS: dict[str, NewsProvider] = {
    "serpapi": SerpApiProvider(),
    "cryptopanic": CryptoPanicProvider(),
    "newsapi_ai": NewsApiAiProvider(),
    "mediastack": MediastackProvider(),
    "google_news_rss": GoogleNewsRssProvider(),
    "curated_rss": CuratedRssProvider(),
}
_OPEN_CIRCUITS: set[str] = set()
_NEWS_CACHE: dict[tuple[str, str, int], list[str]] = {}


def provider_order_for_asset(asset: str, providers: list[str] | None = None) -> list[str]:
    """Primárias em ordem circular estável, seguidas de fallback opcional."""
    valid = [name for name in (providers or settings.NEWS_PROVIDERS) if name in _PROVIDERS]
    if not valid:
        return []
    digest = hashlib.sha256(asset.strip().lower().encode("utf-8")).digest()
    start = int.from_bytes(digest[:4], "big") % len(valid)
    order = valid[start:] + valid[:start]
    # O argumento ``providers`` e usado por testes/chamadores que querem uma
    # ordem fechada; a configuracao de fallback pertence apenas ao roteador real.
    fallback = settings.NEWS_FALLBACK_PROVIDER if providers is None else ""
    if fallback in _PROVIDERS and fallback not in order:
        order.append(fallback)
    return order


def _status_of(exc: BaseException) -> int | None:
    """Status HTTP da excecao, quando ela carrega uma resposta."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return status if isinstance(status, int) else None


def _failure_marker(name: str, exc: BaseException) -> str:
    """Marcador persistido em ``predictions.news_degraded_reason``.

    Formato: ``provider:TipoDaExcecao[:status][@feed]``. O tipo sozinho e
    ambiguo — ``HTTPStatusError`` cobre 3xx nao seguido, 4xx e 5xx, que tem
    causas e tratamentos completamente diferentes (redirect = URL errada;
    429/5xx = abre o disjuntor). Sem o status e o feed, diagnosticar exigia
    reproduzir a chamada na mao. Nunca inclui URL, corpo nem cabecalho: so
    nome do provider, tipo da excecao, inteiro do status e chave do feed.
    """
    marker = f"{name}:{type(exc).__name__}"
    status = _status_of(exc)
    if status is not None:
        marker += f":{status}"
    feed = getattr(exc, "feed_source", None)
    if feed:
        marker += f"@{feed}"
    return marker


async def get_news_result(query: str, limit: int = 5) -> NewsResult:
    """Busca uma fonte saudável e devolve provenance; nunca expõe credenciais."""
    failures: list[str] = []
    for name in provider_order_for_asset(query):
        if name in _OPEN_CIRCUITS:
            failures.append(f"{name}:circuit_open")
            continue
        cache_key = (name, query.strip().lower(), limit)
        if cache_key in _NEWS_CACHE:
            return NewsResult(_NEWS_CACHE[cache_key], name)
        budget = guard_allow("news", name, settings.API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER)
        if not budget.allowed:
            failures.append(budget.reason)
            continue
        try:
            titles = await _PROVIDERS[name].fetch(query, limit)
            if titles:
                _NEWS_CACHE[cache_key] = titles
                return NewsResult(titles=titles, provider=name)
            failures.append(f"{name}:empty")
        except Exception as exc:
            failures.append(_failure_marker(name, exc))
            status = _status_of(exc)
            if status == 429 or (isinstance(status, int) and status >= 500):
                # A fonte não vai se recuperar dentro da mesma rodada. Evita que
                # cada ativo repita retries e consuma a quota/tempo do agendador.
                _OPEN_CIRCUITS.add(name)
            _log.warning(
                "notícias %s indisponíveis para %s: %s (status=%s, feed=%s)",
                name,
                query,
                type(exc).__name__,
                status if status is not None else "-",
                getattr(exc, "feed_source", "-"),
            )
    return NewsResult([], "none", ",".join(failures)[:500] or "no_provider_configured")
