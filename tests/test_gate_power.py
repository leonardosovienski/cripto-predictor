"""Poder do gate: distingue 'não há efeito' de 'não dá para ver com esta amostra'.

Os testes usam n_sim pequeno de propósito — a suíte precisa ser rápida, e aqui
o que se verifica é o COMPORTAMENTO da medida (monotonicidade, calibração,
uso do critério real), não o valor exato de cada célula.
"""

import pytest

from GarimpoInvestimentos.analyzers.backtest import overlap_block_length
from GarimpoInvestimentos.analyzers.gate_power import (
    PowerCell,
    detects,
    overlapping_sample,
    power_at,
    power_table,
    render,
)

# n_sim e n_boot pequenos DE PROPOSITO: o gate canônico custa ~1,1s por avaliação
# com n_boot=10_000, e a suíte precisa rodar em segundos. O que se verifica aqui é
# COMPORTAMENTO (monotonicidade, calibração, uso do critério real), não o valor
# exato de cada célula — e esses sobrevivem à redução.
RAPIDO = 40
BOOT = 200


def test_poder_cresce_com_o_tamanho_da_amostra():
    baixo = power_at(30, 0.3, n_sim=RAPIDO, n_boot=BOOT).detection_rate
    alto = power_at(200, 0.3, n_sim=RAPIDO, n_boot=BOOT).detection_rate
    assert alto > baixo, f"poder não cresce com n: n=30 {baixo}, n=200 {alto}"


def test_poder_cresce_com_o_tamanho_do_efeito():
    fraco = power_at(100, 0.1, n_sim=RAPIDO, n_boot=BOOT).detection_rate
    forte = power_at(100, 0.5, n_sim=RAPIDO, n_boot=BOOT).detection_rate
    assert forte > fraco, f"poder não cresce com rho: 0.1 {fraco}, 0.5 {forte}"


def test_taxa_de_falso_positivo_fica_perto_do_nominal():
    """Se o gate disparasse muito no nulo, o problema não seria poder — seria
    fabricação de significância, que é pior."""
    fp = power_at(100, 0.0, n_sim=120, n_boot=BOOT).detection_rate
    assert fp < 0.20, f"taxa de falso positivo alta demais: {fp:.1%}"


def test_amostra_tem_a_sobreposicao_REAL_da_coleta():
    """Observações consecutivas compartilham horizon-1 dias. Gerar independentes
    superestimaria o poder — e o erro seria na direção que interessa evitar."""
    pares = overlapping_sample(50, 0.0, horizon=7, seed=1)
    retornos = [p[1] for p in pares]
    # autocorrelação lag-1 alta é a assinatura da sobreposição
    n = len(retornos)
    m = sum(retornos) / n
    num = sum((retornos[i] - m) * (retornos[i + 1] - m) for i in range(n - 1))
    den = sum((x - m) ** 2 for x in retornos)
    assert num / den > 0.5, "os retornos não estão sobrepostos — poder sairia inflado"


def test_usa_o_criterio_canonico_e_nao_uma_copia():
    """Medir o poder de uma cópia amaciada não diria nada sobre o gate real."""
    import inspect

    fonte = inspect.getsource(detects)
    assert "spearman_block_ci" in fonte
    assert "overlap_block_length" in fonte
    # e o block_length usado é o do projeto para D+7
    assert overlap_block_length(7) == 7


def test_leitura_marca_subdimensionado_abaixo_de_metade():
    assert PowerCell(30, 0.2, 0.14, 100).leitura.startswith("SUBDIMENSIONADO")
    assert "nao e evidencia de ausencia" in PowerCell(30, 0.2, 0.14, 100).leitura
    assert PowerCell(400, 0.3, 0.85, 100).leitura == "adequado"
    assert PowerCell(30, 0.0, 0.05, 100).is_false_positive_cell


def test_render_declara_que_NAO_altera_gate():
    """Trava de governança: a H6 está congelada por hash. Se alguém usar este
    módulo para justificar mudar o n pré-registrado, o texto tem que estar lá
    dizendo que isso é ajuste post-hoc."""
    texto = render(power_table(ns=(30,), rhos=(0.0, 0.3), n_sim=10, n_boot=BOOT))
    assert "NAO altera gate" in texto
    assert "post-hoc" in texto
    assert "ausencia de" in texto


def test_tabela_cobre_todas_as_celulas():
    t = power_table(ns=(30, 50), rhos=(0.0, 0.2), n_sim=10, n_boot=BOOT)
    assert len(t) == 4
    assert {(c.n, c.true_rho) for c in t} == {(30, 0.0), (30, 0.2), (50, 0.0), (50, 0.2)}


def test_determinismo_mesma_seed_mesmo_resultado():
    a = power_at(50, 0.3, n_sim=RAPIDO, n_boot=BOOT, seed0=7).detection_rate
    b = power_at(50, 0.3, n_sim=RAPIDO, n_boot=BOOT, seed0=7).detection_rate
    assert a == pytest.approx(b)
