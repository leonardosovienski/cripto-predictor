"""Pedágio do cripto — Spearman + block bootstrap (significância do score do LLM).

Roda sem .env: importa só core.stats (puro, sem settings/rede). Invoque de
C:\\Claude\\previsao-cripto:  py -3.12 -m pytest tests/ -q
"""
import random

from predictor_core.stats import (
    spearman,
    block_bootstrap_ci,
    spearman_block_ci,
)


def test_spearman_perfect_monotonic():
    assert abs(spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]) - 1.0) < 1e-9


def test_spearman_perfect_inverse():
    assert abs(spearman([1, 2, 3, 4, 5], [50, 40, 30, 20, 10]) + 1.0) < 1e-9


def test_spearman_none_below_3():
    assert spearman([1, 2], [3, 4]) is None


def test_block_bootstrap_reproducible():
    units = [float(i % 5) for i in range(60)]
    mean = lambda u: sum(u) / len(u)
    r1 = block_bootstrap_ci(units, mean, block_length=5, seed=1)
    r2 = block_bootstrap_ci(units, mean, block_length=5, seed=1)
    assert r1[:2] == r2[:2]


def test_spearman_ci_below_4_is_none():
    assert spearman_block_ci([(1, 2), (3, 4), (5, 6)]) == (None, None, None)


def test_spearman_ci_detects_real_signal():
    """Score correlacionado com o retorno => IC 95% NÃO cruza zero (sinal validado)."""
    rng = random.Random(3)
    pairs = []
    for _ in range(80):
        s = rng.uniform(0, 100)
        ret = 0.1 * (s - 50) + rng.gauss(0, 2)   # retorno cresce com o score
        pairs.append((s, ret))
    rho, lo, hi = spearman_block_ci(pairs, seed=7)
    assert rho > 0.5
    assert lo > 0, f"IC deveria estar acima de 0 para sinal real: [{lo}, {hi}]"


def test_spearman_ci_flags_noise():
    """Score independente do retorno => IC 95% cruza zero (ruído)."""
    rng = random.Random(4)
    pairs = [(rng.uniform(0, 100), rng.gauss(0, 2)) for _ in range(80)]
    rho, lo, hi = spearman_block_ci(pairs, seed=7)
    assert lo < 0 < hi, f"IC deveria cruzar 0 para ruído: [{lo}, {hi}]"
