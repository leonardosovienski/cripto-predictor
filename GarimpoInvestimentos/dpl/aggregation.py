"""Agregação de múltiplas fontes — fusão ponto-a-ponto e TWAP.

Consolidar o mesmo dado de várias exchanges imuniza o sinal contra anomalias de uma
única corretora (ver docs/DOSSIE_PLATAFORMA.md, decisão sobre agregação). Funções
puras e determinísticas — testáveis sem rede.
"""
from __future__ import annotations

import statistics
from datetime import timezone

from GarimpoInvestimentos.dpl.contracts import MarketDataPoint

_FIELDS = ("open", "high", "low", "close", "volume")


def _fuse_per_timestamp(series_by_source: list[list[MarketDataPoint]],
                        reducer, source_label: str) -> list[MarketDataPoint]:
    """Agrupa candles de várias fontes por timestamp e funde cada campo com `reducer`.

    Só consolida timestamps presentes em ao menos uma fonte; cada campo é reduzido
    sobre as fontes que têm aquele timestamp. published_at = max (o consolidado só
    fica disponível quando a última fonte publicou) → preserva anti-lookahead.
    """
    buckets: dict = {}
    for series in series_by_source:
        for p in series:
            buckets.setdefault(p.timestamp, []).append(p)
    out = []
    for ts in sorted(buckets):
        pts = buckets[ts]
        fused = {f: reducer([getattr(p, f) for p in pts]) for f in _FIELDS}
        out.append(MarketDataPoint(
            symbol=pts[0].symbol, timestamp=ts,
            open=fused["open"], high=fused["high"], low=fused["low"],
            close=fused["close"], volume=fused["volume"],
            source=source_label, interval=pts[0].interval,
            published_at=max(p.published_at for p in pts),
        ))
    return out


def consensus_median(series_by_source: list[list[MarketDataPoint]]) -> list[MarketDataPoint]:
    """Mediana ponto-a-ponto entre fontes (robusta a outlier de uma exchange)."""
    return _fuse_per_timestamp(series_by_source, statistics.median, "consensus_median")


def consensus_mean(series_by_source: list[list[MarketDataPoint]]) -> list[MarketDataPoint]:
    """Média ponto-a-ponto entre fontes."""
    return _fuse_per_timestamp(series_by_source, statistics.fmean, "consensus_mean")


def twap(points: list[MarketDataPoint]) -> float:
    """Time-Weighted Average Price de uma série: média dos closes ponderada pelo
    intervalo de tempo que cada candle representa (Σ close·Δt / Σ Δt).

    Suaviza o ruído de uma única vela. Para uma série de grade uniforme equivale à
    média simples dos closes; com lacunas, candles que cobrem mais tempo pesam mais.
    """
    if not points:
        raise ValueError("twap: série vazia")
    ordered = sorted(points, key=lambda p: p.timestamp)
    if len(ordered) == 1:
        return ordered[0].close
    num = den = 0.0
    for i, p in enumerate(ordered):
        if i < len(ordered) - 1:
            dt = (ordered[i + 1].timestamp - p.timestamp).total_seconds()
        else:
            # último candle: usa o Δt médio anterior como peso (evita peso zero)
            dt = (ordered[i].timestamp - ordered[i - 1].timestamp).total_seconds()
        num += p.close * dt
        den += dt
    return num / den if den else ordered[-1].close
