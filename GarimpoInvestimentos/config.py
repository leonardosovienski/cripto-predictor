from dataclasses import dataclass, field
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    # Caminho explícito do .env ao lado deste arquivo — robusto a cwd e ao modo de
    # invocação (python -m, -c, importado por testes). Não depende do frame-walk do dotenv.
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    # dotenv é dependência OPCIONAL: ausente → segue lendo do ambiente já exportado.
    # Só ImportError é tolerado; um .env corrompido (OSError/ValueError) deve estourar,
    # não ser engolido — senão a app roda sem credenciais e a falha vira silenciosa.
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
    # Provedores OpenAI-compatíveis com free tier (mesma API, base_url distinto).
    # ⚠️ Trocar de provedor = trocar de JUIZ (judge_signature muda) = trial NOVA no
    # Experiment Registry. Não misturar na mesma janela de coleta (ver ai_insights).
    GROQ_API_KEY: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    GROQ_MODEL: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    CEREBRAS_API_KEY: str = field(default_factory=lambda: os.getenv("CEREBRAS_API_KEY", ""))
    CEREBRAS_MODEL: str = field(default_factory=lambda: os.getenv("CEREBRAS_MODEL", "gpt-oss-120b"))
    MISTRAL_API_KEY: str = field(default_factory=lambda: os.getenv("MISTRAL_API_KEY", ""))
    MISTRAL_MODEL: str = field(default_factory=lambda: os.getenv("MISTRAL_MODEL", "mistral-small-latest"))

    # --- Notícias ---
    SERP_API_KEY: str = field(default_factory=lambda: os.getenv("SERP_API_KEY", ""))

    # --- Dados de mercado (opcional) ---
    # Chave Demo do CoinGecko: sobe o rate limit do free tier (evita 429 na coleta
    # diária). OPCIONAL — sem ela o endpoint público segue funcionando, só com limite
    # menor. Não entra na trava P0 (não é obrigatória).
    COINGECKO_API_KEY: str = field(default_factory=lambda: os.getenv("COINGECKO_API_KEY", ""))

    # --- Pipeline ---
    LIMIAR_SCORE_MINIMO: float = field(default_factory=lambda: float(os.getenv("LIMIAR_SCORE_MINIMO", "60")))
    DEFAULT_ASSETS: list[str] = field(default_factory=lambda: [asset.strip() for asset in os.getenv("DEFAULT_ASSETS", "bitcoin,ethereum,solana").split(",") if asset.strip()])
    CACHE_TTL_HOURS: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_HOURS", "6")))
    ENABLE_CACHE: bool = field(default_factory=lambda: parse_bool(os.getenv("ENABLE_CACHE"), True))
    # Horizonte (em dias) ao qual o score do LLM se refere e que o backtest usa como correlação principal.
    SCORE_HORIZON_DAYS: int = field(default_factory=lambda: int(os.getenv("SCORE_HORIZON_DAYS", "7")))
    # Pausa (segundos) entre análises de ativos — respeita o limite POR MINUTO do LLM.
    # Gemini free tier ~10 req/min: 7s => ~8,5/min, com folga. Sem isso, um lote de 10+
    # ativos estoura o limite e cai TODO no fallback (score 50). Baixe p/ 0 se tiver tier pago.
    LLM_PACING_SECONDS: float = field(default_factory=lambda: float(os.getenv("LLM_PACING_SECONDS", "7")))

    def __post_init__(self):
        # Trava de governança P0 (predictor_core.settings): chave ausente/FALSA/curta =>
        # crash imediato, antes de qualquer modelo inicializar. SerpAPI sempre obrigatória;
        # a de LLM depende do provedor. Strings de mentira ('dummy', etc.) também crasham.
        from predictor_core.settings import require_secrets
        provider_keys = {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
            "mistral": "MISTRAL_API_KEY",
        }
        provider_key = provider_keys.get(self.LLM_PROVIDER, "GEMINI_API_KEY")
        require_secrets("SERP_API_KEY", provider_key)


settings = Settings()
