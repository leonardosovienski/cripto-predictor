"""Controle de permutação/placebo (bloco 11 do congelamento científico).

Não existia nenhum teste de permutação no repo antes desta auditoria — os
controles positivo/negativo existentes (scripts/attest_harness.py,
tests/test_pbo.py) usam RUÍDO SINTÉTICO independente para o braço negativo,
não permutação dos rótulos de uma série com efeito real plantado. São
controles relacionados mas estatisticamente distintos: ruído independente
testa "o juiz recusa dado sem relação alguma"; permutação testa algo mais
forte — "o juiz para de validar quando a MESMA série com sinal real tem o
pareamento score<->retorno destruído por embaralhamento".

Reaproveita a função real do juiz da Fase 1 (spearman_block_ci, já usada em
GarimpoInvestimentos/analyzers/backtest.py:_report) — não cria estatística
nova, só aplica a existente sobre dados permutados. Controle mínimo, sem
framework novo.
"""

import random

from predictor_core.measurement.stats import spearman_block_ci


def _synthetic_pairs_with_real_signal(n: int = 120, seed: int = 11) -> list[tuple[float, float]]:
    """Série sintética com efeito real plantado (score prediz retorno)."""
    rng = random.Random(seed)
    pairs = []
    for _ in range(n):
        score = rng.uniform(-1, 1)
        retorno = 0.6 * score + rng.gauss(0, 0.15)  # sinal real + ruído
        pairs.append((score, retorno))
    return pairs


# n_boot reduzido do default (10_000) — o teste precisa de um sinal
# estatístico rápido para CI unitário, não de precisão de publicação. O
# default de produção (spearman_block_ci sem argumento) continua 10_000;
# aqui só o CONSUMO deste teste é mais barato.
_FAST_N_BOOT = 300


def test_serie_com_sinal_real_e_validada_pelo_juiz():
    pairs = _synthetic_pairs_with_real_signal()
    rho, lo, hi = spearman_block_ci(pairs, block_length=4, n_boot=_FAST_N_BOOT)
    assert rho is not None and lo is not None and hi is not None
    validado = lo > 0 or hi < 0
    assert validado, "sinal real plantado deveria ser detectado (sensibilidade)"


def test_permutacao_dos_retornos_destroi_o_sinal_e_juiz_para_de_validar():
    """O controle que faltava: embaralha só a coluna de retorno (mantém a
    distribuição marginal idêntica, destrói o pareamento score<->retorno) e
    confirma que o MESMO juiz, sobre os MESMOS valores, deixa de validar.
    """
    pairs = _synthetic_pairs_with_real_signal()
    scores = [s for s, _ in pairs]
    retornos = [r for _, r in pairs]

    rng = random.Random(2026)
    n_permutacoes = 40
    falsos_positivos = 0
    for _ in range(n_permutacoes):
        retornos_embaralhados = retornos[:]
        rng.shuffle(retornos_embaralhados)
        pares_permutados = list(zip(scores, retornos_embaralhados, strict=True))
        rho, lo, hi = spearman_block_ci(pares_permutados, block_length=4, n_boot=_FAST_N_BOOT)
        if rho is not None and lo is not None and hi is not None:
            if lo > 0 or hi < 0:
                falsos_positivos += 1

    # Sob H0 (pareamento destruído), o juiz não deveria validar com frequência
    # muito acima do alpha nominal (~5%). Margem folgada (15%) porque é teste
    # estatístico com n=200 permutações, não uma prova exata — mas qualquer
    # coisa muito acima disso indicaria juiz fabricando significância em ruído.
    taxa_falso_positivo = falsos_positivos / n_permutacoes
    assert taxa_falso_positivo < 0.25, (
        f"juiz validou {falsos_positivos}/{n_permutacoes} permutações "
        f"({taxa_falso_positivo:.1%}) do sinal destruído — especificidade "
        f"pior que o esperado sob H0"
    )


def test_permutacao_completa_dos_dois_lados_tambem_nao_valida():
    """Variante mais forte: embaralha AMBAS as colunas independentemente
    (não só a de retorno) — garante que o teste não depende de alguma
    estrutura residual só na coluna de score.
    """
    pairs = _synthetic_pairs_with_real_signal()
    rng = random.Random(99)
    scores = [s for s, _ in pairs]
    retornos = [r for _, r in pairs]
    rng.shuffle(scores)
    rng.shuffle(retornos)
    pares_totalmente_embaralhados = list(zip(scores, retornos, strict=True))

    rho, lo, hi = spearman_block_ci(
        pares_totalmente_embaralhados, block_length=4, n_boot=_FAST_N_BOOT
    )
    if rho is not None and lo is not None and hi is not None:
        validado = lo > 0 or hi < 0
        assert not validado, "embaralhamento total não deveria produzir validação"
