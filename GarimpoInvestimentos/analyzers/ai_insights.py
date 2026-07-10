"""Análise via LLM, agnóstica de provedor (Gemini, OpenAI e OpenAI-compatíveis).

O provedor é escolhido em `settings.LLM_PROVIDER`. Clientes são construídos de forma
preguiçosa para não exigir a chave do provedor que não está em uso. Groq, Cerebras e
Mistral falam a API da OpenAI (só muda o base_url) — reutilizam o MESMO cliente/retry,
sem dependência nova.

⚠️ Para o backtesting ser válido, NÃO misture provedores na mesma janela de coleta —
um histórico meio-Gemini, meio-OpenAI mistura dois "juízes" com calibrações diferentes.
O carimbo judge_signature() muda com o provedor: trocar = trial NOVA no registry.
"""
import asyncio
import hashlib
import inspect
import json
import logging

from GarimpoInvestimentos.config import settings

_log = logging.getLogger("previsao_cripto.ai_insights")

_gemini_client = None
_openai_clients: dict = {}

# Provedores que falam a API da OpenAI: provider -> (base_url, attr da chave, attr do modelo).
# base_url None = api.openai.com (default do SDK).
_OPENAI_COMPAT = {
    "openai": (None, "OPENAI_API_KEY", "OPENAI_MODEL"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODEL"),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", "CEREBRAS_MODEL"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", "MISTRAL_MODEL"),
}


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


def _get_openai(provider: str = "openai"):
    if provider not in _openai_clients:
        from openai import OpenAI
        base_url, key_attr, _ = _OPENAI_COMPAT[provider]
        _openai_clients[provider] = OpenAI(
            api_key=getattr(settings, key_attr), base_url=base_url)
    return _openai_clients[provider]


def _build_prompt(asset_name: str, hard_data: dict, news_snippets: list[str]) -> str:
    horizon = settings.SCORE_HORIZON_DAYS
    return f"""
    Você é um analista quantitativo de criptoativos. Avalie {asset_name.upper()} para um
    horizonte de {horizon} dias — todas as estimativas devem se referir a esse prazo.

    • Dados de mercado e indicadores técnicos:
    {json.dumps(hard_data, indent=2, ensure_ascii=False)}

    • Notícias recentes (títulos):
    {json.dumps(news_snippets, indent=2, ensure_ascii=False)}

    Considere momentum (RSI), tendência (SMA 50/200, MACD) e volatilidade (Bollinger)
    quando presentes. Estime o retorno de preço esperado nos próximos {horizon} dias e
    devolva **somente um JSON válido**, sem texto adicional:

    {{
      "sentiment": "positivo" | "neutro" | "negativo",
      "summary": "justificativa objetiva em 1-3 frases",
      "opportunity_score": número 0-100 que mede o retorno esperado em {horizon} dias —
        0 = forte queda esperada, 50 = lateralização/incerteza, 100 = forte alta esperada
    }}
    """


# Hash do CÓDIGO do template (inspect), não do texto preenchido: muda sozinho
# quando o prompt muda, sem depender de bumpar uma constante na mão.
_PROMPT_HASH = hashlib.sha256(
    inspect.getsource(_build_prompt).encode("utf-8")).hexdigest()[:12]


def provider_for_asset(asset_name: str) -> str:
    """Provedor efetivo para um ativo. Em LLM_PROVIDER=multi, partição FIXA e
    determinística (sha256 do nome mod n): o mesmo ativo cai SEMPRE no mesmo
    provedor, em qualquer máquina/execução — a série por-ativo mantém um único
    juiz. Fora do modo multi, devolve o provedor global."""
    if settings.LLM_PROVIDER != "multi":
        return settings.LLM_PROVIDER
    providers = settings.LLM_MULTI_PROVIDERS
    digest = hashlib.sha256(asset_name.strip().lower().encode("utf-8")).digest()
    return providers[int.from_bytes(digest[:4], "big") % len(providers)]


def judge_signature(asset_name: str | None = None) -> str:
    """Carimbo do juiz para reprodutibilidade: 'provider:modelo:hash-do-prompt'.

    Modo B do framework: o LLM é o modelo, então PRECISA ser identificado. Sem este
    carimbo, um upgrade de modelo (gemini-2.5-flash -> próximo) ou um ajuste de prompt
    misturaria dois 'juízes' de calibrações diferentes no mesmo histórico — e o
    backtest os trataria como um só estimador, poolando o que não deveria.

    Em LLM_PROVIDER=multi o juiz é POR ATIVO (partição fixa) — passe asset_name;
    sem ele, o modo multi levanta ValueError em vez de carimbar um juiz errado.
    """
    provider = provider_for_asset(asset_name) if asset_name is not None else settings.LLM_PROVIDER
    if provider == "multi":
        raise ValueError("judge_signature() em modo multi exige asset_name")
    compat = _OPENAI_COMPAT.get(provider)
    model = getattr(settings, compat[2]) if compat else settings.GEMINI_MODEL
    return f"{provider}:{model}:{_PROMPT_HASH}"


_DAILY_QUOTA_MARKERS = ("perday", "per day", "requestsperday", "generaterequestsperday")


def _retry_delay_for_error(exc: Exception, attempt: int) -> float | None:
    """Segundos de espera antes de re-tentar um erro de LLM; None = desiste (não retry).

    Cota DIÁRIA (RPD) esgotada não vale re-tentar dentro do mesmo run — não vai liberar
    em segundos. Cota POR MINUTO e 5xx são transitórios e valem retry com backoff.

    Gemini (google.genai.errors.ClientError) devolve o MESMO status 429/"RESOURCE_EXHAUSTED"
    tanto para limite por minuto quanto por dia — o status sozinho NÃO distingue os dois
    casos. A distinção só existe no texto (quotaId contém "PerDay" apenas no caso diário;
    esse texto acaba embutido em str(exc) via exc.details). Por isso a checagem de cota
    diária usa SÓ o texto, nunca o status — caso contrário todo 429 do Gemini (inclusive os
    transitórios por minuto) seria tratado como não-retryable, e o retry nunca dispararia.
    """
    message = str(exc).lower()
    if any(marker in message for marker in _DAILY_QUOTA_MARKERS):
        return None

    # Gemini expõe o status HTTP em `.code` (int); OpenAI em `.status_code` (int).
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status in {429, 500, 502, 503, 504}:
        pass
    elif isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        pass
    else:
        try:
            import httpx
            if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
                pass
            else:
                return None
        except Exception:
            return None

    # 1) Retry-After em headers HTTP — caminho da OpenAI (exc.response é httpx.Response).
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        retry_after = headers.get("retry-after") or headers.get("Retry-After")
        if retry_after is not None:
            try:
                return float(retry_after)
            except (TypeError, ValueError):
                pass

    # 2) RetryInfo embutido no corpo do erro — caminho do Gemini. `exc.details` é o corpo
    #    JSON inteiro (ex.: {"error": {"details": [...]}}); a lista de itens (RetryInfo,
    #    QuotaFailure, Help) mora em details["error"]["details"] quando vem "embrulhada"
    #    no envelope padrão da Google API, ou em details["details"] se já vier desembrulhada.
    body = getattr(exc, "details", None)
    if isinstance(body, dict):
        items = body.get("details") or body.get("error", {}).get("details") or []
        for item in items:
            if isinstance(item, dict) and "RetryInfo" in str(item.get("@type", "")):
                retry_delay = item.get("retryDelay")
                # max(0.0, ...): um retryDelay negativo (nunca visto na API real, mas o
                # servidor não é uma fonte confiável) não deve virar "retry instantâneo
                # sem backoff" — sobretudo com LLM_PACING_SECONDS=0 (tier pago), onde o
                # max(base_delay, delay) em _run_with_llm_retry deixaria de mascarar isso.
                if isinstance(retry_delay, (int, float)):
                    return max(0.0, float(retry_delay))
                if isinstance(retry_delay, str):
                    value = retry_delay.strip().lower()
                    if value.endswith("s"):
                        try:
                            return max(0.0, float(value[:-1]))
                        except ValueError:
                            pass
                    elif value.endswith("m"):
                        try:
                            return max(0.0, float(value[:-1]) * 60.0)
                        except ValueError:
                            pass
                break

    return min(2.0 * attempt, 30.0)


async def _run_with_llm_retry(callable_obj) -> str:
    base_delay = max(float(settings.LLM_PACING_SECONDS), 0.0)
    for attempt in range(1, 5):
        try:
            return await callable_obj()
        except Exception as exc:
            delay = _retry_delay_for_error(exc, attempt)
            if attempt >= 4 or delay is None:
                raise
            sleep_for = max(base_delay, delay)
            _log.warning("llm retry %d/4 after %s (sleep %.1fs)", attempt, type(exc).__name__, sleep_for)
            await asyncio.sleep(sleep_for)
    raise RuntimeError("llm retry loop exhausted")


async def _call_gemini(prompt: str) -> str:
    from google.genai import types
    client = _get_gemini()

    async def _invoke() -> str:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json"),
        )
        return response.text

    return await _run_with_llm_retry(_invoke)


