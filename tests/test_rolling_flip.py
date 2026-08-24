"""Testes do monitor de flip de sinal (rolling Spearman) e do diagnóstico
do mecanismo da H6 — P0 da auditoria externa 2026-08-24."""

from datetime import datetime, timedelta

from GarimpoInvestimentos.analyzers.backtest import (
    ROLLING_MIN_N,
    ROLLING_WINDOW,
    _spearman_rho,
    rolling_flip_check,
)
from scripts.diagnose_h6_mechanism import compute_mechanism, interpret


def _enriched(pairs, start=datetime(2026, 1, 1)):
    """pairs: lista de (score, var_pct) em ordem temporal."""
    return [
        {"score": s, "var_d7_pct": v, "pred_date": start + timedelta(days=i)}
        for i, (s, v) in enumerate(pairs)
    ]


def test_spearman_rho_basico():
    assert _spearman_rho([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert _spearman_rho([1, 2, 3, 4], [40, 30, 20, 10]) == -1.0
    assert _spearman_rho([1, 1, 1], [1, 2, 3]) is None  # variância nula
    assert _spearman_rho([1, 2], [1, 2]) is None  # n mínimo


def test_rolling_flip_detecta_inversao():
    # Corpo inicial com correlação positiva forte; cauda recente negativa
    # forte e longa o bastante para encher a janela.
    pos = [(float(i), float(i)) for i in range(80)]
    neg = [(float(80 + i), float(-i)) for i in range(ROLLING_WINDOW)]
    res = rolling_flip_check(_enriched(pos + neg), 7)
    assert res is not None
    _geral, recente, nj = res
    assert nj == ROLLING_WINDOW
    assert recente < 0  # janela recente inverteu


def test_rolling_flip_estavel_sem_inversao():
    pos = [(float(i % 37), float((i % 37) * 2 + (i % 3))) for i in range(150)]
    res = rolling_flip_check(_enriched(pos), 7)
    assert res is not None
    geral, recente, _ = res
    assert (geral > 0) == (recente > 0)


def test_rolling_flip_amostra_pequena_retorna_none():
    small = [(float(i), float(i)) for i in range(ROLLING_MIN_N)]
    assert rolling_flip_check(_enriched(small), 7) is None


def test_mechanism_espelho_do_passado():
    # score == retorno passado (espelho) e futuro anti-correlacionado
    rows = [
        {"score": float(i), "past_ret_pct": float(i), "fut_ret_pct": float(-i)}
        for i in range(30)
    ]
    m = compute_mechanism(rows)
    assert m["n"] == 30
    assert m["rho_score_vs_passado"] == 1.0
    assert m["rho_score_vs_futuro"] == -1.0
    assert m["rho_reversal_ingenuo"] == 1.0  # baseline ingênuo captura tudo
    txt = interpret(m)
    assert "INGÊNUO" in txt  # valor incremental do LLM não demonstrado


def test_mechanism_n_pequeno():
    m = compute_mechanism([{"score": 1.0, "past_ret_pct": 1.0, "fut_ret_pct": 2.0}])
    assert "pequeno demais" in interpret(m)
