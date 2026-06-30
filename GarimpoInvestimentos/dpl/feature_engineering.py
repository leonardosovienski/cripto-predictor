"""Feature engineering — deriva features do OHLCV bruto (sem alargar o contrato).

O `MarketDataPoint` permanece a fotografia mínima do candle. Os campos que o domínio
consome além do OHLCV (change_24h/7d/30d, volume, indicadores técnicos) são FEATURES
DERIVADAS, calculadas aqui a partir dos candles e materializadas em `features_aligned`
durante a ingestão. Assim o preço bruto e as features derivadas coexistem sem misturar
responsabilidades (ver docs/DOSSIE_PLATAFORMA.md, decisão sobre Variância Zero).
"""
from __future__ import annotations

import math

from GarimpoInvestimentos.analyzers.indicators import compute_indicators
from GarimpoInvestimentos.dpl.contracts import MarketDataPoint

# Chaves produzidas por compute_indicators — usadas no serving para separar os
# indicadores (sub-dict "indicadores") das demais features de topo.
INDICATOR_KEYS = frozenset({
    "rsi_14", "sma_50", "preco_vs_sma50_pct", "sma_200", "preco_vs_sma200_pct",
    "macd", "macd_signal", "macd_histogram", "bollinger_pct_b",
})
# Features de baixa frequência alinhadas (não-derivadas) que não entram no hard_data
# de mercado — ficam disponíveis separadamente (ex.: sentimento).
_SIGNAL_KEYS = frozenset({"fear_greed"})


def _change_pct(closes: list[float], n: int) -> float | None:
    """Variação % entre o último close e o de n períodos atrás."""
    if len(closes) <= n or closes[-1 - n] == 0:
        return None
    return round((closes[-1] / closes[-1 - n] - 1) * 100, 2)


def derive_features(candles: list[MarketDataPoint]) -> dict:
    """Calcula as features derivadas para o ÚLTIMO candle da série diária.

    Retorna um dict {feature: valor} pronto para materialização. Inclui:
      - price_usd, volume_usd (do último candle)
      - change_24h / change_7d / change_30d (calculados dos closes diários)
      - indicadores técnicos (rsi_14, sma_50/200, macd*, bollinger_pct_b)
    Features que não puderam ser calculadas (série curta) simplesmente não aparecem.
    """
    if not candles:
        return {}
    ordered = sorted(candles, key=lambda c: c.timestamp)
    closes = [c.close for c in ordered]
    last = ordered[-1]

    feats: dict[str, float] = {
        "price_usd": last.close,
        "volume_usd": last.volume,
    }
    for label, n in (("change_24h", 1), ("change_7d", 7), ("change_30d", 30)):
        v = _change_pct(closes, n)
        if v is not None:
            feats[label] = v

    feats.update(compute_indicators(closes))
    return feats


def to_hard_data(flat: dict) -> dict:
    """Reconstrói a estrutura que o pipeline consome a partir da linha LARGA servida.

    A Feature Store devolve um dict plano {feature: valor}; o domínio espera os
    campos de mercado no topo e os indicadores aninhados em "indicadores" (formato
    histórico do hard_data). Valores NaN (features ausentes/stale) são descartados.
    """
    indicadores: dict = {}
    hard: dict = {}
    for k, v in flat.items():
        if k == "ts" or k in _SIGNAL_KEYS:
            continue
        if isinstance(v, float) and math.isnan(v):
            continue
        if k in INDICATOR_KEYS:
            indicadores[k] = v
        else:
            hard[k] = v
    if indicadores:
        hard["indicadores"] = indicadores
    return hard
