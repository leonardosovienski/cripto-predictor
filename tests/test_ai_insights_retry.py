"""Testes do retry/backoff de LLM (_retry_delay_for_error, _run_with_llm_retry).

Sem cobertura antes: a lógica original (adicionada num PR do Copilot) tinha um bug real
não pego por nenhum teste — todo erro 429 do Gemini (cota diária OU por minuto) era
tratado como não-retryable, porque `exc.code` é SEMPRE 429 para os dois casos e a
checagem usava `status in {429, 403}` como atalho que anulava a distinção por texto.
Estes testes fixam o contrato correto: só cota DIÁRIA desiste; cota por minuto e 5xx
retentam com o delay do RetryInfo (Gemini) ou do header Retry-After (OpenAI).
"""
import asyncio

import pytest

from GarimpoInvestimentos.analyzers.ai_insights import (
    _retry_delay_for_error,
    _run_with_llm_retry,
)


class _FakeGeminiError(Exception):
    """Espelha a forma real de google.genai.errors.ClientError: .code (int) e .status
    (string) sempre presentes, .details = corpo JSON inteiro {"error": {...}}."""

    def __init__(self, quota_id: str, retry_delay: str | None = None):
        self.code = 429
        self.status = "RESOURCE_EXHAUSTED"
        details_items = [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                          "violations": [{"quotaId": quota_id}]}]
        if retry_delay:
            details_items.append({"@type": "type.googleapis.com/google.rpc.RetryInfo",
                                   "retryDelay": retry_delay})
        self.details = {"error": {"code": 429, "status": self.status,
                                   "message": f"Quota exceeded for {quota_id}",
                                   "details": details_items}}
        super().__init__(f"{self.code} {self.status}. {self.details}")


class _FakeOpenAIError(Exception):
    """Espelha openai.APIStatusError: .status_code (int) e .response.headers."""

    def __init__(self, status_code: int, retry_after: str | None = None):
        self.status_code = status_code

        class _Resp:
            headers = {"retry-after": retry_after} if retry_after else {}

        self.response = _Resp()
        super().__init__(f"{status_code} error")


def test_gemini_daily_quota_gives_up_no_retry():
    exc = _FakeGeminiError("GenerateRequestsPerDayPerProjectPerModel-FreeTier", retry_delay="44s")
    assert _retry_delay_for_error(exc, attempt=1) is None


def test_gemini_per_minute_quota_retries_with_retryinfo_delay():
    """Regressão do bug real: .code=429 é IGUAL para cota diária e por minuto — só o
    texto do quotaId distingue. Antes da correção, este caso retornava None (bug)."""
    exc = _FakeGeminiError("GenerateRequestsPerMinutePerProjectPerModel-FreeTier", retry_delay="12s")
    assert _retry_delay_for_error(exc, attempt=1) == 12.0


def test_gemini_transient_error_without_retryinfo_falls_back_to_backoff():
    exc = _FakeGeminiError("GenerateRequestsPerMinutePerProjectPerModel-FreeTier")
    delay = _retry_delay_for_error(exc, attempt=2)
    assert delay == pytest.approx(4.0)  # 2.0 * attempt, sem RetryInfo


def test_openai_rate_limit_uses_retry_after_header():
    exc = _FakeOpenAIError(429, retry_after="5")
    assert _retry_delay_for_error(exc, attempt=1) == 5.0


def test_non_transient_error_no_retry():
    exc = _FakeOpenAIError(400)  # bad request — nunca deve reentrar
    assert _retry_delay_for_error(exc, attempt=1) is None


def test_run_with_llm_retry_recovers_after_transient_errors(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", _instant_sleep)
    attempts = {"n": 0}

    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise _FakeGeminiError("GenerateRequestsPerMinutePerProjectPerModel-FreeTier",
                                    retry_delay="0.01s")
        return "ok"

    result = asyncio.run(_run_with_llm_retry(flaky))
    assert result == "ok"
    assert attempts["n"] == 3


def test_run_with_llm_retry_gives_up_immediately_on_daily_quota(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", _instant_sleep)
    attempts = {"n": 0}

    async def always_daily_quota():
        attempts["n"] += 1
        raise _FakeGeminiError("GenerateRequestsPerDayPerProjectPerModel-FreeTier")

    with pytest.raises(_FakeGeminiError):
        asyncio.run(_run_with_llm_retry(always_daily_quota))
    assert attempts["n"] == 1  # desistiu na primeira, não gastou as 4 tentativas


async def _instant_sleep(_seconds):
    return None
