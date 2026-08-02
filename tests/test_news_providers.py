"""Contratos offline do roteador de fontes de notícias."""

import asyncio
import hashlib

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
    assert news.provider_order_for_asset("bitcoin", providers) == news.provider_order_for_asset(
        "bitcoin", providers
    )
    assert (
        len(
            {
                news.provider_order_for_asset(asset, providers)[0]
                for asset in ("bitcoin", "ethereum", "solana", "ripple", "cardano")
            }
        )
        > 1
    )


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


def test_curated_rss_blockworks_nao_usa_dominio_antigo():
    # Regressão (achado 2026-07-20, OP-7): blockworks.co migrou para
    # blockworks.com com redirect 308 permanente; get_http_client() não
    # segue redirect, então raise_for_status() derrubava TODA chamada que
    # hasheasse para "blockworks" com HTTPStatusError — silenciosamente
    # classificado como "fonte indisponível", nunca como bug de URL.
    assert news.CURATED_RSS_FEEDS["blockworks"] == "https://blockworks.com/feed/"
    assert ".co/" not in news.CURATED_RSS_FEEDS["blockworks"]


def test_curated_rss_coindesk_nao_usa_barra_antes_da_query():
    # Regressão (achado 2026-07-25): a rota do CoinDesk passou a responder 308
    # permanente quando ha barra antes do "?" — mesmo modo de falha do
    # blockworks acima. Como get_http_client() nao segue redirect, todo ativo
    # que hasheasse para "coindesk" perdia a fonte (5 previsoes/noite desde
    # 21/07). A URL correta e a mesma rota SEM a barra.
    url = news.CURATED_RSS_FEEDS["coindesk"]
    assert url == "https://www.coindesk.com/arc/outboundfeeds/rss?outputType=xml"
    assert "/rss/?" not in url


def test_curated_rss_nenhum_feed_tem_barra_antes_da_query():
    # Generaliza os dois achados: barra imediatamente antes da query string é o
    # padrão que produziu 308 em blockworks (2026-07-20) e coindesk
    # (2026-07-25). Barra a classe inteira do bug, não só as duas instâncias.
    for nome, url in news.CURATED_RSS_FEEDS.items():
        assert "/?" not in url, f"{nome} tem barra antes da query: {url}"


def test_curated_rss_propaga_erro_de_redirect_nao_seguido(monkeypatch):
    # Fixa o contrato que o bug acima violava: uma resposta cujo
    # raise_for_status() levanta (3xx não seguido, 4xx, 5xx) deve propagar
    # como falha ISOLADA da fonte — get_news_result() a categoriza no
    # degraded_reason em vez de deixar a exceção subir sem contexto.
    import httpx

    class _RedirectResponse:
        def raise_for_status(self):
            raise httpx.HTTPStatusError("308 redirect", request=None, response=None)

    class _RedirectClient:
        async def get(self, url, **kwargs):
            return _RedirectResponse()

    monkeypatch.setattr(news, "get_http_client", lambda: _ClientContext(_RedirectClient()))
    monkeypatch.setattr(news, "_PROVIDERS", {"curated_rss": news.CuratedRssProvider()})
    monkeypatch.setattr(news, "_OPEN_CIRCUITS", set())
    monkeypatch.setattr(news, "provider_order_for_asset", lambda asset: ["curated_rss"])
    result = asyncio.run(news.get_news_result("bitcoin"))
    assert result.provider == "none"
    assert result.degraded
    assert "curated_rss:HTTPStatusError" in result.degraded_reason


def _falha_curated(monkeypatch, status):
    """Monta um curated_rss cujo raise_for_status() falha com o status dado."""
    import httpx

    class _Resp:
        status_code = status

        def raise_for_status(self):
            erro = httpx.HTTPStatusError("falha", request=None, response=None)
            erro.response = self  # type: ignore[assignment]
            raise erro

    class _Cli:
        async def get(self, url, **kwargs):
            return _Resp()

    monkeypatch.setattr(news, "get_http_client", lambda: _ClientContext(_Cli()))
    monkeypatch.setattr(news, "_PROVIDERS", {"curated_rss": news.CuratedRssProvider()})
    monkeypatch.setattr(news, "_OPEN_CIRCUITS", set())
    monkeypatch.setattr(news, "_NEWS_CACHE", {})
    monkeypatch.setattr(news, "provider_order_for_asset", lambda asset: ["curated_rss"])


def test_marcador_de_falha_grava_status_http_e_feed(monkeypatch):
    # O tipo da exceção sozinho é ambíguo: HTTPStatusError cobre 3xx não
    # seguido, 4xx e 5xx. Sem o status, diagnosticar o 308 do coindesk exigiu
    # reproduzir a chamada na mão. O marcador persistido em
    # news_degraded_reason passa a carregar status e feed de origem.
    _falha_curated(monkeypatch, 308)
    resultado = asyncio.run(news.get_news_result("uniswap"))
    assert resultado.provider == "none"
    assert "curated_rss:HTTPStatusError:308@" in resultado.degraded_reason
    # o feed carimbado é o que a partição por hash escolheu para o ativo
    esperado = sorted(news.CURATED_RSS_FEEDS)[
        int.from_bytes(hashlib.sha256(b"uniswap").digest()[:4], "big") % len(news.CURATED_RSS_FEEDS)
    ]
    assert resultado.degraded_reason.endswith("@" + esperado)


def test_marcador_nao_vaza_url_nem_corpo(monkeypatch):
    # O marcador é persistido no banco e sai no log: só pode conter nome do
    # provider, tipo da exceção, status e chave do feed — nunca URL, que em
    # outros providers (serpapi) carrega a credencial na query string.
    _falha_curated(monkeypatch, 500)
    razao = asyncio.run(news.get_news_result("uniswap")).degraded_reason
    # "http" sozinho não serve como sonda: HTTPStatusError é o próprio tipo da
    # exceção. O que não pode aparecer é URL — esquema, host ou query string.
    assert "://" not in razao
    assert "?" not in razao and "/" not in razao
    assert not any(feed in razao for feed in news.CURATED_RSS_FEEDS.values())


def test_disjuntor_abre_em_429_e_5xx_mas_nao_em_redirect(monkeypatch):
    # Fixa a regra que o status agora torna auditável: 429/5xx derrubam a fonte
    # pela rodada inteira; um 3xx (URL errada) não deve abrir o disjuntor —
    # senão um feed com URL velha silencia os outros quatro.
    for status, deve_abrir in ((308, False), (404, False), (429, True), (503, True)):
        _falha_curated(monkeypatch, status)
        asyncio.run(news.get_news_result("uniswap"))
        assert ("curated_rss" in news._OPEN_CIRCUITS) is deve_abrir, status


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
    rows = to_prediction_rows(
        [
            {
                "ativo": "bitcoin",
                "data": "2026-07-17 00:00:00",
                "score": 70,
                "news_provider": "google_news_rss",
                "news_degraded_reason": None,
                "collection_policy": '{"news_providers":["google_news_rss"]}',
            },
            {"ativo": "ethereum", "data": "2026-07-17 00:00:00", "score": 60},
        ]
    )
    with FeatureStore(tmp_path / "news.db") as store:
        store.write_predictions(rows)
        got = {row["ativo"]: row for row in store.read_predictions()}
    assert got["BITCOIN"]["news_provider"] == "google_news_rss"
    assert got["BITCOIN"]["news_degraded_reason"] is None
    assert got["BITCOIN"]["collection_policy"] == '{"news_providers":["google_news_rss"]}'
    assert got["ETHEREUM"]["news_provider"] is None
    assert got["ETHEREUM"]["collection_policy"] is None
