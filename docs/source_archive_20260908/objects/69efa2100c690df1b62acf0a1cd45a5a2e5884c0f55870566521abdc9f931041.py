"""PBO — Probabilidade de Overfitting do Backtest, via CSCV (B10 em docs/HYPOTHESES.md).

COMPLEMENTA o Deflated Sharpe Ratio, não o substitui. As duas perguntas são
diferentes e as duas importam:

  DSR  — "este Sharpe sobrevive ao MÁXIMO ESPERADO POR SORTE, dadas N tentativas?"
         Opera sobre um número agregado por tentativa (o que `trials.json` guarda).
  PBO  — "qual a PROBABILIDADE de que a configuração escolhida como melhor seja,
         de fato, overfit?" Opera sobre a SÉRIE de retornos de cada configuração,
         medindo com que frequência a melhor in-sample cai na metade pior
         out-of-sample.

Um DSR alto com PBO alto significa: o número passou no desconto por múltiplas
tentativas, mas o PROCESSO de seleção entre configurações continua frágil.

Método (Bailey, Borwein, López de Prado & Zhu — SSRN 2326253), CSCV:
  1. matriz T observações x N configurações de retorno;
  2. particiona T em S blocos CONTÍGUOS (S par) — contíguos porque quebrar a
     ordem temporal destruiria a dependência serial que o método precisa
     preservar dentro de cada bloco;
  3. para cada uma das C(S, S/2) combinações, metade dos blocos vira IS e o
     complemento vira OOS;
  4. n* = argmax da performance IS; calcula o rank de n* OOS;
  5. omega = rank / (N+1);  lambda = logit(omega);
  6. PBO = fração de combinações com lambda <= 0, isto é, a melhor IS caiu na
     metade inferior OOS.

Implementação em stdlib puro (sem numpy) DE PROPÓSITO: `analyzers/` roda na
instalação base, sem os extras `science`/`v3`. Exigir numpy aqui tornaria o PBO
indisponível justamente na suíte offline que o CI roda por padrão.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import combinations

# S par e não muito grande: C(16,8)=12870 combinações, suficiente para uma
# estimativa estável e barato em Python puro. Valor usado no paper original.
DEFAULT_N_SPLITS = 16


class PBOError(ValueError):
    """Entrada insuficiente para o PBO ser DEFINIDO (não é falha transitória)."""


@dataclass(frozen=True)
class PBOResult:
    pbo: float
    n_configs: int
    n_observations: int
    n_splits: int
    n_combinations: int
    logits: tuple[float, ...]
    dropped_observations: int

    @property
    def veredito(self) -> str:
        """Leitura textual. Os cortes são convenção de LEITURA, não gate: o
        projeto não tem critério pré-registrado sobre PBO, e inventar um agora
        seria exatamente o tipo de limiar escolhido depois de ver o número que
        o pré-registro existe para impedir."""
        if self.pbo >= 0.5:
            return "ALTO (>=0.50) — seleção indistinguível de sorte"
        if self.pbo >= 0.2:
            return "MODERADO (0.20-0.50)"
        return "BAIXO (<0.20)"


def sharpe(returns: Sequence[float]) -> float:
    """Sharpe por observação, sem anualizar — o PBO só usa a ORDENAÇÃO entre
    configurações, e anualizar é uma transformação monotônica que não a altera.
    Variância zero devolve -inf: uma série constante nunca deve ser eleita a
    melhor, e devolver 0.0 a colocaria acima de qualquer config negativa."""
    n = len(returns)
    if n < 2:
        return float("-inf")
    media = sum(returns) / n
    var = sum((x - media) ** 2 for x in returns) / (n - 1)
    if var <= 0:
        return float("-inf")
    return media / math.sqrt(var)


def _blocos(n_obs: int, n_splits: int) -> list[range]:
    """Blocos contíguos de tamanho igual. O resto é descartado do INÍCIO (dado
    mais ANTIGO): uma decisão prospectiva usa o passado recente, então preservar
    a cauda recente é o descarte menos danoso — e fica reportado em
    `dropped_observations` para não ser silencioso."""
    tamanho = n_obs // n_splits
    inicio = n_obs - tamanho * n_splits
    return [range(inicio + i * tamanho, inicio + (i + 1) * tamanho) for i in range(n_splits)]


def probability_of_backtest_overfitting(
    returns_by_config: dict[str, Sequence[float]],
    *,
    n_splits: int = DEFAULT_N_SPLITS,
    performance: Callable[[Sequence[float]], float] = sharpe,
) -> PBOResult:
    """PBO por CSCV. Levanta PBOError quando o número é INDEFINIDO — nunca
    devolve um valor de conveniência para entrada insuficiente."""
    if len(returns_by_config) < 2:
        raise PBOError(
            "PBO exige >= 2 configuracoes: ele mede a escolha ENTRE alternativas. "
            f"Recebidas: {len(returns_by_config)}."
        )
    if n_splits % 2 or n_splits < 2:
        raise PBOError(f"n_splits deve ser PAR e >= 2 (CSCV divide ao meio); recebido {n_splits}.")

    tamanhos = {len(v) for v in returns_by_config.values()}
    if len(tamanhos) != 1:
        raise PBOError(
            "todas as configuracoes precisam ter a MESMA serie de observacoes "
            f"(mesmas datas, mesmo comprimento); comprimentos: {sorted(tamanhos)}."
        )
    n_obs = tamanhos.pop()
    if n_obs < n_splits * 2:
        raise PBOError(
            f"observacoes insuficientes: {n_obs} para n_splits={n_splits} "
            f"(minimo {n_splits * 2}, para 2 observacoes por bloco)."
        )

    nomes = sorted(returns_by_config)
    series = [list(returns_by_config[nome]) for nome in nomes]
    blocos = _blocos(n_obs, n_splits)
    n_config = len(nomes)

    logits: list[float] = []
    for is_idx in combinations(range(n_splits), n_splits // 2):
        oos_idx = [i for i in range(n_splits) if i not in is_idx]
        is_pos = [p for i in is_idx for p in blocos[i]]
        oos_pos = [p for i in oos_idx for p in blocos[i]]

        perf_is = [performance([s[p] for p in is_pos]) for s in series]
        melhor = max(range(n_config), key=lambda c: perf_is[c])

        perf_oos = [performance([s[p] for p in oos_pos]) for s in series]
        # rank 1 = PIOR, n_config = MELHOR. Empates contam como "não superado",
        # o que é a leitura conservadora: empatar com a melhor não é evidência
        # de que a seleção funcionou.
        rank = 1 + sum(1 for c in range(n_config) if perf_oos[c] < perf_oos[melhor])
        omega = rank / (n_config + 1)
        logits.append(math.log(omega / (1 - omega)))

    pbo = sum(1 for x in logits if x <= 0) / len(logits)
    return PBOResult(
        pbo=pbo,
        n_configs=n_config,
        n_observations=n_obs,
        n_splits=n_splits,
        n_combinations=len(logits),
        logits=tuple(logits),
        dropped_observations=n_obs - len(blocos) * len(blocos[0]),
    )


__all__ = [
    "DEFAULT_N_SPLITS",
    "PBOError",
    "PBOResult",
    "probability_of_backtest_overfitting",
    "sharpe",
]
