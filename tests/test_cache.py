"""Testes de cache.py — TTL, UTC, setdefault, cache corrompido.

Todos os testes rodam sem rede e sem .env real (conftest injeta credenciais mínimas).
"""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import GarimpoInvestimentos.store.cache as cache_mod


def _write_cache(path: str, entries: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ts(dt: datetime) -> str:
    return dt.isoformat()


# ------------------------------------------------------------------ #
# Testes                                                              #
# ------------------------------------------------------------------ #

def test_load_cache_empty_when_file_missing():
    """Sem arquivo de cache → retorna dict vazio sem exception."""
    with tempfile.TemporaryDirectory() as tmpdir:
        missing = os.path.join(tmpdir, "nonexistent.json")
        with patch.object(cache_mod, "CACHE_PATH", missing):
            result = cache_mod.load_cache()
    assert result == {}


def test_load_cache_valid_entry_within_ttl():
    """Entrada com cached_at recente deve ser retornada."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "cache.json")
        recent = _ts(_now_utc() - timedelta(minutes=30))
        _write_cache(path, {"bitcoin": {"score": 75, "cached_at": recent}})
        with patch.object(cache_mod, "CACHE_PATH", path), \
             patch.object(cache_mod, "TTL_HOURS", 6):
            result = cache_mod.load_cache()
    assert "bitcoin" in result
    assert result["bitcoin"]["score"] == 75


def test_load_cache_expired_entry_excluded():
    """Entrada com cached_at expirado (>TTL) não deve ser retornada."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "cache.json")
        old = _ts(_now_utc() - timedelta(hours=8))
        _write_cache(path, {"ethereum": {"score": 60, "cached_at": old}})
        with patch.object(cache_mod, "CACHE_PATH", path), \
             patch.object(cache_mod, "TTL_HOURS", 6):
            result = cache_mod.load_cache()
    assert "ethereum" not in result


def test_load_cache_entry_without_cached_at_excluded():
    """Entrada sem campo cached_at deve ser descartada silenciosamente."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "cache.json")
        _write_cache(path, {"solana": {"score": 55}})
        with patch.object(cache_mod, "CACHE_PATH", path):
            result = cache_mod.load_cache()
    assert "solana" not in result


def test_load_cache_corrupted_json_returns_empty():
    """JSON corrompido → retorna dict vazio sem exception (degradação graciosa)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "cache.json")
        with open(path, "w") as f:
            f.write("{invalid json{{")
        with patch.object(cache_mod, "CACHE_PATH", path):
            result = cache_mod.load_cache()
    assert result == {}


def test_save_cache_stamps_new_entries():
    """save_cache deve carimbar cached_at em entradas novas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "cache.json")
        cache = {"bitcoin": {"score": 80}}
        with patch.object(cache_mod, "CACHE_PATH", path):
            cache_mod.save_cache(cache)
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
    assert "cached_at" in saved["bitcoin"]


def test_save_cache_setdefault_preserves_original_timestamp():
    """save_cache não deve sobrescrever cached_at de entradas já carimbadas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "cache.json")
        original_ts = _ts(_now_utc() - timedelta(hours=1))
        cache = {"bitcoin": {"score": 70, "cached_at": original_ts}}
        with patch.object(cache_mod, "CACHE_PATH", path):
            cache_mod.save_cache(cache)
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
    assert saved["bitcoin"]["cached_at"] == original_ts


def test_load_cache_malformed_cached_at_excluded():
    """Entrada com cached_at malformado descartada; entradas válidas preservadas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "cache.json")
        good_ts = _ts(_now_utc() - timedelta(minutes=10))
        _write_cache(path, {
            "bitcoin": {"score": 70, "cached_at": good_ts},
            "broken": {"score": 50, "cached_at": "not-a-date"},
        })
        with patch.object(cache_mod, "CACHE_PATH", path), \
             patch.object(cache_mod, "TTL_HOURS", 6):
            result = cache_mod.load_cache()
    assert "bitcoin" in result
    assert "broken" not in result
