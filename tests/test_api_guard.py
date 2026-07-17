"""Guardas de custo antes das chamadas externas da Fase 1."""
import asyncio
from datetime import datetime, timezone

from GarimpoInvestimentos.collectors import news
from GarimpoInvestimentos.core import api_guard
from GarimpoInvestimentos.dpl.providers.fear_greed import FearAndGreedProvider
from GarimpoInvestimentos.dpl.signals import SignalPoint


def test_guarda_desligada_nao_muda_comportamento(monkeypatch):
    monkeypatch.setattr(api_guard.settings, "API_GUARD_ENABLED", False)
    api_guard.reset_for_test()
    assert api_guard.allow("llm", "gemini", 1).allowed
    assert api_guard.allow("llm", "gemini", 1).allowed


def test_guarda_bloqueia_antes_da_unidade_seguinte(monkeypatch):
    monkeypatch.setattr(api_guard.settings, "API_GUARD_ENABLED", True)
    api_guard.reset_for_test()
    assert api_guard.allow("news", "serpapi", 1).allowed
    denied = api_guard.allow("news", "serpapi", 1)
    assert not denied.allowed
    assert denied.reason == "budget_exhausted:news:serpapi"


def test_news_cache_evita_nova_chamada(monkeypatch):
    class _Provider:
        name = "one"
        calls = 0

        async def fetch(self, query, limit):
            self.calls += 1
            return ["Bitcoin noticia"]

    provider = _Provider()
    monkeypatch.setattr(news, "_PROVIDERS", {"one": provider})
    monkeypatch.setattr(news, "_NEWS_CACHE", {})
    monkeypatch.setattr(news, "_OPEN_CIRCUITS", set())
    monkeypatch.setattr(news, "provider_order_for_asset", lambda asset: ["one"])
    assert asyncio.run(news.get_news_result("bitcoin")).titles
    assert asyncio.run(news.get_news_result("bitcoin")).titles
    assert provider.calls == 1


def test_fear_greed_cache_nao_toca_rede_uma_segunda_vez():
    provider = FearAndGreedProvider()
    points = [SignalPoint(name="fear_greed", timestamp=datetime.now(timezone.utc), value=50,
                          source="alternative.me", published_at=datetime.now(timezone.utc))]
    provider._cache[30] = points
    assert asyncio.run(provider.fetch(30)) == points
