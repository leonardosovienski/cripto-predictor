"""Retry com exponential backoff para chamadas de rede transitórias.

Aplicado às chamadas de CoinGecko, SerpAPI e LLM. Objetivo: um `503`/`429` transitório
não deve virar fallback (que envenena o histórico). Erros NÃO-transitórios (404, chave
inválida, cota DIÁRIA esgotada) não são reententados — retry não os resolve.

Nota: o retry de transporte embutido do httpx só cobre erros de conexão, não status HTTP
como 429/503 — por isso o retry vive aqui, no nível da chamada.
"""
import asyncio
import functools
import random

# Status HTTP transitórios que valem retry.
TRANSIENT_STATUS = {429, 500, 502, 503, 504}
# Marcadores de erro transitório em SDKs (Gemini/OpenAI) que não expõem status limpo.
TRANSIENT_MARKERS = (
    "unavailable", "overloaded", "high demand", "rate limit",
    "temporarily", "timeout", "try again", "resource_exhausted",
)
# Cota DIÁRIA/por projeto: retry não ajuda (espere o reset). Não reententar.
DAILY_QUOTA_MARKERS = ("per day", "perday", "requests per day", "generaterequestsperday")


def _status_of(exc) -> int | None:
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(code, int):
        return code
    resp = getattr(exc, "response", None)
    if resp is not None and isinstance(getattr(resp, "status_code", None), int):
        return resp.status_code
    return None


def is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    if any(m in msg for m in DAILY_QUOTA_MARKERS):
        return False  # cota diária — retry só desperdiça tempo
    if _status_of(exc) in TRANSIENT_STATUS:
        return True
    try:
        import httpx
        if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
            return True
    except Exception:
        pass
    return any(m in msg for m in TRANSIENT_MARKERS)


def with_retry(attempts: int = 4, base_delay: float = 2.0, max_delay: float = 30.0):
    """Decorator para corotinas: reexecuta em erro transitório com backoff exponencial + jitter."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == attempts or not is_transient(exc):
                        raise
                    sleep = min(delay, max_delay) + random.uniform(0, 1)
                    print(f"⏳ {fn.__name__}: transitório ({type(exc).__name__}); "
                          f"tentativa {attempt}/{attempts - 1}, aguardando {sleep:.1f}s")
                    await asyncio.sleep(sleep)
                    delay *= 2
        return wrapper
    return decorator
