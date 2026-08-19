"""Regressão: `require_secrets` deve validar os valores JÁ RESOLVIDOS de `Settings`
(vindos de .env, env var real do processo, ou init kwarg), não o `os.environ`
cru — que pode estar vazio mesmo com um `.env` correto e completo.

Bug real reproduzido em produção (auditoria 2026-08-19): `.env` no local
documentado (`GarimpoInvestimentos/.env`), com `GEMINI_API_KEY`/`SERP_API_KEY`
válidas (>=16 chars, sem placeholder), mas o processo Python nunca exportava
essas chaves para `os.environ` — só ficavam nos campos já resolvidos de
`Settings`. `require_secrets(*names)` (default `env=None`) olhava só para
`os.environ`, via `MissingCredentialsError`, mesmo com tudo certo.
"""

import pytest
from predictor_core.kernel.settings import MissingCredentialsError

from GarimpoInvestimentos.config import Settings


def test_chave_resolvida_via_init_kwarg_e_aceita_mesmo_ausente_de_os_environ(monkeypatch):
    # Simula o cenário real: a chave existe no .env (aqui, via init kwarg, que
    # tem a mesma prioridade de resolução de campo que o .env teria) mas NUNCA
    # foi exportada como variável de ambiente do processo.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SERP_API_KEY", raising=False)
    settings = Settings(
        GEMINI_API_KEY="unit-test-key-vinda-do-dotenv",
        SERP_API_KEY="unit-test-outra-key-vinda-do-dotenv",
    )
    assert settings.GEMINI_API_KEY == "unit-test-key-vinda-do-dotenv"
    assert settings.SERP_API_KEY == "unit-test-outra-key-vinda-do-dotenv"


def test_chave_realmente_ausente_ainda_e_rejeitada(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SERP_API_KEY", raising=False)
    with pytest.raises(MissingCredentialsError, match="GEMINI_API_KEY"):
        Settings(GEMINI_API_KEY="", SERP_API_KEY="unit-test-chave-valida-bem-longa")


def test_chave_com_placeholder_ainda_e_rejeitada_mesmo_resolvida(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SERP_API_KEY", raising=False)
    with pytest.raises(MissingCredentialsError, match="SERP_API_KEY"):
        Settings(GEMINI_API_KEY="unit-test-chave-valida-bem-longa", SERP_API_KEY="changeme")


def test_modo_multi_valida_todas_as_chaves_dos_providers_resolvidos(monkeypatch):
    for name in (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "MISTRAL_API_KEY",
        "SERP_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(MissingCredentialsError, match="GROQ_API_KEY"):
        Settings(
            LLM_PROVIDER="multi",
            GEMINI_API_KEY="unit-test-key-valida-bem-longa",
            GROQ_API_KEY="",  # faltando de propósito
            CEREBRAS_API_KEY="unit-test-key-valida-bem-longa",
            MISTRAL_API_KEY="unit-test-key-valida-bem-longa",
            SERP_API_KEY="unit-test-key-valida-bem-longa",
        )

    settings = Settings(
        LLM_PROVIDER="multi",
        GEMINI_API_KEY="unit-test-key-valida-bem-longa",
        GROQ_API_KEY="unit-test-key-valida-bem-longa",
        CEREBRAS_API_KEY="unit-test-key-valida-bem-longa",
        MISTRAL_API_KEY="unit-test-key-valida-bem-longa",
        SERP_API_KEY="unit-test-key-valida-bem-longa",
    )
    assert settings.LLM_PROVIDER == "multi"
