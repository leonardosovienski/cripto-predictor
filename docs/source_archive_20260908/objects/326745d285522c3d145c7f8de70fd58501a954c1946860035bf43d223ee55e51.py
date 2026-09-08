"""Cobertura da gestão de risco intratrade (SL/TP) do backtest V3.

Antes desta revisão o backtest_v3 só avaliava o sinal no horizonte fixo
(24h/48h) — nenhuma saída antecipada por perda ou ganho. `_find_barrier_return`
adiciona isso como camada opcional sobre o P&L, sem alterar o cálculo do IC
(que continua medindo o sinal cru contra o retorno do horizonte cheio).
"""

import math

from GarimpoInvestimentos.v3.backtest_v3 import _find_barrier_return

_HOUR_MS = 3_600_000


def _spot_index(prices: list[float], start_ms: int = 1_700_000_000_000) -> dict[int, float]:
    """Constrói um índice timestamp→close com velas de 1h a partir de start_ms."""
    return {start_ms + i * _HOUR_MS: p for i, p in enumerate(prices)}


def test_sem_barreiras_cai_no_retorno_do_horizonte_cheio():
    # comportamento antigo preservado quando sl/tp == 0 (default)
    entry = 100.0
    prices = [entry, 101, 99, 102, 98, 103]  # 5 candles após a entrada (horizonte=5h)
    idx = _spot_index(prices)
    entry_ts = next(iter(idx))
    r = _find_barrier_return(entry_ts + _HOUR_MS, horizon_hours=5, direction=1, spot_index=idx)
    assert r is not None
    ret, reason = r
    assert reason == "horizon"
    assert math.isclose(ret, math.log(prices[-1] / entry), rel_tol=1e-9)


def test_stop_loss_corta_a_cauda_de_perda_em_posicao_long():
    entry = 100.0
    # cai 3% na 2a vela (dentro do horizonte de 5h) — stop de 1% deve disparar antes
    prices = [entry, 99.5, 97.0, 96.0, 95.0, 94.0]
    idx = _spot_index(prices)
    entry_ts = next(iter(idx))
    r = _find_barrier_return(
        entry_ts + _HOUR_MS,
        horizon_hours=5,
        direction=1,
        spot_index=idx,
        stop_loss_bps=100.0,  # 1%
    )
    assert r is not None
    ret, reason = r
    assert reason == "stop_loss"
    # retorno truncado no stop, não no fim do caminho (muito mais negativo)
    assert math.isclose(ret, -0.01, rel_tol=1e-6)


def test_take_profit_corta_o_upside_em_posicao_short():
    entry = 100.0
    # preço cai 3% (lucro pra short) — take-profit de 1% deve disparar antes
    prices = [entry, 99.5, 97.0, 96.0, 95.0]
    idx = _spot_index(prices)
    entry_ts = next(iter(idx))
    r = _find_barrier_return(
        entry_ts + _HOUR_MS,
        horizon_hours=4,
        direction=-1,  # short: lucra quando o preço cai
        spot_index=idx,
        take_profit_bps=100.0,  # 1%
    )
    assert r is not None
    ret, reason = r
    assert reason == "take_profit"
    # ret é o retorno no frame de position*ret (já ajustado por direção no gross)
    assert math.isclose(ret, -0.01, rel_tol=1e-6)


def test_stop_loss_nao_dispara_se_dentro_da_margem():
    entry = 100.0
    prices = [entry, 100.2, 100.5, 100.1, 100.8]
    idx = _spot_index(prices)
    entry_ts = next(iter(idx))
    r = _find_barrier_return(
        entry_ts + _HOUR_MS,
        horizon_hours=4,
        direction=1,
        spot_index=idx,
        stop_loss_bps=200.0,  # 2%, nunca cruzado
        take_profit_bps=500.0,  # 5%, nunca cruzado
    )
    assert r is not None
    ret, reason = r
    assert reason == "horizon"


def test_sem_preco_de_entrada_retorna_none():
    idx = _spot_index([100.0, 101.0], start_ms=9_999_999_999_999)
    r = _find_barrier_return(1_700_000_000_000, horizon_hours=5, direction=1, spot_index=idx)
    assert r is None
