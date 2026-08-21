"""Poder do gate — quanta chance o criterio tem de VER um efeito que existe.

=== A PERGUNTA QUE FALTAVA ===

O projeto tem controle positivo do JUIZ (`scripts/attest_harness.py`): prova que
o criterio detecta edge plantado e rejeita ruido, com n=120 sintetico. Isso
responde "o juiz funciona?".

Nao responde "com o n que vamos ter, o juiz CONSEGUE ver?". Sao coisas
diferentes, e a segunda decide como LER um veredito negativo:

  poder alto + "RUIDO"  ->  evidencia de AUSENCIA de efeito
  poder baixo + "RUIDO" ->  ausencia de EVIDENCIA. Nao diz nada.

Sem esse numero, um "RUIDO" e ambiguo do mesmo jeito que um NO-GO sobre dado
real e ambiguo entre "nao ha edge" e "o pipeline esta quebrado" — a ambiguidade
que o controle positivo existe para eliminar, so que no eixo do TAMANHO DA
AMOSTRA em vez do eixo da correcao do codigo.

=== POR QUE O n NOMINAL ENGANA AQUI ===

A coleta e diaria e o horizonte e D+7, entao previsoes consecutivas do mesmo
ativo compartilham 6 dos 7 dias de retorno. As observacoes nao sao
independentes: o n EFETIVO e bem menor que o n contado. O `block_length` do
bootstrap ja existe para absorver isso na estimativa do IC — mas ninguem tinha
medido o que sobra de PODER depois de absorver.

=== O QUE ESTE MODULO NAO FAZ ===

NAO altera nenhum gate. A H6 esta congelada por hash com `n >= 30`
pre-registrado; trocar esse numero DEPOIS de calcular poder seria ajuste
post-hoc de criterio — exatamente o que o pre-registro existe para impedir. O
uso correto deste modulo e QUALIFICAR a leitura do veredito, nunca reescrever a
regra que o produz.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from predictor_core.stats import spearman_block_ci

from GarimpoInvestimentos.analyzers.backtest import overlap_block_length

#: Simulacoes por celula. 400 da erro-padrao ~2,5pp numa taxa de 50% — suficiente
#: para distinguir "poder baixo" de "poder alto", que e a decisao em jogo.
DEFAULT_N_SIM = 400

#: Reamostragens do bootstrap. O default do `spearman_block_ci` e 10_000, o que
#: custa ~1,1s POR AVALIACAO — uma tabela de poder faz milhares delas, e a conta
#: passa de uma hora. Provavelmente e por isso que este numero nunca fora
#: calculado neste projeto.
#:
#: Aqui o default e menor DE PROPOSITO, e a troca e legitima porque o objeto de
#: medida e diferente: o gate oficial estima UM IC e quer precisao maxima nele;
#: a analise de poder estima uma TAXA sobre centenas de ICs, e o ruido de cada
#: um se dilui na media. Para reproduzir o gate exatamente, passe n_boot=10_000.
DEFAULT_N_BOOT = 1_000


@dataclass(frozen=True)
class PowerCell:
    n: int
    true_rho: float
    detection_rate: float
    n_sim: int

    @property
    def is_false_positive_cell(self) -> bool:
        return self.true_rho == 0.0

    @property
    def leitura(self) -> str:
        if self.is_false_positive_cell:
            return "taxa de falso positivo (nominal ~5%)"
        if self.detection_rate < 0.5:
            return "SUBDIMENSIONADO — 'RUIDO' aqui nao e evidencia de ausencia"
        if self.detection_rate < 0.8:
            return "marginal"
        return "adequado"


def overlapping_sample(
    n: int, true_rho: float, *, horizon: int, seed: int
) -> list[tuple[float, float]]:
    """Amostra com a estrutura REAL da coleta: previsoes diarias, janelas D+h
    sobrepostas.

    Retornos diarios iid; o retorno do horizonte e a soma dos `horizon` dias
    seguintes, entao observacoes consecutivas compartilham horizon-1 dias. O
    score e correlacionado com o retorno futuro na intensidade alvo. Gerar
    observacoes independentes aqui superestimaria o poder — e o erro seria
    justamente na direcao que interessa evitar.
    """
    rng = random.Random(seed)
    diarios = [rng.gauss(0.0, 1.0) for _ in range(n + horizon + 1)]
    pares = []
    for t in range(n):
        retorno = sum(diarios[t + 1 : t + 1 + horizon])
        sinal = retorno / (horizon**0.5)
        score = true_rho * sinal + ((1.0 - true_rho**2) ** 0.5) * rng.gauss(0.0, 1.0)
        pares.append((score, retorno))
    return pares


def detects(
    pares: list[tuple[float, float]], *, horizon: int, n_boot: int = DEFAULT_N_BOOT
) -> bool:
    """O criterio REAL do projeto: IC95 por block bootstrap que nao cruza zero.
    Reusar a funcao canonica e obrigatorio — medir o poder de uma copia
    amaciada nao diria nada sobre o gate de verdade. So o `n_boot` e reduzido,
    pelo motivo documentado em DEFAULT_N_BOOT."""
    rho, lo, hi = spearman_block_ci(
        pares, block_length=overlap_block_length(horizon), n_boot=n_boot
    )
    return rho is not None and lo is not None and hi is not None and (lo > 0 or hi < 0)


def power_at(
    n: int,
    true_rho: float,
    *,
    horizon: int = 7,
    n_sim: int = DEFAULT_N_SIM,
    n_boot: int = DEFAULT_N_BOOT,
    seed0: int = 0,
) -> PowerCell:
    detectados = sum(
        detects(
            overlapping_sample(n, true_rho, horizon=horizon, seed=seed0 + s),
            horizon=horizon,
            n_boot=n_boot,
        )
        for s in range(n_sim)
    )
    return PowerCell(n=n, true_rho=true_rho, detection_rate=detectados / n_sim, n_sim=n_sim)


def power_table(
    ns: tuple[int, ...] = (30, 50, 100, 200, 440),
    rhos: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3, 0.5),
    *,
    horizon: int = 7,
    n_sim: int = DEFAULT_N_SIM,
    n_boot: int = DEFAULT_N_BOOT,
) -> list[PowerCell]:
    return [power_at(n, r, horizon=horizon, n_sim=n_sim, n_boot=n_boot) for n in ns for r in rhos]


def render(celulas: list[PowerCell], *, horizon: int = 7) -> str:
    ns = sorted({c.n for c in celulas})
    rhos = sorted({c.true_rho for c in celulas})
    por = {(c.n, c.true_rho): c for c in celulas}
    linhas = [
        f"PODER DO GATE (D+{horizon}, block_length={overlap_block_length(horizon)}, "
        "criterio: IC95 nao cruza zero)",
        "",
        f"  {'n':>6} | " + " | ".join(f"rho={r:<4.1f}" for r in rhos),
        f"  {'-' * (9 + 11 * len(rhos))}",
    ]
    for n in ns:
        celulas_n = " | ".join(f"{por[(n, r)].detection_rate:>7.1%} " for r in rhos)
        linhas.append(f"  {n:>6} | {celulas_n}")
    linhas += [
        "",
        "  rho=0.0 e a taxa de FALSO POSITIVO (nominal ~5%).",
        "  As demais sao PODER: chance de VER um efeito que existe.",
        "",
        "  NAO altera gate nenhum. A H6 esta congelada com n>=30 pre-registrado;",
        "  mudar esse numero depois de calcular poder seria ajuste post-hoc.",
        "  Serve para LER o veredito: 'RUIDO' com poder baixo e ausencia de",
        "  evidencia, nao evidencia de ausencia.",
    ]
    return "\n".join(linhas)


def main() -> int:
    print(render(power_table()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
