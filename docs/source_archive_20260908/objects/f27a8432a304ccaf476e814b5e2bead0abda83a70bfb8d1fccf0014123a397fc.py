"""Identidade canônica da política que selecionou uma previsão."""

import json

from GarimpoInvestimentos.config import settings


def current_policy() -> dict:
    """Somente escolhas que afetam a população ou o input do LLM."""
    return {
        "api_guard": {
            "enabled": settings.API_GUARD_ENABLED,
            "max_ingest_assets": settings.API_GUARD_MAX_INGEST_ASSETS,
            "max_llm_calls_per_provider": settings.API_GUARD_MAX_LLM_CALLS_PER_PROVIDER,
            "max_news_attempts_per_provider": settings.API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER,
        },
        "llm_prefilter": {
            "enabled": settings.LLM_PREFILTER_ENABLED,
            "min_abs_change_7d": settings.LLM_PREFILTER_MIN_ABS_CHANGE_7D,
            "min_volume_usd": settings.LLM_PREFILTER_MIN_VOLUME_USD,
        },
        "news_fallback_provider": settings.NEWS_FALLBACK_PROVIDER or None,
        "news_providers": settings.NEWS_PROVIDERS,
    }


def current_policy_json() -> str:
    return json.dumps(current_policy(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
