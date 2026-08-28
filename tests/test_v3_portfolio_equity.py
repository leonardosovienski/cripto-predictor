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
    _portfolio_equity_curve,
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
