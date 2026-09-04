"""H9 (OI/volume, docs/HYPOTHESES.md): covariável extra para o RegimeEngine —
mesmo mecanismo de `extra_features` que o H7 (macro/DXY) já usa.

`build_oi_volume_ratio` — razão OI notional / volume notional (ambos em USD),
ponto-a-ponto, alinhada a uma lista de FeatureVector. Mede crowding
especulativo: quanto do interesse aberto é sustentado por giro real de
negociação, vs. posição alavancada acumulada sem giro correspondente.
Ortogonal ao que H1-H3 usam (nível/z-score do funding rate) — ver H9 em
docs/HYPOTHESES.md para o mecanismo causal completo.

Dado 100% já coletado: `oi_notional_usd` já está em FeatureVector (usado por
H1-H3); `volume` (spot, unidade do ativo-base) já é coletado por
spot_collector.py mas nunca tinha sido consumido. Convertido para notional USD
aqui (`volume * spot_close`, mesmo close já presente no FeatureVector — sem
lookahead, é o candle do próprio ponto). Zero coleta prospectiva nova.
"""

from __future__ import annotations

import math

from GarimpoInvestimentos.v3.feature_builder import FeatureVector, _find_asof


def build_oi_volume_ratio(
    feature_vectors: list[FeatureVector],
    volume_index: dict[int, float],
    *,
    join_tolerance_ms: int = 5 * 60 * 1000,
) -> list[float]:
    """log(OI_notional_usd / volume_notional_usd) por ponto — log para
    estabilidade de escala (mesma razão de log_return_8h/oi_log_delta já
    existentes em FeatureVector). Ponto sem volume alinhado disponível
    (tolerância `join_tolerance_ms`, mesma janela de `_find_asof` do
    feature_builder) recebe 0.0 — decisão CONSERVADORA (covariável neutra),
    não erro silencioso: confira a cobertura de `volume_index` antes de
    treinar."""
    if join_tolerance_ms < 0:
        raise ValueError("join_tolerance_ms não pode ser negativo")
    out = []
    for fv in feature_vectors:
        vol_base = _find_asof(fv.timestamp_exchange_ms, volume_index, join_tolerance_ms)
        if vol_base is None or vol_base <= 0.0 or fv.spot_close <= 0.0 or fv.oi_notional_usd <= 0.0:
            out.append(0.0)
            continue
        volume_notional_usd = vol_base * fv.spot_close
        out.append(_safe_log_ratio(fv.oi_notional_usd, volume_notional_usd))
    return out


def _safe_log_ratio(numerator: float, denominator: float) -> float:
    if numerator <= 0.0 or denominator <= 0.0:
        return 0.0
    return math.log(numerator / denominator)


__all__ = ["build_oi_volume_ratio"]
