"""DSL de fatores point-in-time (pré-requisito (1) do B9 em docs/HYPOTHESES.md).

Existe para tornar possível o desenho em que o LLM propõe HIPÓTESES e um motor
determinístico as executa — em vez de o LLM ser ele próprio o preditor, como em
H4/H5/H6. O princípio que o DSL materializa: o agente escolhe a DIREÇÃO do
raciocínio; nunca o protocolo empírico.

GARANTIA CENTRAL — CAUSALIDADE POR CONSTRUÇÃO. Toda operação do vocabulário lê
exclusivamente índices <= t. Não existe operação que olhe para frente: não é que
elas sejam desencorajadas, é que não estão no vocabulário. Uma recipe é um dict
JSON validado contra uma whitelist, montado em árvore de expressão — nunca
`eval`/`exec`. Consequências:

  - uma recipe malformada falha na CONSTRUÇÃO, antes de tocar dado;
  - um operador desconhecido é erro explícito, não no-op silencioso;
  - o conjunto de recipes possíveis é enumerável e auditável, que é a condição
    para o registro append-only de hipóteses ter significado.

A garantia é PROVADA, não afirmada: `tests/test_factor_dsl.py` mutila o FUTURO
da série e exige que todo valor passado permaneça bit-idêntico — a mesma
contraprova de invariância usada na auditoria de look-ahead do HMM
(docs/AUDITORIA_HMM.md). Revisão de código não substitui esse teste.

Isto é INFRAESTRUTURA. Não é hipótese, não consome tentativa, não autoriza nada.
Promover a hipótese exige os quatro requisitos do B9.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

Serie = list[float | None]


class RecipeError(ValueError):
    """Recipe inválida. Sempre falha na construção, nunca em silêncio."""


@dataclass(frozen=True)
class Factor:
    """Nó da árvore. `op` vem da whitelist; `args` são nós ou escalares."""

    op: str
    args: tuple[Any, ...]


def feature(nome: str) -> Factor:
    return Factor("feature", (nome,))


def const(valor: float) -> Factor:
    return Factor("const", (float(valor),))


def lag(expr: Factor, k: int) -> Factor:
    if k < 1:
        raise RecipeError(f"lag exige k >= 1 (k=0 seria o proprio instante); recebido {k}")
    return Factor("lag", (expr, int(k)))


def rolling_mean(expr: Factor, janela: int) -> Factor:
    return Factor("rolling_mean", (expr, _janela(janela)))


def rolling_std(expr: Factor, janela: int) -> Factor:
    return Factor("rolling_std", (expr, _janela(janela)))


def zscore(expr: Factor, janela: int) -> Factor:
    return Factor("zscore", (expr, _janela(janela)))


def sign(expr: Factor) -> Factor:
    return Factor("sign", (expr,))


def add(a: Factor, b: Factor) -> Factor:
    return Factor("add", (a, b))


def sub(a: Factor, b: Factor) -> Factor:
    return Factor("sub", (a, b))


def mul(a: Factor, b: Factor) -> Factor:
    return Factor("mul", (a, b))


def div(a: Factor, b: Factor) -> Factor:
    return Factor("div", (a, b))


def _janela(janela: int) -> int:
    if janela < 2:
        raise RecipeError(f"janela deve ser >= 2; recebido {janela}")
    return int(janela)


# Whitelist: (n_args, construtor). Fora daqui não existe operação.
_BUILDERS = {
    "feature": (1, lambda a: feature(a[0])),
    "const": (1, lambda a: const(a[0])),
    "lag": (2, lambda a: lag(a[0], a[1])),
    "rolling_mean": (2, lambda a: rolling_mean(a[0], a[1])),
    "rolling_std": (2, lambda a: rolling_std(a[0], a[1])),
    "zscore": (2, lambda a: zscore(a[0], a[1])),
    "sign": (1, lambda a: sign(a[0])),
    "add": (2, lambda a: add(a[0], a[1])),
    "sub": (2, lambda a: sub(a[0], a[1])),
    "mul": (2, lambda a: mul(a[0], a[1])),
    "div": (2, lambda a: div(a[0], a[1])),
}


def from_recipe(recipe: dict) -> Factor:
    """Constrói a árvore a partir do dict JSON. Sem eval: cada `op` é resolvida
    contra a whitelist e cada aridade é conferida."""
    if not isinstance(recipe, dict):
        raise RecipeError(f"recipe deve ser um objeto JSON; recebido {type(recipe).__name__}")
    op = recipe.get("op")
    if op not in _BUILDERS:
        raise RecipeError(f"operacao desconhecida: {op!r}. Permitidas: {sorted(_BUILDERS)}")
    args = recipe.get("args", [])
    if not isinstance(args, list):
        raise RecipeError(f"args de {op!r} deve ser lista; recebido {type(args).__name__}")
    esperado, builder = _BUILDERS[op]
    if len(args) != esperado:
        raise RecipeError(f"{op!r} espera {esperado} argumento(s); recebeu {len(args)}")
    resolvidos = [from_recipe(a) if isinstance(a, dict) else a for a in args]
    return builder(resolvidos)


def to_recipe(f: Factor) -> dict:
    """Serializa de volta. Roundtrip estável é o que permite guardar a hipótese
    no registro append-only e reconstruí-la exatamente depois."""
    return {
        "op": f.op,
        "args": [to_recipe(a) if isinstance(a, Factor) else a for a in f.args],
    }


def _finito(x: float | None) -> bool:
    return x is not None and math.isfinite(x)


def evaluate(f: Factor, dados: dict[str, Serie]) -> Serie:
    """Avalia o fator sobre séries alinhadas por índice temporal crescente.

    `None` propaga como ausência (não como zero): o Alignment Engine da DPL já
    usa NULL == NaN para stale/ausente, e converter para zero aqui inventaria
    observação que não existe.
    """
    if f.op == "feature":
        nome = f.args[0]
        if nome not in dados:
            raise RecipeError(f"feature ausente nos dados: {nome!r}. Disponiveis: {sorted(dados)}")
        return list(dados[nome])

    if f.op == "const":
        n = len(next(iter(dados.values()))) if dados else 0
        return [float(f.args[0])] * n

    if f.op == "lag":
        base = evaluate(f.args[0], dados)
        k = f.args[1]
        # Só olha para TRÁS. Os k primeiros não têm passado suficiente -> None.
        return [None] * k + base[: len(base) - k]

    if f.op in {"rolling_mean", "rolling_std", "zscore"}:
        base = evaluate(f.args[0], dados)
        janela = f.args[1]
        saida: Serie = []
        for i in range(len(base)):
            # Janela FECHADA em i: [i-janela+1, i]. Nunca i+1.
            if i + 1 < janela:
                saida.append(None)
                continue
            bloco = [x for x in base[i - janela + 1 : i + 1] if _finito(x)]
            if len(bloco) < janela:
                saida.append(None)
                continue
            media = sum(bloco) / janela
            if f.op == "rolling_mean":
                saida.append(media)
                continue
            var = sum((x - media) ** 2 for x in bloco) / (janela - 1)
            desvio = math.sqrt(var)
            if f.op == "rolling_std":
                saida.append(desvio)
            else:
                saida.append(None if desvio == 0 else (base[i] - media) / desvio)
        return saida

    if f.op == "sign":
        base = evaluate(f.args[0], dados)
        return [
            None if not _finito(x) else (1.0 if x > 0 else (-1.0 if x < 0 else 0.0)) for x in base
        ]

    esquerda = evaluate(f.args[0], dados)
    direita = evaluate(f.args[1], dados)
    saida = []
    for a, b in zip(esquerda, direita, strict=True):
        if not _finito(a) or not _finito(b):
            saida.append(None)
        elif f.op == "add":
            saida.append(a + b)
        elif f.op == "sub":
            saida.append(a - b)
        elif f.op == "mul":
            saida.append(a * b)
        else:
            saida.append(None if b == 0 else a / b)
    return saida


def warmup(f: Factor) -> int:
    """Quantas observações iniciais o fator NÃO consegue produzir. Serve para
    cortar o começo da série antes de avaliar edge — contar `None` de warmup
    como observação seria inflar o n."""
    if f.op in {"feature", "const"}:
        return 0
    if f.op == "lag":
        return warmup(f.args[0]) + f.args[1]
    if f.op in {"rolling_mean", "rolling_std", "zscore"}:
        return warmup(f.args[0]) + f.args[1] - 1
    if f.op == "sign":
        return warmup(f.args[0])
    return max(warmup(f.args[0]), warmup(f.args[1]))


__all__ = [
    "Factor",
    "RecipeError",
    "add",
    "const",
    "div",
    "evaluate",
    "feature",
    "from_recipe",
    "lag",
    "mul",
    "rolling_mean",
    "rolling_std",
    "sign",
    "sub",
    "to_recipe",
    "warmup",
    "zscore",
]
