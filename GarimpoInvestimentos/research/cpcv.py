"""CPCV — Combinatorial Purged Cross-Validation, com purga e embargo derivados dos dados.

Referência: M. López de Prado, *Advances in Financial Machine Learning* (Wiley, 2018),
cap. 7 (purged k-fold e embargo) e cap. 12 (CPCV). Mesma semântica de rótulo de
`research.validation.LabelInterval`: a janela de informação da observação i é o intervalo
fechado [start_i, available_i] (decisão -> instante em que o alvo fica conhecido,
available_i >= end_i), num relógio inteiro declarado (ex.: ms).

  1. as observações (ordenadas pelo início do rótulo) são divididas em N grupos contíguos;
  2. cada combinação de k grupos vira TESTE; os demais são candidatos a TREINO;
     grupos de teste adjacentes formam um único bloco;
  3. PURGA: sai do treino toda observação cuja janela de informação intercepta a janela
     de um bloco de teste [menor start, maior available] — nenhuma informação de rótulo
     do treino se sobrepõe à janela do teste;
  4. EMBARGO: sai do treino toda observação que começa até `embargo` depois do fim de um
     bloco de teste (dependência serial que sobrevive ao fim do rótulo);
  5. o número de caminhos de backtest é C(N-1, k-1).

`derive_purge_and_embargo` fixa os tamanhos pela semântica temporal, não por "parecer
razoável": a purga é o horizonte do rótulo; o embargo é o maior lag com autocorrelação
significativa dos retornos por passo (banda de Bartlett ±1,96/√n sob ruído branco).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations

from GarimpoInvestimentos.research.validation import LabelInterval


@dataclass(frozen=True)
class CPCVSplit:
    test_groups: tuple[int, ...]
    train: tuple[int, ...]
    test: tuple[int, ...]
    purged: tuple[int, ...]
    embargoed: tuple[int, ...]


def group_bounds(n_observations: int, n_groups: int) -> list[range]:
    """N grupos contíguos de tamanho quase igual (os primeiros recebem a sobra)."""
    if n_groups < 2 or n_observations < n_groups:
        raise ValueError("CPCV exige >= 2 grupos e ao menos uma observação por grupo")
    base, extra = divmod(n_observations, n_groups)
    bounds, start = [], 0
    for g in range(n_groups):
        size = base + (1 if g < extra else 0)
        bounds.append(range(start, start + size))
        start += size
    return bounds


def n_backtest_paths(n_groups: int, n_test_groups: int) -> int:
    return math.comb(n_groups - 1, n_test_groups - 1)


def backtest_paths(splits: list[CPCVSplit], n_groups: int) -> list[list[tuple[int, int]]]:
    """Caminho p = para cada grupo g, a p-ésima divisão (em ordem) que testa g.

    Cada caminho cobre todos os grupos uma vez, e cada previsão OOS entra em um só caminho.
    """
    by_group: list[list[int]] = [[] for _ in range(n_groups)]
    for index, split in enumerate(splits):
        for g in split.test_groups:
            by_group[g].append(index)
    n_paths = len(by_group[0])
    if any(len(s) != n_paths for s in by_group):
        raise ValueError("divisões não formam um CPCV completo")
    return [[(by_group[g][p], g) for g in range(n_groups)] for p in range(n_paths)]


def cpcv_splits(
    labels: list[LabelInterval], *, n_groups: int, n_test_groups: int, embargo: int
) -> list[CPCVSplit]:
    if any(labels[i].start > labels[i + 1].start for i in range(len(labels) - 1)):
        raise ValueError("rótulos precisam estar ordenados pelo início")
    if not 1 <= n_test_groups < n_groups:
        raise ValueError("1 <= n_test_groups < n_groups")
    if type(embargo) is not int or embargo < 0:
        raise ValueError("embargo deve ser inteiro >= 0 no relógio dos rótulos")
    groups = group_bounds(len(labels), n_groups)
    splits = []
    for test_groups in combinations(range(n_groups), n_test_groups):
        blocks: list[list[int]] = []
        for g in test_groups:
            if blocks and blocks[-1][-1] == g - 1:
                blocks[-1].append(g)
            else:
                blocks.append([g])
        windows = []
        for block in blocks:
            idx = [i for g in block for i in groups[g]]
            windows.append(
                (min(labels[i].start for i in idx), max(labels[i].available for i in idx))
            )
        test = tuple(i for g in test_groups for i in groups[g])
        test_set = set(test)
        train, purged, embargoed = [], [], []
        for i, label in enumerate(labels):
            if i in test_set:
                continue
            if any(label.start <= t1 and label.available >= t0 for t0, t1 in windows):
                purged.append(i)
            elif any(t1 < label.start <= t1 + embargo for _, t1 in windows):
                embargoed.append(i)
            else:
                train.append(i)
        splits.append(CPCVSplit(test_groups, tuple(train), test, tuple(purged), tuple(embargoed)))
    return splits


def autocorrelation(values: list[float], lag: int) -> float:
    n = len(values)
    if not 1 <= lag < n:
        raise ValueError("lag fora da série")
    mean = sum(values) / n
    denom = sum((x - mean) ** 2 for x in values)
    if denom == 0:
        return 0.0
    return sum((values[t] - mean) * (values[t - lag] - mean) for t in range(lag, n)) / denom


def derive_purge_and_embargo(
    step_returns: list[float], *, label_horizon: int, step: int, max_lag: int
) -> dict:
    """Purga = horizonte do rótulo; embargo = (primeiro lag com |ACF| < banda) − 1 passos.

    Se nenhum lag até `max_lag` sai da banda, o embargo fica em `max_lag` passos e
    `capped=True` (a dependência pode ser maior do que o investigado).
    """
    if label_horizon < 0 or step <= 0 or max_lag < 1 or len(step_returns) <= max_lag + 1:
        raise ValueError("parâmetros de derivação inválidos")
    band = 1.96 / math.sqrt(len(step_returns))
    acf = [autocorrelation(step_returns, lag) for lag in range(1, max_lag + 1)]
    first_insignificant = next((lag for lag, v in enumerate(acf, 1) if abs(v) < band), None)
    embargo_steps = max_lag if first_insignificant is None else first_insignificant - 1
    return {
        "purge_size": label_horizon,
        "embargo_size": embargo_steps * step,
        "embargo_steps": embargo_steps,
        "capped": first_insignificant is None,
        "acf": acf,
        "band": band,
        "rule": "purga = horizonte do rótulo; embargo = lags iniciais consecutivos com "
        "|ACF| >= 1,96/sqrt(n) nos retornos por passo, não sobrepostos",
    }
