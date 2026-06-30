"""Testes da Data Provider Layer (Fase 1) — contrato, fallback e integridade temporal.

Offline: provedores são fakes injetados no Router/fachada; nenhum acessa rede ou
ccxt. Telemetria é redirecionada para um JSONL temporário via PREDICTOR_EVENTS_PATH.
Async sem plugin: cada teste roda a corotina com asyncio.run.
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from GarimpoInvestimentos.dpl import (
    CryptoDataProvider,
    DataProvider,
    DataUnavailableError,
    FallbackRouter,
    MarketDataPoint,
)
from predictor_core.obs import read_events

UTC_NOW = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)


def _point(source: str, close: float) -> MarketDataPoint:
    return MarketDataPoint(
        symbol="bitcoin", timestamp=UTC_NOW, open=close, high=close + 1,
        low=close - 1, close=close, volume=10.0, source=source,
        interval="1d", published_at=UTC_NOW,
    )


class _OkProvider(DataProvider):
    def __init__(self, name, close):
        self.name = name
        self._close = close
        self.calls = 0

    async def fetch_ohlcv(self, symbol, interval="1d", limit=1):
        self.calls += 1
        return [_point(self.name, self._close)]

    async def health_check(self):
        return True


class _FailProvider(DataProvider):
    def __init__(self, name):
        self.name = name
        self.calls = 0

    async def fetch_ohlcv(self, symbol, interval="1d", limit=1):
        self.calls += 1
        raise RuntimeError(f"{self.name} caiu")

    async def health_check(self):
        return False


# --- Contrato MarketDataPoint ------------------------------------------------

def test_marketdatapoint_rejeita_high_menor_que_low():
    with pytest.raises(ValueError):
        MarketDataPoint(
            symbol="x", timestamp=UTC_NOW, open=1, high=1, low=5, close=2,
            volume=0, source="t", interval="1d", published_at=UTC_NOW,
        )


def test_marketdatapoint_rejeita_published_antes_do_timestamp():
    with pytest.raises(ValueError):
        MarketDataPoint(
            symbol="x", timestamp=UTC_NOW, open=1, high=2, low=1, close=2,
            volume=0, source="t", interval="1d",
            published_at=UTC_NOW - timedelta(hours=1),
        )


def test_marketdatapoint_eh_imutavel():
    p = _point("binance", 100.0)
    with pytest.raises(Exception):
        p.close = 999.0  # frozen dataclass


# --- Router: fallback sequencial ---------------------------------------------

def test_primaria_ok_nao_chama_secundaria():
    primaria = _OkProvider("binance", 100.0)
    secundaria = _OkProvider("coingecko", 200.0)
    router = FallbackRouter([primaria, secundaria])
    pts = asyncio.run(router.fetch_ohlcv("bitcoin"))
    assert pts[0].source == "binance"
    assert secundaria.calls == 0  # secundária nunca tocada


def test_fallback_usa_secundaria_quando_primaria_falha(tmp_path, monkeypatch):
    events = tmp_path / "ev.jsonl"
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(events))
    primaria = _FailProvider("binance")
    secundaria = _OkProvider("coingecko", 200.0)
    router = FallbackRouter([primaria, secundaria])
    pts = asyncio.run(router.fetch_ohlcv("bitcoin"))
    assert pts[0].source == "coingecko"
    assert primaria.calls == 1 and secundaria.calls == 1
    eventos = [e["event"] for e in read_events(events)]
    assert "data.fallback" in eventos  # degradação foi registrada


def test_todas_falham_levanta_data_unavailable(tmp_path, monkeypatch):
    events = tmp_path / "ev.jsonl"
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(events))
    router = FallbackRouter([_FailProvider("binance"), _FailProvider("coingecko")])
    with pytest.raises(DataUnavailableError):
        asyncio.run(router.fetch_ohlcv("bitcoin"))
    eventos = [e["event"] for e in read_events(events)]
    assert "data.unavailable" in eventos


def test_router_exige_ao_menos_um_provedor():
    with pytest.raises(ValueError):
        FallbackRouter([])


# --- Fachada -----------------------------------------------------------------

def test_fachada_latest_close_delegada_ao_router():
    router = FallbackRouter([_OkProvider("binance", 42.0)])
    facade = CryptoDataProvider(router=router)
    assert asyncio.run(facade.latest_close("bitcoin")) == 42.0


def test_fachada_monta_router_do_sources_json():
    # Sem injeção: deve ler o sources.json real e instanciar os 2 conectores
    # (binance, coingecko) na ordem. Não faz rede — só valida a montagem.
    facade = CryptoDataProvider()
    assert facade._router._providers[0].name == "binance"
    assert facade._router._providers[1].name == "coingecko"
