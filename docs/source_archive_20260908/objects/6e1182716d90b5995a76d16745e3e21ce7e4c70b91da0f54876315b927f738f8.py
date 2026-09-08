"""Testes da Fase 3 — agregação (mediana/TWAP), AggregationRouter e Circuit Breaker.

Offline e determinístico: provedores fake, relógio injetado no breaker.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from predictor_core.obs import read_events

from GarimpoInvestimentos.dpl import (
    AggregationRouter,
    CircuitBreaker,
    DataProvider,
    DataUnavailableError,
    MarketDataPoint,
    consensus_median,
    twap,
)
from GarimpoInvestimentos.dpl.circuit_breaker import CLOSED, HALF_OPEN, OPEN

UTC = UTC


def _pt(day: int, close: float, source: str, vol: float = 10.0) -> MarketDataPoint:
    ts = datetime(2026, 1, day, tzinfo=UTC)
    return MarketDataPoint(
        symbol="bitcoin",
        timestamp=ts,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=vol,
        source=source,
        interval="1d",
        published_at=ts,
    )


class _Ok(DataProvider):
    def __init__(self, name, closes):
        self.name = name
        self._closes = closes  # {day: close}

    async def fetch_ohlcv(self, symbol, interval="1d", limit=1):
        return [_pt(d, c, self.name) for d, c in self._closes.items()]

    async def health_check(self):
        return True


class _Fail(DataProvider):
    def __init__(self, name):
        self.name = name

    async def fetch_ohlcv(self, symbol, interval="1d", limit=1):
        raise RuntimeError("down")

    async def health_check(self):
        return False


# --- Agregação pura ----------------------------------------------------------


def test_consensus_median_funde_por_timestamp():
    a = [_pt(1, 100, "binance"), _pt(2, 200, "binance")]
    b = [_pt(1, 110, "kraken"), _pt(2, 190, "kraken")]
    c = [_pt(1, 105, "x"), _pt(2, 300, "x")]  # 300 é outlier no dia 2
    fused = consensus_median([a, b, c])
    assert fused[0].close == 105  # mediana(100,110,105)
    assert fused[1].close == 200  # mediana(200,190,300) ignora o outlier
    assert fused[0].source == "consensus_median"


def test_consensus_median_published_at_eh_o_maximo():
    p1 = _pt(1, 100, "binance")
    p2 = MarketDataPoint(
        symbol="bitcoin",
        timestamp=p1.timestamp,
        open=100,
        high=101,
        low=99,
        close=110,
        volume=5,
        source="kraken",
        interval="1d",
        published_at=p1.timestamp + timedelta(hours=2),
    )
    fused = consensus_median([[p1], [p2]])
    # consolidado só disponível quando a ÚLTIMA fonte publicou (anti-lookahead)
    assert fused[0].published_at == p1.timestamp + timedelta(hours=2)


def test_twap_serie_uniforme_eh_media():
    pts = [_pt(1, 100, "x"), _pt(2, 200, "x"), _pt(3, 300, "x")]
    assert twap(pts) == 200.0


# --- AggregationRouter -------------------------------------------------------


def test_aggregation_router_funde_sobreviventes(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(tmp_path / "ev.jsonl"))
    r = AggregationRouter(
        [_Ok("binance", {1: 100}), _Ok("kraken", {1: 120})], policy="consensus_median"
    )
    out = asyncio.run(r.fetch_ohlcv("bitcoin"))
    assert out[0].close == 110  # mediana de 2 = média
    eventos = [e["event"] for e in read_events(tmp_path / "ev.jsonl")]
    assert "data.aggregated" in eventos


def test_aggregation_router_tolera_falha_parcial(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(tmp_path / "ev.jsonl"))
    r = AggregationRouter([_Ok("binance", {1: 100}), _Fail("kraken")], policy="consensus_median")
    out = asyncio.run(r.fetch_ohlcv("bitcoin"))
    assert out[0].close == 100  # funde só o sobrevivente


def test_aggregation_router_todas_falham_levanta():
    r = AggregationRouter([_Fail("a"), _Fail("b")], policy="consensus_median")
    with pytest.raises(DataUnavailableError):
        asyncio.run(r.fetch_ohlcv("bitcoin"))


def test_aggregation_router_rejeita_politica_invalida():
    with pytest.raises(ValueError):
        AggregationRouter([_Ok("a", {1: 1})], policy="inexistente")


# --- Circuit Breaker ---------------------------------------------------------


def test_breaker_abre_apos_limiar(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(tmp_path / "ev.jsonl"))
    cb = CircuitBreaker("binance", failure_threshold=3, reset_timeout=60)
    assert cb.state == CLOSED and cb.allow()
    for _ in range(3):
        cb.record_failure()
    assert cb.state == OPEN and not cb.allow()


def test_breaker_meio_aberto_apos_timeout_e_fecha_no_sucesso():
    now = {"t": 1000.0}
    cb = CircuitBreaker("binance", failure_threshold=2, reset_timeout=30, clock=lambda: now["t"])
    cb.record_failure()
    cb.record_failure()
    assert cb.state == OPEN
    now["t"] += 31  # passou o timeout
    # CB unificado (Onda 3): state é getter PURO; allow() dispara OPEN→HALF_OPEN.
    assert cb.allow() and cb.state == HALF_OPEN  # allow() libera a sondagem e transiciona
    cb.record_success()
    assert cb.state == CLOSED


def test_breaker_reabre_se_sondagem_falha():
    now = {"t": 0.0}
    cb = CircuitBreaker("binance", failure_threshold=1, reset_timeout=10, clock=lambda: now["t"])
    cb.record_failure()
    assert cb.state == OPEN
    now["t"] += 11
    assert cb.allow() and cb.state == HALF_OPEN  # allow() dispara OPEN→HALF_OPEN
    cb.record_failure()  # falhou a sondagem
    assert cb.state == OPEN
