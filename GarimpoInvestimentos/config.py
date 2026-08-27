from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from predictor_core.settings import require_secrets
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

CsvList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    """Typed operational settings. Scientific defaults remain unchanged."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name(".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = Field(default="", repr=False)
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: str = Field(default="", repr=False)
    OPENAI_MODEL: str = "gpt-4o-mini"
    GROQ_API_KEY: str = Field(default="", repr=False)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    CEREBRAS_API_KEY: str = Field(default="", repr=False)
    CEREBRAS_MODEL: str = "gpt-oss-120b"
    MISTRAL_API_KEY: str = Field(default="", repr=False)
    MISTRAL_MODEL: str = "mistral-small-latest"
    OPENROUTER_API_KEY: str = Field(default="", repr=False)
    OPENROUTER_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    LLM_MULTI_PROVIDERS: CsvList = ["gemini", "groq", "cerebras", "mistral"]

    SERP_API_KEY: str = Field(default="", repr=False)
    NEWS_PROVIDERS: CsvList = ["serpapi"]
    NEWS_FALLBACK_PROVIDER: str = ""
    CRYPTOPANIC_AUTH_TOKEN: str = Field(default="", repr=False)
    NEWSAPIAI_API_KEY: str = Field(default="", repr=False)
    MEDIASTACK_API_KEY: str = Field(default="", repr=False)
    COINGECKO_API_KEY: str = Field(default="", repr=False)

    LIMIAR_SCORE_MINIMO: float = 60.0
    DEFAULT_ASSETS: CsvList = ["bitcoin", "ethereum", "solana"]
    CACHE_TTL_HOURS: int = 6
    ENABLE_CACHE: bool = True
    SCORE_HORIZON_DAYS: int = 7
    LLM_PACING_SECONDS: float = 7.0
    LLM_ENSEMBLE_N: int = 1
    LLM_PREFILTER_ENABLED: bool = False
    LLM_PREFILTER_MIN_VOLUME_USD: float = 10_000_000.0
    LLM_PREFILTER_MIN_ABS_CHANGE_7D: float = 2.0
    API_GUARD_ENABLED: bool = False
    API_GUARD_MAX_INGEST_ASSETS: int = 0
    API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER: int = 0
    API_GUARD_MAX_LLM_CALLS_PER_PROVIDER: int = 0

    DATA_DIR: Path = Path("data")
    OUTPUT_DIR: Path = Path("output")
    CACHE_DIR: Path = Path("cache")
    LOG_LEVEL: str = "INFO"
    PROVIDER_TIMEOUT_SECONDS: float = 15.0
    PROVIDER_MAX_ATTEMPTS: int = 3
    PROVIDER_CIRCUIT_FAILURE_THRESHOLD: int = 5

    @field_validator("LLM_PROVIDER", "NEWS_FALLBACK_PROVIDER", mode="before")
    @classmethod
    def normalize_name(cls, value: Any) -> str:
        return str(value or "").strip().lower()

    @field_validator("LLM_MULTI_PROVIDERS", "NEWS_PROVIDERS", "DEFAULT_ASSETS", mode="before")
    @classmethod
    def parse_csv(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return list(value)

    @model_validator(mode="after")
    def validate_contract(self) -> Settings:
        allowed_news = {
            "serpapi",
            "cryptopanic",
            "newsapi_ai",
            "mediastack",
            "google_news_rss",
            "curated_rss",
        }
        unknown_news = set(self.NEWS_PROVIDERS) - allowed_news
        if not self.NEWS_PROVIDERS or unknown_news:
            raise ValueError(f"NEWS_PROVIDERS inválido: {sorted(unknown_news) or 'vazio'}")
        if len(set(self.NEWS_PROVIDERS)) != len(self.NEWS_PROVIDERS):
            raise ValueError("NEWS_PROVIDERS não pode conter duplicatas")
        if self.NEWS_FALLBACK_PROVIDER and self.NEWS_FALLBACK_PROVIDER not in allowed_news:
            raise ValueError("NEWS_FALLBACK_PROVIDER inválido")
        if self.NEWS_FALLBACK_PROVIDER in self.NEWS_PROVIDERS:
            raise ValueError("NEWS_FALLBACK_PROVIDER deve ficar fora de NEWS_PROVIDERS")
        guards = (
            self.API_GUARD_MAX_INGEST_ASSETS,
            self.API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER,
            self.API_GUARD_MAX_LLM_CALLS_PER_PROVIDER,
        )
        if any(value < 0 for value in guards):
            raise ValueError("limite de API não pode ser negativo")
        if self.LLM_PREFILTER_MIN_VOLUME_USD < 0 or self.LLM_PREFILTER_MIN_ABS_CHANGE_7D < 0:
            raise ValueError("limites do LLM prefilter não podem ser negativos")
        if self.LLM_ENSEMBLE_N < 1:
            raise ValueError("LLM_ENSEMBLE_N deve ser >= 1")
        provider_keys = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        allowed_llm = set(provider_keys)
        unknown_llm = set(self.LLM_MULTI_PROVIDERS) - allowed_llm
        if self.LLM_PROVIDER != "multi" and self.LLM_PROVIDER not in allowed_llm:
            raise ValueError(f"LLM_PROVIDER inválido: {self.LLM_PROVIDER!r}")
        if not self.LLM_MULTI_PROVIDERS or unknown_llm:
            raise ValueError(f"LLM_MULTI_PROVIDERS inválido: {sorted(unknown_llm) or 'vazio'}")
        if len(set(self.LLM_MULTI_PROVIDERS)) != len(self.LLM_MULTI_PROVIDERS):
            raise ValueError("LLM_MULTI_PROVIDERS não pode conter duplicatas")
        required_news = (
            ["SERP_API_KEY"]
            if "serpapi" in {*self.NEWS_PROVIDERS, self.NEWS_FALLBACK_PROVIDER}
            else []
        )
        if self.LLM_PROVIDER == "multi":
            required = [provider_keys[provider] for provider in self.LLM_MULTI_PROVIDERS]
        else:
            required = [provider_keys[self.LLM_PROVIDER]]
        # `require_secrets(*names)` (default env=None) lê os.environ CRU — mas o
        # pydantic-settings já resolveu os valores reais (de .env, env var do SO,
        # ou default) nos campos de `self`. Um `.env` correto e completo, mas sem
        # as mesmas chaves também exportadas como variável de ambiente do processo,
        # passaria raw os.environ vazio e falharia aqui mesmo com tudo certo
        # (auditoria 2026-08-19: reproduzido no pipeline de produção — GEMINI_API_KEY
        # e SERP_API_KEY presentes e válidas no .env, mas MissingCredentialsError
        # mesmo assim). Validar contra os valores JÁ RESOLVIDOS de self, não contra
        # o ambiente do processo.
        resolved = {name: getattr(self, name, "") for name in {*required_news, *required}}
        require_secrets(*required_news, *required, env=resolved)
        return self


settings = Settings()
