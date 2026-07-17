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
    OPENROUTER_API_KEY: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    # OpenRouter é RESERVA (não está na partição da H5 — mudar partição = trial
    # nova). Modelos :free rotacionam e congestionam (429) — smoke test antes de usar.
    OPENROUTER_MODEL: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"))
    # LLM_PROVIDER=multi: particiona os ativos entre estes provedores (partição FIXA
    # e determinística por sha256 do nome — cada ativo tem SEMPRE o mesmo juiz, para
    # a série por-ativo ser consistente). Divide a carga: 22 ativos / 4 ≈ 5-6
    # chamadas/dia por provedor, dentro de todos os free tiers.
    LLM_MULTI_PROVIDERS: list[str] = field(default_factory=lambda: [
        p.strip().lower() for p in os.getenv(
            "LLM_MULTI_PROVIDERS", "gemini,groq,cerebras,mistral").split(",") if p.strip()])

    # --- Notícias ---
    SERP_API_KEY: str = field(default_factory=lambda: os.getenv("SERP_API_KEY", ""))
    # O padrão preserva H5. Outra composição de fontes altera o input do LLM e
    # deve ser ativada somente em uma nova trial forward.
    NEWS_PROVIDERS: list[str] = field(default_factory=lambda: [
        p.strip().lower() for p in os.getenv("NEWS_PROVIDERS", "serpapi").split(",") if p.strip()])
    # Vazio preserva o roteamento historico. Quando preenchido, esta fonte e
    # consultada somente depois de todas as fontes primarias distribuidas.
    NEWS_FALLBACK_PROVIDER: str = field(default_factory=lambda: os.getenv(
        "NEWS_FALLBACK_PROVIDER", "").strip().lower())
    CRYPTOPANIC_AUTH_TOKEN: str = field(default_factory=lambda: os.getenv("CRYPTOPANIC_AUTH_TOKEN", ""))
    # Credenciais opcionais: os adaptadores permanecem desativados ate serem
    # incluidos explicitamente em NEWS_PROVIDERS de uma nova trial forward.
    NEWSAPIAI_API_KEY: str = field(default_factory=lambda: os.getenv(
        "NEWSAPIAI_API_KEY", os.getenv("NEWSAPI_AI_API_KEY", "")))
    MEDIASTACK_API_KEY: str = field(default_factory=lambda: os.getenv("MEDIASTACK_API_KEY", ""))

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
    # Prefiltro OPT-IN: reduz chamadas de LLM usando apenas features já
    # materializadas. Ligá-lo altera a população observada e exige nova trial.
    LLM_PREFILTER_ENABLED: bool = field(default_factory=lambda: parse_bool(
        os.getenv("LLM_PREFILTER_ENABLED"), False))
    LLM_PREFILTER_MIN_VOLUME_USD: float = field(default_factory=lambda: float(
        os.getenv("LLM_PREFILTER_MIN_VOLUME_USD", "10000000")))
    LLM_PREFILTER_MIN_ABS_CHANGE_7D: float = field(default_factory=lambda: float(
        os.getenv("LLM_PREFILTER_MIN_ABS_CHANGE_7D", "2")))
    # Guardas de requisição da Fase 1. Zero = sem teto; habilitar qualquer teto
    # muda a coleta e requer trial nova. Os contadores vivem só no processo atual.
    API_GUARD_ENABLED: bool = field(default_factory=lambda: parse_bool(
        os.getenv("API_GUARD_ENABLED"), False))
    API_GUARD_MAX_INGEST_ASSETS: int = field(default_factory=lambda: int(
        os.getenv("API_GUARD_MAX_INGEST_ASSETS", "0")))
    API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER: int = field(default_factory=lambda: int(
        os.getenv("API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER", "0")))
    API_GUARD_MAX_LLM_CALLS_PER_PROVIDER: int = field(default_factory=lambda: int(
        os.getenv("API_GUARD_MAX_LLM_CALLS_PER_PROVIDER", "0")))

    def __post_init__(self):
        # Trava de governança P0 (predictor_core.settings): chave ausente/FALSA/curta =>
        # crash imediato, antes de qualquer modelo inicializar. SerpAPI só é obrigatória
        # quando configurada; RSS não exige credencial. Strings de mentira ('dummy', etc.)
        # também crasham.
        from predictor_core.settings import require_secrets
        allowed_news = {
            "serpapi", "cryptopanic", "newsapi_ai", "mediastack",
            "google_news_rss", "curated_rss",
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
        for name in ("API_GUARD_MAX_INGEST_ASSETS", "API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER",
                     "API_GUARD_MAX_LLM_CALLS_PER_PROVIDER"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} não pode ser negativo")
        if self.LLM_PREFILTER_MIN_VOLUME_USD < 0 or self.LLM_PREFILTER_MIN_ABS_CHANGE_7D < 0:
            raise ValueError("limites do LLM prefilter não podem ser negativos")
        provider_keys = {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        uses_serpapi = "serpapi" in self.NEWS_PROVIDERS or self.NEWS_FALLBACK_PROVIDER == "serpapi"
        required_news = ["SERP_API_KEY"] if uses_serpapi else []
        if self.LLM_PROVIDER == "multi":
            # Modo multi exige a chave de TODOS os provedores da partição — falhar
            # na primeira chamada do lote seria degradação silenciosa (fallback 50).
            required = [provider_keys.get(p, "GEMINI_API_KEY") for p in self.LLM_MULTI_PROVIDERS]
            require_secrets(*required_news, *required)
        else:
            provider_key = provider_keys.get(self.LLM_PROVIDER, "GEMINI_API_KEY")
            require_secrets(*required_news, provider_key)


settings = Settings()
