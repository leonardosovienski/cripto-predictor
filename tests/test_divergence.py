"""Cross-check flag-only (Opção 1) — tagueia contradição LLM-vs-técnico, NÃO muta score.

Tudo em score_engine, que é puro (sem settings/rede) — roda sem .env.
"""
from GarimpoInvestimentos.analyzers.score_engine import (
    technical_direction,
    llm_direction,
    divergence_flag,
    calculate_final_score,
)


def test_technical_direction_bull():
    assert technical_direction({"preco_vs_sma200_pct": 5.0, "macd_histogram": 0.2}) == "bull"


def test_technical_direction_bear():
    assert technical_direction({"preco_vs_sma200_pct": -5.0, "macd_histogram": -0.2}) == "bear"


def test_technical_direction_none_without_trend_or_momentum():
    assert technical_direction({}) is None
    assert technical_direction({"rsi_14": 50}) is None  # só RSI não basta para opinar


def test_technical_direction_rsi_overbought_offsets_weak_trend():
    # trend +1 e RSI sobrecomprado -1 => empata em neutral
    assert technical_direction({"preco_vs_sma200_pct": 1.0, "rsi_14": 80}) == "neutral"


def test_llm_direction():
    assert llm_direction(75) == "bull"
    assert llm_direction(20) == "bear"
    assert llm_direction(50) == "neutral"


def test_divergence_flag_contradiction():
    # LLM otimista (80) mas técnico bear => divergência
    assert divergence_flag(80, {"preco_vs_sma200_pct": -5.0, "macd_histogram": -0.3}) == 1


def test_divergence_flag_aligned():
    assert divergence_flag(80, {"preco_vs_sma200_pct": 5.0, "macd_histogram": 0.3}) == 0


def test_divergence_flag_no_indicators_is_zero():
    assert divergence_flag(80, {}) == 0


def test_divergence_does_not_mutate_score():
    """Garantia da Opção 1: o score final é o do LLM, intocado pelo cross-check."""
    assert calculate_final_score({"opportunity_score": 88}) == 88.0
