import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.paths import OUTPUT_DIR

CACHE_PATH = str(OUTPUT_DIR / "cache.json")
TTL_HOURS = settings.CACHE_TTL_HOURS


def load_cache() -> Dict[str, Any]:
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}

    now = datetime.now(timezone.utc)
    valid = {}
    for key, entry in raw.items():
        cached_at_str = entry.get("cached_at")
        if not cached_at_str:
            continue
        try:
            cached_at = datetime.fromisoformat(cached_at_str)
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)
            if now - cached_at < timedelta(hours=TTL_HOURS):
                valid[key] = entry
        except Exception:
            continue
    return valid


def save_cache(cache: Dict[str, Any]) -> None:
    now_utc = datetime.now(timezone.utc).isoformat()
    for entry in cache.values():
        # setdefault preserva o timestamp da análise original; só carimba entradas novas.
        # Sem isso, reexecuções renovavam o TTL para sempre e serviam análise velha.
        entry.setdefault("cached_at", now_utc)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
