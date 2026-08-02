import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from predictor_core.obs import emit_event

from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.paths import OUTPUT_DIR

logger = logging.getLogger(__name__)

CACHE_PATH = str(OUTPUT_DIR / "cache.json")
TTL_HOURS = settings.CACHE_TTL_HOURS
_DOMAIN = "previsao_cripto"


def load_cache() -> dict[str, Any]:
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("cache ilegível em %s (%s) — tratando como vazio", CACHE_PATH, exc)
        emit_event(
            _DOMAIN,
            "cache_integrity",
            metrics={},
            metadata={
                "path": CACHE_PATH,
                "error_type": type(exc).__name__,
                "error_msg": str(exc)[:200],
                "action": "treated_as_empty",
            },
        )
        return {}

    now = datetime.now(UTC)
    valid = {}
    for key, entry in raw.items():
        cached_at_str = entry.get("cached_at")
        if not cached_at_str:
            continue
        try:
            cached_at = datetime.fromisoformat(cached_at_str)
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=UTC)
            if now - cached_at < timedelta(hours=TTL_HOURS):
                valid[key] = entry
        except (ValueError, TypeError) as exc:
            # timestamp malformado nesta entrada: descarta só ela, mas registra —
            # entrada corrompida silenciosa esconde bug de quem escreveu o cache.
            logger.warning("entrada de cache %r com cached_at invalido (%s) — ignorada", key, exc)
            emit_event(
                _DOMAIN,
                "cache_integrity",
                metrics={},
                metadata={
                    "key": key,
                    "error_type": type(exc).__name__,
                    "action": "entry_discarded",
                },
            )
            continue
    return valid


def save_cache(cache: dict[str, Any]) -> None:
    now_utc = datetime.now(UTC).isoformat()
    for entry in cache.values():
        # setdefault preserva o timestamp da análise original; só carimba entradas novas.
        # Sem isso, reexecuções renovavam o TTL para sempre e serviam análise velha.
        entry.setdefault("cached_at", now_utc)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
