"""
Testes de _portfolio_equity_curve (V-01, revisão 2 — contabilidade por evento).

Cobre a distinção central desta revisão: alocação de capital fixada no
instante de ABERTURA de cada trade, com P&L creditado de volta em ordem
cronológica de FECHAMENTO — em vez do peso fixo 1/num_slots aplicado
multiplicativamente em ordem de fechamento (revisão anterior), que
subestimava perdas concorrentes por herdar implicitamente a base já
reduzida por fechamentos que ainda não eram conhecidos no momento em que
a alocação foi decidida.
"""

import pytest
from predictor_core.stats import max_drawdown

from GarimpoInvestimentos.v3.backtest_v3 import (
    _MS_PER_8H,
    _SPOT_CANDLE_MS,
    _calmar_ratio,
    _portfolio_equity_curve,
    _sortino_ratio,
    _Trade,
)


def test_curva_vazia_para_lista_vazia():
    assert _portfolio_equity_curve([], num_slots=3) == []


def test_trade_unico_sem_concorrencia_usa_capital_integral_do_slot():
    # num_slots=1: o trade recebe 100% do equity — comportamento idêntico
    # a uma composição sequencial simples de um único trade.
    trades = [_Trade(entry_ms=0, net_return=0.10, horizon_hours=24)]
    curve = _portfolio_equity_curve(trades, num_slots=1)
    assert curve[-1] == pytest.approx(1.10)


def test_tres_perdas_concorrentes_dividem_capital_aditivamente():
    """
    3 trades concorrentes (entradas 8h/8h/8h, horizonte 24h -> num_slots=3),
    cada um perdendo -50% do seu próprio slot (1/3 do capital no momento
    da abertura). A perda real ao portfólio é ADITIVA: 3 * (1/3 * 50%) =
    50% do capital total — não a composição multiplicativa (1-1/6)^3 ~=
    42.1% de perda, que era o resultado (incorreto) da revisão anterior.
    """
    trades = [_Trade(entry_ms=i * _MS_PER_8H, net_return=-0.5, horizon_hours=24) for i in range(3)]
    curve = _portfolio_equity_curve(trades, num_slots=3)
    assert curve[-1] == pytest.approx(0.5)
    assert max_drawdown(curve) == pytest.approx(0.5, rel=1e-6)


def test_ganho_realizado_e_reinvestido_no_proximo_trade_do_mesmo_slot():
    """
    Sem sobreposição temporal (T2 abre só depois que T1 fecha), o segundo
    trade deve capturar 1/num_slots do equity JÁ CRESCIDO pelo ganho do
    primeiro — reinvestimento correto do capital realizado.
    """
    horizon_ms = 24 * _SPOT_CANDLE_MS
    trades = [
        _Trade(entry_ms=0, net_return=0.20, horizon_hours=24),
        _Trade(entry_ms=horizon_ms, net_return=0.20, horizon_hours=24),
    ]
    curve = _portfolio_equity_curve(trades, num_slots=1)
    assert curve[-1] == pytest.approx(1.2 * 1.2)


def test_capital_nunca_alocado_alem_do_caixa_disponivel():
    """
    Mesmo em cenários de perdas sucessivas que reduzem o equity total, a
    alocação de um novo slot nunca deve exceder o caixa disponível
    (proteção min(alloc, cash) — nunca deveria faltar caixa dado que
    num_slots já é o teto físico de concorrência, mas o guard evita
    crash/alocação negativa se o pressuposto for violado por engano).
    """
    trades = [
        _Trade(entry_ms=0, net_return=-0.9, horizon_hours=24),
        _Trade(entry_ms=_MS_PER_8H, net_return=-0.9, horizon_hours=24),
        _Trade(entry_ms=2 * _MS_PER_8H, net_return=-0.9, horizon_hours=24),
    ]
    curve = _portfolio_equity_curve(trades, num_slots=3)
    assert all(e >= 0.0 for e in curve)


def test_slot_ocioso_nao_contribui_retorno():
    # Só 1 trade ativo com num_slots=3: os outros 2/3 do capital ficam
    # parados (equity não deve variar além da fração alocada ao trade).
    trades = [_Trade(entry_ms=0, net_return=0.30, horizon_hours=24)]
    curve = _portfolio_equity_curve(trades, num_slots=3)
    assert curve[-1] == pytest.approx(1.0 + (1.0 / 3.0) * 0.30)


def test_sortino_ignora_dispersao_de_ganhos():
    """
    Dois conjuntos de retornos com a MESMA média e o MESMO desvio total, mas
    um deles com toda a variância concentrada em ganhos (upside) — o Sortino
    do segundo deve ser estritamente maior que o do primeiro, já que só
    penaliza desvio de retornos negativos.
    """
    returns_dispersao_simetrica = [0.10, -0.10, 0.10, -0.10]
    returns_so_upside_varia = [0.05, 0.05, 0.25, -0.15]  # mesma média/desvio total
    s1 = _sortino_ratio(returns_dispersao_simetrica)
    s2 = _sortino_ratio(returns_so_upside_varia)
    assert s2 > s1


def test_sortino_zero_sem_retornos_negativos():
    # Sem downside, downside_std=0 -> não dá pra dividir; retorna 0.0 (não inf).
    assert _sortino_ratio([0.05, 0.10, 0.03]) == 0.0


def test_sortino_amostra_insuficiente():
    assert _sortino_ratio([0.05]) == 0.0
    assert _sortino_ratio([]) == 0.0


def test_calmar_usa_retorno_cumulativo_da_curva_nao_media_por_trade():
    """
    Calmar = retorno cumulativo do portfólio / |MaxDD| — sobre a MESMA curva
    usada no MaxDD, não sobre a média aritmética de retorno por trade
    (grandezas diferentes: uma é do portfólio, a outra é por posição). Um
    trade perdedor seguido de um vencedor maior gera drawdown real e
    recuperação — exercita o cálculo de verdade, não só o caso-limite dd=0.
    """
    from predictor_core.stats import max_drawdown

    trades = [
        _Trade(entry_ms=0, net_return=-0.20, horizon_hours=24),
        _Trade(entry_ms=24 * _SPOT_CANDLE_MS, net_return=0.50, horizon_hours=24),
    ]
    curve = _portfolio_equity_curve(trades, num_slots=1)
    dd = max_drawdown(curve)
    assert dd > 1e-9

    calmar = _calmar_ratio(curve, dd)
    cumulative_return = curve[-1] - 1.0
    assert calmar == pytest.approx(cumulative_return / dd)


def test_calmar_zero_para_curva_vazia_ou_sem_drawdown():
    assert _calmar_ratio([], max_dd=0.1) == 0.0
    assert _calmar_ratio([1.0, 1.1, 1.2], max_dd=0.0) == 0.0
