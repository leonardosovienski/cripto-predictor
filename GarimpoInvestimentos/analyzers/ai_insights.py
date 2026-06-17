"""Análise via LLM, agnóstica de provedor (Gemini ou OpenAI).

O provedor é escolhido em `settings.LLM_PROVIDER`. Clientes são construídos de forma
preguiçosa para não exigir a chave do provedor que não está em uso.

⚠️ Para o backtesting ser válido, NÃO misture provedores na mesma janela de coleta —
um histórico meio-Gemini, meio-OpenAI mistura dois "juízes" com calibrações diferentes.
"""
import asyncio
import hashlib
import inspect
import json

from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core.retry import with_retry

_gemini_client = None
_openai_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


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


def judge_signature() -> str:
    """Carimbo do juiz para reprodutibilidade: 'provider:modelo:hash-do-prompt'.

    Modo B do framework: o LLM é o modelo, então PRECISA ser identificado. Sem este
    carimbo, um upgrade de modelo (gemini-2.5-flash -> próximo) ou um ajuste de prompt
    misturaria dois 'juízes' de calibrações diferentes no mesmo histórico — e o
    backtest os trataria como um só estimador, poolando o que não deveria.
    """
    model = settings.OPENAI_MODEL if settings.LLM_PROVIDER == "openai" else settings.GEMINI_MODEL
    return f"{settings.LLM_PROVIDER}:{model}:{_PROMPT_HASH}"


@with_retry()
async def _call_gemini(prompt: str) -> str:
    from google.genai import types
    client = _get_gemini()
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json"),
    )
    return response.text


@with_retry()
async def _call_openai(prompt: str) -> str:
    client = _get_openai()
    response = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    )
    return response.choices[0].message.content


async def analyze_asset(asset_name: str, hard_data: dict, news_snippets: list[str]):
    prompt = _build_prompt(asset_name, hard_data, news_snippets)
    try:
        if settings.LLM_PROVIDER == "openai":
            text = await _call_openai(prompt)
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
        }

    except Exception as e:
        print(f"⚠️ Erro ao analisar {asset_name}: {e}")
        return {
            "sentiment": "neutro",
            "summary": "erro na análise (fallback aplicado)",
            "opportunity_score": 50,
        }


# Compat: código antigo importava analyze_with_gemini.
analyze_with_gemini = analyze_asset