async def _call_openai(prompt: str, provider: str = "openai") -> str:
    client = _get_openai(provider)
    model = getattr(settings, _OPENAI_COMPAT[provider][2])

    async def _invoke() -> str:
        response = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
        )
        return response.choices[0].message.content

    return await _run_with_llm_retry(_invoke)


async def analyze_asset(asset_name: str, hard_data: dict, news_snippets: list[str]):
    prompt = _build_prompt(asset_name, hard_data, news_snippets)
    try:
        provider = provider_for_asset(asset_name)
        if provider in _OPENAI_COMPAT:
            text = await _call_openai(prompt, provider)
        else:
            text = await _call_gemini(prompt)

        text = text.strip()
        if "{" in text and "}" in text:
            text = text[text.find("{") : text.rfind("}") + 1]
        data = json.loads(text)

        return {
            "sentiment": data.get("sentiment", "neutro"),
            "summary": data.get("summary", "sem resumo disponível"),
            "opportunity_score": data.get("opportunity_score", 50),
            "llm_fallback": False,
        }

    except Exception as e:
        _log.warning("erro ao analisar %s (%s: %s) — fallback aplicado",
                     asset_name, type(e).__name__, e)
        # llm_fallback=True é o carimbo ESTRUTURAL (migração 0009): o backtest
        # exclui por ele, não pela string do summary (que segue por compat/legado).
        return {
            "sentiment": "neutro",
            "summary": "erro na análise (fallback aplicado)",
            "opportunity_score": 50,
            "llm_fallback": True,
        }


# Compat: código antigo importava analyze_with_gemini.
analyze_with_gemini = analyze_asset
