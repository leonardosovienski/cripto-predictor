"""Alignment Engine — funde séries de granularidades diferentes sem lookahead.

Regra dupla (ver docs/DOSSIE_PLATAFORMA.md, ADR-003):
  - ELEGIBILIDADE (anti-lookahead): um sinal só pode entrar num candle se já era
    público naquele instante — `signal.published_at <= candle.timestamp`. Usa o
    instante de PUBLICAÇÃO, não o do dado.
  - FRESCOR (max_staleness): mesmo elegível, se o sinal for velho demais
    (`candle.timestamp - signal.timestamp > max_staleness`) injeta-se NaN em vez de
    repetir um valor obsoleto (forward fill honesto). Mede pelo instante do DADO.

A DPL entrega o dado bruto com forward fill / NaN; a engenharia de features
derivadas (deltas, z-scores — tratamento da Variância Zero) é do domínio.
"""

from __future__ import annotations

import bisect
from datetime import timedelta

from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.signals import SignalPoint

NaN = float("nan")


def _asof_value(
    signals_sorted: list[SignalPoint], pub_keys: list, candle_ts, max_staleness: timedelta | None
):
    """Último sinal cujo published_at <= candle_ts (forward fill anti-lookahead).
    Retorna NaN se não houver elegível ou se o dado estiver stale.
    """
    # idx = nº de sinais já publicados em candle_ts (pub_keys ordenado por published_at)
    idx = bisect.bisect_right(pub_keys, candle_ts)
    if idx == 0:
        return NaN  # nada era público ainda
    sig = signals_sorted[idx - 1]
    if max_staleness is not None and (candle_ts - sig.timestamp) > max_staleness:
        return NaN  # elegível, mas velho demais → não inventa valor
    return sig.value


def _available_at(signal: SignalPoint):
    """Conservative knowledge time for revisions/backfills.

    A revision cannot be used before it was ingested/collected, even when a
    provider backdates ``published_at`` to the original release estimate.
    """
    candidates = [signal.published_at]
    if signal.vintage is not None:
        candidates.append(signal.vintage)
    if signal.ingested_at is not None:
        candidates.append(signal.ingested_at)
    return max(candidates)


class AlignmentEngine:
    """Materializa a matriz alinhada a partir de candles + sinais de baixa freq."""

    def align(
        self,
        candles: list[MarketDataPoint],
        signals: dict[str, list[SignalPoint]] | None = None,
        max_staleness: dict[str, timedelta] | None = None,
    ) -> list[dict]:
        """Retorna linhas {ts, close, volume, <signal_name>: value|NaN}, ordenadas.

        `candles` define a grade temporal (eixo). Cada sinal é alinhado por as-of
        join em published_at. `max_staleness[name]` controla o frescor por sinal.
        """
        signals = signals or {}
        max_staleness = max_staleness or {}

        # Use effective knowledge time, not only nominal publication time.
        prepared: dict[str, tuple[list[SignalPoint], list]] = {}
        for name, series in signals.items():
            s = sorted(series, key=_available_at)
            prepared[name] = (s, [_available_at(x) for x in s])

        rows = []
        for candle in sorted(candles, key=lambda c: c.timestamp):
            row = {
                "ts": candle.timestamp,
                "close": candle.close,
                "volume": candle.volume,
            }
            for name, (s_sorted, pub_keys) in prepared.items():
                row[name] = _asof_value(
                    s_sorted, pub_keys, candle.timestamp, max_staleness.get(name)
                )
            rows.append(row)
        return rows
