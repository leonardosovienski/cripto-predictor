"""Weekend-only calendar arithmetic; does not establish publication availability.

A fixed business-day lag ignores holidays, release hours and revised vintages.
Use documented publication timestamps for causal historical research.
"""

from __future__ import annotations

from datetime import date, timedelta

__all__ = ["add_business_days", "published_at"]


def add_business_days[D: date](day: D, n: int) -> D:
    """Soma `n` dias ÚTEIS a `day`, pulando sábado/domingo. `n` deve ser >= 0.

    Genérica sobre `date`/`datetime` de propósito: o provider trabalha com
    `datetime` (carimba `published_at`) e as features do V3 trabalham com
    `date`. Uma implementação, os dois usos — `timedelta` preserva o tipo.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n não pode ser negativo")
    d = day
    added = 0
    while added < n:
        d = d + timedelta(days=1)
        if d.weekday() < 5:  # 0=segunda ... 4=sexta
            added += 1
    return d


def published_at[D: date](observation_day: D, lag_business_days: int) -> D:
    """Momento a partir do qual uma observação datada em `observation_day` pode
    ser considerada CONHECIDA, dada uma defasagem em dias úteis.

    É o predicado anti-look-ahead na sua forma direta: uma observação só é
    usável num ponto `t` quando `published_at(obs_day, lag) <= t`. Preferir isto
    a calcular um "cutoff" para trás — subtrair dias corridos de `t` e comparar
    com a data da observação NÃO é equivalente e foi exatamente o erro corrigido
    em 2026-09-05.
    """
    return add_business_days(observation_day, lag_business_days)
