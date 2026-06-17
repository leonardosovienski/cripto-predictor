"""Trava P0 de credenciais (predictor_core.settings) — caminho stdlib (sem pydantic),
que é exatamente o fallback universal. O crash imediato em chave falsa/ausente."""
import pytest

from predictor_core.settings import is_fake_secret, require_secrets, MissingCredentialsError


def test_is_fake_secret_detects_junk():
    assert is_fake_secret("")
    assert is_fake_secret("   ")
    assert is_fake_secret("dummy")
    assert is_fake_secret("CHANGEME")          # case-insensitive
    assert is_fake_secret("short")             # < 16 chars
    assert not is_fake_secret("AIzaSyA-uma-chave-de-verdade-123")


def test_require_secrets_passes_for_valid(monkeypatch):
    monkeypatch.setenv("K1", "uma-chave-valida-0123456789")
    assert require_secrets("K1") == {"K1": "uma-chave-valida-0123456789"}


def test_require_secrets_crashes_on_missing(monkeypatch):
    monkeypatch.delenv("SUMIU", raising=False)
    with pytest.raises(MissingCredentialsError):
        require_secrets("SUMIU")


def test_require_secrets_crashes_on_fake(monkeypatch):
    monkeypatch.setenv("K2", "dummy")
    with pytest.raises(MissingCredentialsError):
        require_secrets("K2")


def test_require_secrets_lists_all_offenders(monkeypatch):
    monkeypatch.setenv("OK", "uma-chave-valida-0123456789")
    monkeypatch.setenv("RUIM", "x")
    monkeypatch.delenv("AUSENTE", raising=False)
    with pytest.raises(MissingCredentialsError) as ei:
        require_secrets("OK", "RUIM", "AUSENTE")
    msg = str(ei.value)
    assert "RUIM" in msg and "AUSENTE" in msg and "OK" not in msg