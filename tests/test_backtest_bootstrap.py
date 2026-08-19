"""block_length do bootstrap deve cobrir o overlap real (horizonte / cadência).

Auditoria 2026-08-19: block_length=5 (default de spearman_block_ci) era menor
que o horizonte de 7 dias de H5/H6 com emissão diária — o bloco não cobria a
janela inteira de overlap entre previsões vizinhas, subestimando a dependência
serial. overlap_block_length() é a regra que fecha essa lacuna.
"""

import pytest

from GarimpoInvestimentos.analyzers.backtest import overlap_block_length


def test_horizonte_diario_d7_exige_bloco_de_7():
    assert overlap_block_length(7, emission_interval_days=1) == 7


def test_horizonte_d1_com_emissao_diaria_nao_tem_overlap():
    assert overlap_block_length(1, emission_interval_days=1) == 1


def test_horizonte_d30_exige_bloco_de_30():
    assert overlap_block_length(30, emission_interval_days=1) == 30


def test_emissao_menos_frequente_reduz_overlap_arredondando_para_cima():
    # horizonte 7d, emissao a cada 2 dias -> ceil(7/2) = 4
    assert overlap_block_length(7, emission_interval_days=2) == 4


def test_emissao_intervalo_invalido_levanta():
    with pytest.raises(ValueError):
        overlap_block_length(7, emission_interval_days=0)


def test_default_usa_cadencia_diaria_do_projeto():
    from GarimpoInvestimentos.analyzers.backtest import EMISSION_INTERVAL_DAYS

    assert EMISSION_INTERVAL_DAYS == 1
    assert overlap_block_length(7) == 7
