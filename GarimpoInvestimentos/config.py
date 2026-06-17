from dataclasses import dataclass, field
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    # Caminho explícito do .env ao lado deste arquivo — robusto a cwd e ao modo de
    # invocação (python -m, -c, importado por testes). Não depende do frame-walk do dotenv.
    load_dotenv(Path(__file__).with_name(".env"))
except Exception:
    pass


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # --- Provedor de LLM ---
    LLM_PROVIDER: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "gemini").strip().lower())
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    # --- Notícias ---
    SERP_API_KEY: str = field(default_factory=lambda: os.getenv("SERP_API_KEY", ""))

    # --- Pipeline ---
    LIMIAR_SCORE_MINIMO: float = field(default_factory=lambda: float(os.getenv("LIMIAR_SCORE_MINIMO", "60")))
    DEFAULT_ASSETS: list[str] = field(default_factory=lambda: [asset.strip() for asset in os.getenv("DEFAULT_ASSETS", "bitcoin,ethereum,solana").split(",") if asset.strip()])
    CACHE_TTL_HOURS: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_HOURS", "6")))
    ENABLE_CACHE: bool = field(default_factory=lambda: parse_bool(os.getenv("ENABLE_CACHE"), True))
    # Horizonte (em dias) ao qual o score do LLM se refere e que o backtest usa como correlação principal.
    SCORE_HORIZON_DAYS: int = field(default_factory=lambda: int(os.getenv("SCORE_HORIZON_DAYS", "7")))

    def __post_init__(self):
        # SerpAPI é sempre obrigatória; a chave de LLM exigida depende do provedor escolhido.
        required = {"SERP_API_KEY": self.SERP_API_KEY}
        if self.LLM_PROVIDER == "openai":
            required["OPENAI_API_KEY"] = self.OPENAI_API_KEY
        else:
            required["GEMINI_API_KEY"] = self.GEMINI_API_KEY
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Variáveis obrigatórias ausentes no .env: {', '.join(missing)}")


settings = Settings()
