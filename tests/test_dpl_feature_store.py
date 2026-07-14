"""Testes da Fase 2 — Feature Store, Alignment Engine e ingestão.

Offline e determinístico: SQLite em arquivo temporário, séries sintéticas. O foco é
a integridade temporal (zero lookahead) e a injeção de NaN por staleness — as duas
garantias que justificam o Alignment Engine centralizado.
"""
import asyncio
import math
from datetime import datetime, timedelta, timezone

import pytest

from GarimpoInvestimentos.dpl import (
    AlignmentEngine,
    FeatureStore,
    MarketDataPoint,
    SignalPoint,
)

UTC = timezone.utc


def _candle(day: int, close: float) -> MarketDataPoint:
    ts = datetime(2026, 1, day, tzinfo=UTC)
    return MarketDataPoint(
        symbol="bitcoin", timestamp=ts, open=close, high=close + 1, low=close - 1,
        close=close, volume=100.0, source="binance", interval="1d", published_at=ts,
    )


def _signal(day: int, value: float, *, published_day: int | None = None) -> SignalPoint:
    ts = datetime(2026, 1, day, tzinfo=UTC)
    pub = datetime(2026, 1, published_day or day, tzinfo=UTC)
    return SignalPoint(name="fear_greed", timestamp=ts, value=value,
                       source="alternative.me", published_at=pub)


# --- Alignment Engine: anti-lookahead ---------------------------------------

def test_align_forward_fill_basico():
    candles = [_candle(1, 100), _candle(2, 110), _candle(3, 120)]
    signals = {"fear_greed": [_signal(1, 30.0), _signal(3, 70.0)]}
    rows = AlignmentEngine().align(candles, signals)
    # dia 1: 30; dia 2: forward fill de 30 (sinal do dia 2 não existe); dia 3: 70
    assert rows[0]["fear_greed"] == 30.0
    assert rows[1]["fear_greed"] == 30.0
    assert rows[2]["fear_greed"] == 70.0


def test_align_nao_usa_sinal_publicado_no_futuro():
    """Lookahead: sinal com timestamp do dia 1 mas PUBLICADO só no dia 3 não pode
    vazar para os candles dos dias 1 e 2."""
    candles = [_candle(1, 100), _candle(2, 110), _candle(3, 120)]
    # sinal "vale" para o dia 1, mas só ficou público no dia 3
    signals = {"fear_greed": [_signal(1, 99.0, published_day=3)]}
    rows = AlignmentEngine().align(candles, signals)
    assert math.isnan(rows[0]["fear_greed"])  # nada público ainda
    assert math.isnan(rows[1]["fear_greed"])
    assert rows[2]["fear_greed"] == 99.0      # liberado no dia 3


def test_align_injeta_nan_quando_stale():
    """max_staleness: sinal elegível mas velho demais vira NaN, não forward fill."""
    candles = [_candle(1, 100), _candle(5, 140)]
    signals = {"fear_greed": [_signal(1, 50.0)]}
    rows = AlignmentEngine().align(
        candles, signals, max_staleness={"fear_greed": timedelta(days=2)}
    )
    assert rows[0]["fear_greed"] == 50.0       # fresco
    assert math.isnan(rows[1]["fear_greed"])   # 4 dias > 2 dias → NaN


def test_align_sem_sinais_so_preco():
    rows = AlignmentEngine().align([_candle(1, 100)])
    assert rows[0]["close"] == 100 and "fear_greed" not in rows[0]


# --- Feature Store: ingestão e serving ---------------------------------------

def test_feature_store_write_read_raw(tmp_path):
    with FeatureStore(tmp_path / "fs.db") as fs:
        fs.write_raw([_candle(1, 100), _candle(2, 110)])
        out = fs.read_raw("bitcoin", "1d")
    assert [p.close for p in out] == [100, 110]
    assert all(p.source == "binance" for p in out)


def test_feature_store_write_raw_idempotente(tmp_path):
    c = _candle(1, 100)
    with FeatureStore(tmp_path / "fs.db") as fs:
        fs.write_raw([c])
        fs.write_raw([c])  # mesma PK → upsert, não duplica
        assert len(fs.read_raw("bitcoin", "1d")) == 1


def test_feature_store_features_nan_roundtrip(tmp_path):
    """NaN materializado vira NULL e volta como NaN no serving."""
    rows = [{"ts": datetime(2026, 1, 1, tzinfo=UTC), "close": 100.0,
             "fear_greed": float("nan")}]
    with FeatureStore(tmp_path / "fs.db") as fs:
        fs.write_features("bitcoin", "1d", rows)
        out = fs.read_features("bitcoin", "1d")
    assert out[0]["close"] == 100.0
    assert math.isnan(out[0]["fear_greed"])


# --- Ingestão: separação ingestão/serving ------------------------------------

def test_ingest_materializa_e_serve(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(tmp_path / "ev.jsonl"))
    from GarimpoInvestimentos.dpl.ingest import ingest_crypto
    from GarimpoInvestimentos.dpl import (
        CryptoDataProvider, DataProvider, FallbackRouter, SignalProvider)

    class _FakePrice(DataProvider):
        name = "binance"
        async def fetch_ohlcv(self, symbol, interval="1d", limit=1):
            return [_candle(1, 100), _candle(2, 110)]
        async def health_check(self):
            return True

    class _FakeFG(SignalProvider):
        name = "fear_greed"
        async def fetch(self, limit=30):
            return [_signal(1, 40.0)]

    facade = CryptoDataProvider(router=FallbackRouter([_FakePrice()]))
    with FeatureStore(tmp_path / "fs.db") as fs:
        aligned = asyncio.run(ingest_crypto(
            fs, facade, "bitcoin", interval="1d", limit=2,
            signal_providers=[_FakeFG()],
        ))
        served = fs.read_features("bitcoin", "1d")
    assert len(aligned) == 2
    assert served[0]["fear_greed"] == 40.0
    assert served[1]["fear_greed"] == 40.0  # forward fill
