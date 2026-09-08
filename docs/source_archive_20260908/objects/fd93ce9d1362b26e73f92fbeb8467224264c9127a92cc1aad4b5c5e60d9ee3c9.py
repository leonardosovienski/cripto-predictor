"""Guarda de sanidade numérica para os adaptadores de provider (interno, não é API pública).

`MarketDataPoint.__post_init__` (vendor) valida `high >= low`, mas essa comparação com
NaN é sempre False — um preço NaN passaria pela guarda "falha explícita" sem ser pego, e
corromperia silenciosamente `consensus_median`/`consensus_mean` (mediana/média com NaN
tem resultado indefinido, sem levantar exceção). JSON padrão não tem NaN, mas o parser
`json` do Python aceita os tokens literais NaN/Infinity/-Infinity se a API os emitir —
já visto em exchanges durante anomalias de mercado.

Corrigido aqui, na fronteira do provider (domínio, não vendor): um valor não-finito
levanta ValueError, que o Router já trata como falha normal desse provedor — a fonte
contaminada é excluída (fallback) ou some da lista de sobreviventes (consenso), em vez
de silenciosamente entrar na mediana.
"""

from __future__ import annotations

import math


def require_finite(value: float, *, field: str, provider: str, symbol: str) -> float:
    """Levanta ValueError se `value` não for finito (NaN/±Infinity); senão retorna igual."""
    if not math.isfinite(value):
        raise ValueError(
            f"{provider}: valor não-finito ({value!r}) no campo '{field}' de {symbol} "
            "— dado da fonte rejeitado (evita corromper silenciosamente a mediana)"
        )
    return value
