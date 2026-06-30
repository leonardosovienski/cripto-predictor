"""Testes do feature engineering e do serving (Fase 2 — wiring do main.py).

Validam que features derivadas (change_*, indicadores) saem do OHLCV bruto sem
alargar o MarketDataPoint, e que o serving reconstrói o hard_data que o pipeline
consome (price/change no topo, indicadores aninhados).
"""
from datetime import datetime, timezone

from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.feature_engineering import derive_features, to_hard_data

UTC = timezone.utc


def _series(closes: list[float]) -> list[MarketDataPoint]:
    pts = []
    for i, c in enumerate(closes, start=1):
        ts = datetime(2026, 1, 1, tzinfo=UTC).replace(day=min(i, 28))
        pts.append(MarketDataPoint(
            symbol="bitcoin", timestamp=ts, open=c, high=c, low=c, close=c,
            volume=float(i), source="coingecko", interval="1d", published_at=ts,
        ))
    return pts


def test_derive_change_24h():
    feats = derive_features(_series([100.0, 110.0]))
    assert feats["price_usd"] == 110.0
    assert feats["change_24h"] == 10.0  # +10%


def test_derive_inclui_indicadores_com_serie_longa():
    feats = derive_features(_series([float(100 + i) for i in range(60)]))
    assert "rsi_14" in feats and "sma_50" in feats
    assert "change_30d" in feats


def test_derive_serie_curta_sem_indicadores_longos():
    feats = derive_features(_series([100.0, 101.0, 102.0]))
    assert "sma_50" not in feats  # série curta demais
    assert "change_7d" not in feats


def test_to_hard_data_separa_indicadores():
    flat = {
        "ts": datetime(2026, 1, 1, tzinfo=UTC),
        "price_usd": 100.0, "volume_usd": 5.0, "change_24h": 2.0,
        "rsi_14": 55.0, "sma_200": 90.0, "preco_vs_sma200_pct": 11.1,
        "fear_greed": 40.0,
    }
    hard = to_hard_data(flat)
    assert hard["price_usd"] == 100.0 and hard["change_24h"] == 2.0
    assert hard["indicadores"]["rsi_14"] == 55.0
    assert "fear_greed" not in hard and "ts" not in hard  # sinal e ts não vão pro hard_data


def test_to_hard_data_descarta_nan():
    flat = {"ts": datetime(2026, 1, 1, tzinfo=UTC), "price_usd": 100.0,
            "change_7d": float("nan")}
    hard = to_hard_data(flat)
    assert "change_7d" not in hard  # NaN não polui o prompt
