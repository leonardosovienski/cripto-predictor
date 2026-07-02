"""Modelo de custos (Risco 4 — passo 5.2): fricção round-trip + funding signed.

Invariantes: fricção sempre ≥ 0 e com DUAS pernas; funding é signed (long paga
f>0, short recebe); posição zero não paga nada; líquido < bruto sempre que há
fricção e o funding não a compensa.
"""
from GarimpoInvestimentos.v3.costs import CostModel


def test_friccao_duas_pernas_sobre_posicao_absoluta():
    cm = CostModel(taker_fee_bps=10.0, slippage_bps=5.0)
    # (10+5) bps por perna × 2 pernas = 30 bps sobre |posição|
    assert abs(cm.friction(1.0) - 0.0030) < 1e-12
    assert cm.friction(-0.5) == cm.friction(0.5)          # short paga igual
    assert cm.friction(0.0) == 0.0


def test_funding_signed_long_paga_short_recebe():
    cm = CostModel()
    f = 0.0001                                            # +1bp por janela de 8h
    assert cm.funding_pnl(1.0, f, 8.0) < 0                # long paga
    assert cm.funding_pnl(-1.0, f, 8.0) > 0               # short recebe
    assert cm.funding_pnl(1.0, -f, 8.0) > 0               # funding negativo inverte
    # horizonte de 24h = 3 janelas
    assert abs(cm.funding_pnl(1.0, f, 24.0) - (-3 * f)) < 1e-12


def test_net_return_liquido_de_tudo():
    cm = CostModel(taker_fee_bps=10.0, slippage_bps=5.0)
    gross, pos, f = 0.0100, 1.0, 0.0001
    net = cm.net_return(gross, pos, f, 8.0)
    # bruto 100bps − fricção 30bps − funding 1bp = 69bps
    assert abs(net - 0.0069) < 1e-12
    assert net < gross


def test_posicao_zero_nao_paga_custo():
    cm = CostModel()
    assert cm.net_return(0.0, 0.0, 0.01, 8.0) == 0.0


def test_edge_menor_que_custo_vira_prejuizo_liquido():
    """A razão de o Risco 4 existir: bruto positivo pode ser líquido negativo."""
    cm = CostModel(taker_fee_bps=10.0, slippage_bps=5.0)
    assert cm.net_return(0.0020, 1.0, 0.0, 8.0) < 0       # 20bps de edge < 30bps de custo
