"""PBO/CSCV — controle positivo da própria ferramenta.

Mesma disciplina que `scripts/attest_harness.py` aplica aos juízes: uma métrica
de overfitting que nunca foi confrontada com um caso de skill REAL e um caso de
ruído PURO não tem poder demonstrado. Se o PBO não distingue os dois, ele é
decoração — pior que ausente, porque dá sensação de rigor.
"""

import math
import random

import pytest

from GarimpoInvestimentos.analyzers.pbo import (
    PBOError,
    probability_of_backtest_overfitting,
    sharpe,
)


def _skill_real(n_obs=320, n_config=8, seed=11):
    """Uma configuração tem edge GENUÍNO e persistente; as outras são ruído.
    A melhor IS deve continuar melhor OOS -> PBO baixo."""
    rng = random.Random(seed)
    dados = {
        f"ruido_{i}": [rng.gauss(0.0, 0.01) for _ in range(n_obs)] for i in range(n_config - 1)
    }
    dados["com_edge"] = [rng.gauss(0.004, 0.01) for _ in range(n_obs)]
    return dados


def _ruido_puro(n_obs=320, n_config=8, seed=12):
    """Nenhuma configuração tem edge. Quem parece melhor IS é sorte, então
    OOS cai em posição aleatória -> PBO perto de 0.5."""
    rng = random.Random(seed)
    return {f"cfg_{i}": [rng.gauss(0.0, 0.01) for _ in range(n_obs)] for i in range(n_config)}


def test_skill_real_produz_pbo_baixo():
    r = probability_of_backtest_overfitting(_skill_real(), n_splits=10)
    assert r.pbo < 0.10, f"edge genuíno deveria dar PBO baixo, deu {r.pbo}"
    assert r.veredito.startswith("BAIXO")


def test_ruido_puro_produz_pbo_alto():
    r = probability_of_backtest_overfitting(_ruido_puro(), n_splits=10)
    assert r.pbo > 0.30, f"ruído puro deveria dar PBO alto, deu {r.pbo}"


def test_sensibilidade_e_especificidade_juntas():
    """O par é o que importa: uma métrica que sempre diz 'baixo' passa no
    primeiro teste e é inútil; uma que sempre diz 'alto' passa no segundo."""
    skill = probability_of_backtest_overfitting(_skill_real(), n_splits=10).pbo
    ruido = probability_of_backtest_overfitting(_ruido_puro(), n_splits=10).pbo
    assert skill < ruido, f"PBO não discrimina: skill={skill}, ruído={ruido}"


def test_numero_de_combinacoes_e_o_da_teoria():
    r = probability_of_backtest_overfitting(_ruido_puro(n_obs=200), n_splits=8)
    assert r.n_combinations == math.comb(8, 4)  # C(S, S/2)
    assert r.n_splits == 8


def test_observacoes_descartadas_sao_reportadas_nao_silenciosas():
    """T não divisível por S força descarte. Silenciar isso esconderia que
    parte da amostra não entrou na conta."""
    r = probability_of_backtest_overfitting(_ruido_puro(n_obs=205), n_splits=10)
    assert r.dropped_observations == 5
    assert r.n_observations == 205


def test_uma_configuracao_so_e_erro_nao_valor_de_conveniencia():
    """PBO mede a escolha ENTRE alternativas: com uma só, é indefinido.
    Devolver 0.0 aqui seria mentir 'não há overfitting'."""
    with pytest.raises(PBOError, match="2 configuracoes"):
        probability_of_backtest_overfitting({"unica": [0.1] * 100})


def test_n_splits_impar_e_recusado():
    with pytest.raises(PBOError, match="PAR"):
        probability_of_backtest_overfitting(_ruido_puro(), n_splits=7)


def test_series_de_comprimentos_diferentes_sao_recusadas():
    """Configurações avaliadas em janelas diferentes não são comparáveis; casar
    posição por índice produziria um ranking sem significado."""
    with pytest.raises(PBOError, match="MESMA serie"):
        probability_of_backtest_overfitting({"a": [0.1] * 100, "b": [0.1] * 90})


def test_amostra_curta_demais_e_recusada():
    with pytest.raises(PBOError, match="insuficientes"):
        probability_of_backtest_overfitting(_ruido_puro(n_obs=10), n_splits=10)


def test_sharpe_de_serie_constante_nao_vence_ninguem():
    """Variância zero -> -inf, nunca 0.0: uma série constante ficaria acima de
    qualquer configuração de retorno negativo e seria eleita 'a melhor'."""
    assert sharpe([0.01] * 50) == float("-inf")
    assert sharpe([0.01]) == float("-inf")
    assert sharpe([-0.01, -0.02, -0.03]) < 0


def test_pbo_fica_no_intervalo_valido():
    for dados in (_skill_real(), _ruido_puro()):
        r = probability_of_backtest_overfitting(dados, n_splits=10)
        assert 0.0 <= r.pbo <= 1.0
        assert len(r.logits) == r.n_combinations
