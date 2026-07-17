"""Contratos offline do roteador de fontes de notícias."""
import asyncio

from GarimpoInvestimentos.collectors import news
from GarimpoInvestimentos.core.history import to_prediction_rows
from GarimpoInvestimentos.dpl import FeatureStore


class _Provider:
    def __init__(self, name, result=None, error=None):
        self.name, self.result, self.error = name, result or [], error
        self.calls = 0

    async def fetch(self, query, limit):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result[:limit]


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _ClientContext:
    def __init__(self, client):
        self.client = client

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, *args):
        return None


class _Client:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return _Response(self.payload)

    async def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return _Response(self.payload)


def test_rss_parser_suporta_rss_e_atom():
    rss = b"<rss><channel><item><title>Bitcoin sobe</title></item></channel></rss>"
    atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Ethereum cai</title></entry></feed>'
    assert news._rss_titles(rss) == ["Bitcoin sobe"]
    assert news._rss_titles(atom) == ["Ethereum cai"]


def test_ordem_por_ativo_e_estavel_e_distribuida():
    providers = ["serpapi", "cryptopanic", "google_news_rss", "curated_rss"]
    assert news.provider_order_for_asset("bitcoin", providers) == news.provider_order_for_asset("bitcoin", providers)
    assert len({news.provider_order_for_asset(asset, providers)[0] for asset in ("bitcoin", "ethereum", "solana", "ripple", "cardano")}) > 1


def test_fallback_configurado_e_ultima_tentativa(monkeypatch):
    monkeypatch.setattr(news.settings, "NEWS_PROVIDERS", ["cryptopanic", "newsapi_ai"])
    monkeypatch.setattr(news.settings, "NEWS_FALLBACK_PROVIDER", "serpapi")
    order = news.provider_order_for_asset("bitcoin")
    assert set(order[:-1]) == {"cryptopanic", "newsapi_ai"}
    assert order[-1] == "serpapi"


def test_fallback_nao_mistura_titulos(monkeypatch):
    first = _Provider("one", error=RuntimeError("offline"))
    second = _Provider("two", result=["Bitcoin noticia"])
    monkeypatch.setattr(news, "_PROVIDERS", {"one": first, "two": second})
    monkeypatch.setattr(news, "_OPEN_CIRCUITS", set())
    monkeypatch.setattr(news, "provider_order_for_asset", lambda asset: ["one", "two"])
    result = asyncio.run(news.get_news_result("bitcoin"))
    assert result.provider == "two"
    assert result.titles == ["Bitcoin noticia"]
    assert first.calls == second.calls == 1


def test_429_abre_circuito_na_rodada(monkeypatch):
    class _Response:
        status_code = 429

    class _RateLimited(RuntimeError):
        response = _Response()

    limited = _Provider("limited", error=_RateLimited())
    fallback = _Provider("fallback", result=["Bitcoin noticia"])
    monkeypatch.setattr(news, "_PROVIDERS", {"limited": limited, "fallback": fallback})
    monkeypatch.setattr(news, "_OPEN_CIRCUITS", set())
    monkeypatch.setattr(news, "provider_order_for_asset", lambda asset: ["limited", "fallback"])
    assert asyncio.run(news.get_news_result("bitcoin")).provider == "fallback"
    assert asyncio.run(news.get_news_result("ethereum")).provider == "fallback"
    assert limited.calls == 1


def test_newsapi_ai_envia_chave_no_corpo_e_normaliza_titulos(monkeypatch):
    client = _Client({"articles": {"results": [{"title": "Bitcoin gains today"}]}})
    monkeypatch.setattr(news.settings, "NEWSAPIAI_API_KEY", "unit-test-key")
    monkeypatch.setattr(news, "get_http_client", lambda: _ClientContext(client))
    result = asyncio.run(news.NewsApiAiProvider().fetch("bitcoin", 5))
    assert result == ["Bitcoin gains today"]
    method, _, kwargs = client.calls[0]
    assert method == "post"
    assert kwargs["json"]["apiKey"] == "unit-test-key"


def test_mediastack_envia_consulta_e_rejeita_erro_da_api(monkeypatch):
    client = _Client({"data": [{"title": "Ethereum market update"}]})
    monkeypatch.setattr(news.settings, "MEDIASTACK_API_KEY", "unit-test-key")
    monkeypatch.setattr(news, "get_http_client", lambda: _ClientContext(client))
    result = asyncio.run(news.MediastackProvider().fetch("ethereum", 5))
    assert result == ["Ethereum market update"]
    method, _, kwargs = client.calls[0]
    assert method == "get"
    assert kwargs["params"]["access_key"] == "unit-test-key"

    error_client = _Client({"error": {"code": "invalid_access_key"}})
    monkeypatch.setattr(news, "get_http_client", lambda: _ClientContext(error_client))
    try:
        asyncio.run(news.MediastackProvider().fetch("ethereum", 5))
    except RuntimeError as exc:
        assert str(exc) == "Mediastack retornou erro da API"
    else:
        raise AssertionError("erro da API deveria interromper o provider")


def test_provenance_de_noticias_persiste_e_legado_permanece_null(tmp_path):
    rows = to_prediction_rows([
        {"ativo": "bitcoin", "data": "2026-07-17 00:00:00", "score": 70,
         "news_provider": "google_news_rss", "news_degraded_reason": None,
         "collection_policy": "{\"news_providers\":[\"google_news_rss\"]}"},
        {"ativo": "ethereum", "data": "2026-07-17 00:00:00", "score": 60},
    ])
    with FeatureStore(tmp_path / "news.db") as store:
        store.write_predictions(rows)
        got = {row["ativo"]: row for row in store.read_predictions()}
    assert got["BITCOIN"]["news_provider"] == "google_news_rss"
    assert got["BITCOIN"]["news_degraded_reason"] is None
    assert got["BITCOIN"]["collection_policy"] == "{\"news_providers\":[\"google_news_rss\"]}"
    assert got["ETHEREUM"]["news_provider"] is None
    assert got["ETHEREUM"]["collection_policy"] is None
