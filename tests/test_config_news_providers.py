"""Validação fail-fast da configuração de fontes de notícias."""
import pytest

from GarimpoInvestimentos.config import Settings


def test_news_provider_desconhecido_e_rejeitado(monkeypatch):
    monkeypatch.setenv("NEWS_PROVIDERS", "serpapi,inventado")
    with pytest.raises(ValueError, match="NEWS_PROVIDERS inválido"):
        Settings()


def test_news_provider_duplicado_e_rejeitado(monkeypatch):
    monkeypatch.setenv("NEWS_PROVIDERS", "serpapi,serpapi")
    with pytest.raises(ValueError, match="duplicatas"):
        Settings()


def test_novos_news_providers_sao_aceitos_sem_gravar_credenciais(monkeypatch):
    monkeypatch.setenv("NEWS_PROVIDERS", "newsapi_ai,mediastack,google_news_rss")
    # O construtor exige uma credencial de LLM, mas fontes sem SerpAPI nao exigem
    # segredo de noticia durante a validacao da configuracao.
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key-long-enough")
    settings = Settings()
    assert settings.NEWS_PROVIDERS == ["newsapi_ai", "mediastack", "google_news_rss"]


def test_fallback_separado_e_validado(monkeypatch):
    monkeypatch.setenv("NEWS_PROVIDERS", "cryptopanic,newsapi_ai,mediastack")
    monkeypatch.setenv("NEWS_FALLBACK_PROVIDER", "serpapi")
    monkeypatch.setenv("SERP_API_KEY", "unit-test-key-long-enough")
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key-long-enough")
    settings = Settings()
    assert settings.NEWS_FALLBACK_PROVIDER == "serpapi"

    monkeypatch.setenv("NEWS_PROVIDERS", "serpapi,cryptopanic")
    with pytest.raises(ValueError, match="deve ficar fora"):
        Settings()


def test_teto_negativo_e_rejeitado(monkeypatch):
    monkeypatch.setenv("API_GUARD_MAX_LLM_CALLS_PER_PROVIDER", "-1")
    with pytest.raises(ValueError, match="não pode ser negativo"):
        Settings()
