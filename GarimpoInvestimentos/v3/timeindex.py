"""Lookup de vizinho temporal mais próximo — helper único (C5, auditoria 2026-07-09).

Antes desta extração a MESMA lógica ("valor no timestamp exato, senão o mais
próximo dentro de ±tolerância") existia em 3 cópias — backtest_v3._find_spot_return,
paper_trader._ref_price e paper_report._closest_price — todas O(n) no miss
(varriam o dict inteiro). Aqui é bisect sobre chaves ordenadas: O(log n) por
consulta, com o índice ordenado construído uma vez por dict (cache por id()
seria frágil; o chamador que consulta em loop deve usar SortedTimeIndex).

Candidato a promoção futura pro predictor_core (plano de convergência da
auditoria: predictor_core/timeindex.py) — a evolução do core é upstream via
sync_core, nunca editando o vendor; até lá o helper vive no pacote v3.
"""

from bisect import bisect_left

_DEFAULT_TOLERANCE_MS = 300_000  # ±5 min — a tolerância histórica das 3 cópias


class SortedTimeIndex:
    """Índice imutável timestamp→valor com busca O(log n) do vizinho mais próximo."""

    def __init__(self, index: dict[int, float]) -> None:
        self._keys = sorted(index)
        self._index = index

    def nearest(self, ts: int, tolerance_ms: int = _DEFAULT_TOLERANCE_MS) -> float | None:
        """Valor no timestamp mais próximo de `ts` dentro de ±tolerance_ms;
        None se nenhum candidato na janela. Empate exato de distância: fica o
        anterior (determinístico; as 3 cópias antigas dependiam da ordem do
        dict e eram, na prática, também 'o primeiro visto')."""
        if not self._keys:
            return None
        v = self._index.get(ts)
        if v is not None:
            return v
        i = bisect_left(self._keys, ts)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(self._keys):
                k = self._keys[j]
                d = abs(k - ts)
                if d <= tolerance_ms and (best is None or d < best[0]):
                    best = (d, k)
        return self._index[best[1]] if best else None


def nearest_value(
    index: dict[int, float], ts: int, tolerance_ms: int = _DEFAULT_TOLERANCE_MS
) -> float | None:
    """Conveniência para consulta única. Em loops, construa SortedTimeIndex
    uma vez (o sort é O(n log n) por chamada aqui)."""
    return SortedTimeIndex(index).nearest(ts, tolerance_ms)
