import hashlib
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from predictor_core.obs import emit_event

from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.paths import OUTPUT_DIR
from GarimpoInvestimentos.durable_io import atomic_write, file_lock, strict_json_loads

logger = logging.getLogger(__name__)

CACHE_PATH = str(OUTPUT_DIR / "cache.json")
TTL_HOURS = settings.CACHE_TTL_HOURS
_DOMAIN = "previsao_cripto"


def analysis_fingerprint(market_data: dict, judge: str, source: str, policy: str) -> str:
    """Cache identity includes public inputs and the current analysis configuration."""
    payload = json.dumps(
        {"market": market_data, "judge": judge, "source": source, "policy": policy},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    if not isinstance(raw, dict):
        logger.warning("cache has invalid root type — treating as empty")
        return {}
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        cached_at_str = entry.get("cached_at")
        if not cached_at_str:
            continue
        try:
            cached_at = datetime.fromisoformat(cached_at_str)
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=UTC)
            if timedelta(0) <= now - cached_at < timedelta(hours=TTL_HOURS):
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
    path = Path(CACHE_PATH)
    with file_lock(path):
        if path.exists():
            original = strict_json_loads(path.read_text(encoding="utf-8"))
            if not isinstance(original, dict):
                raise ValueError("invalid cache root; preserve before recovery")
        # Merge concurrent writes under the lock. Expired entries are ephemeral.
        merged = load_cache()
        now_utc = datetime.now(UTC).isoformat()
        for key, entry in cache.items():
            if not isinstance(entry, dict):
                raise ValueError("invalid cache entry")
            merged[key] = {"cached_at": now_utc, **entry}
        atomic_write(
            path,
            (json.dumps(merged, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode(
                "utf-8"
            ),
        )
