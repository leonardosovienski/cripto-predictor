def calculate_final_score(analysis: dict) -> float:
    """Score final = o `opportunity_score` do modelo (0-100), apenas validado/limitado.

    O sentimento NÃO entra mais no cálculo (era dupla contagem: o modelo já reflete o
    cenário no próprio opportunity_score). Ele permanece em `analysis["sentiment"]`
    como metadado de exibição/filtro.
    """
    score = analysis.get("opportunity_score", 50)
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 50.0
    return round(min(max(score, 0), 100), 2)


# --- Cross-check determinístico (Opção 1: SÓ SINALIZAR) ---------------------
# "Medir antes de modelar": o motor técnico NÃO altera o score do LLM. Ele só
# detecta CONTRADIÇÃO direta (LLM otimista enquanto tendência+momentum apontam pra
# baixo, ou vice-versa) e tagueia a linha. O pedágio do bootstrap depois estratifica
# e prova se as linhas tagueadas perdem alpha — sem hiperparâmetro arbitrário mutando
# o sinal original.

def technical_direction(indicadores: dict) -> str | None:
    """'bull' | 'bear' | 'neutral' a partir de tendência (SMA200), momentum (MACD) e
    sobrecompra/sobrevenda (RSI). None se não há indicador suficiente para opinar."""
    if not indicadores:
        return None
    has_trend = "preco_vs_sma200_pct" in indicadores
    has_mom = "macd_histogram" in indicadores
    if not (has_trend or has_mom):
        return None
    votes = 0
    if has_trend:
        votes += 1 if indicadores["preco_vs_sma200_pct"] > 0 else -1
    if has_mom:
        votes += 1 if indicadores["macd_histogram"] > 0 else -1
    rsi = indicadores.get("rsi_14")
    if rsi is not None:
        if rsi > 70:
            votes -= 1
        elif rsi < 30:
            votes += 1
    if votes > 0:
        return "bull"
    if votes < 0:
        return "bear"
    return "neutral"


def llm_direction(score: float, hi: float = 60.0, lo: float = 40.0) -> str:
    """Direção implícita no opportunity_score do LLM (0-100, 50=neutro)."""
    if score >= hi:
        return "bull"
    if score <= lo:
        return "bear"
    return "neutral"


def divergence_flag(llm_score: float, indicadores: dict) -> int:
    """1 se o LLM CONTRADIZ diretamente o técnico (bull vs bear), senão 0.

    SÓ sinaliza — não muta o score. Sem direção técnica (indicador insuficiente) => 0.
    """
    td = technical_direction(indicadores)
    if td is None or td == "neutral":
        return 0
    ld = llm_direction(llm_score)
    return int((ld == "bull" and td == "bear") or (ld == "bear" and td == "bull"))
