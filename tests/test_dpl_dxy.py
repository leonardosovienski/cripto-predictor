"""DXYProvider (httpx mockado — sem rede real, ver aviso em dpl/providers/dxy.py)."""

import asyncio

import pytest

from GarimpoInvestimentos.dpl.providers import dxy

_CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2026-08-10,103.10,103.40,102.90,103.20,0\n"
    "2026-08-11,103.20,103.55,103.00,103.45,0\n"
    "2026-08-12,103.45,103.60,103.10,103.30,0\n"
)


class _Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class _Client:
    def __init__(self, text):
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def get(self, url, params=None):
        return _Resp(self._text)


def test_dxy_parses_csv_into_signal_points(monkeypatch):
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client(_CSV))
    provider = dxy.DXYProvider()
    points = asyncio.run(provider.fetch(limit=90))

    assert len(points) == 3
    assert [p.value for p in points] == [103.20, 103.45, 103.30]
    assert all(p.source == "stooq" and p.name == "dxy" for p in points)
    # publicado no próprio dia — mesmo padrão conservador do FearAndGreedProvider
    assert all(p.published_at == p.timestamp for p in points)


def test_dxy_respects_limit(monkeypatch):
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client(_CSV))
    provider = dxy.DXYProvider()
    points = asyncio.run(provider.fetch(limit=2))
    assert len(points) == 2
    assert [p.value for p in points] == [103.45, 103.30]


def test_dxy_skips_malformed_rows_without_interpolating(monkeypatch):
    csv_with_gap = _CSV + "2026-08-13,N/D,N/D,N/D,N/D,0\n"
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client(csv_with_gap))
    provider = dxy.DXYProvider()
    points = asyncio.run(provider.fetch(limit=90))
    assert len(points) == 3  # a linha N/D foi descartada, não virou 0.0


def test_dxy_empty_response_raises(monkeypatch):
    monkeypatch.setattr(
        dxy, "get_http_client", lambda *a, **k: _Client("Date,Open,High,Low,Close,Volume\n")
    )
    provider = dxy.DXYProvider()
    with pytest.raises(RuntimeError, match="dxy"):
        asyncio.run(provider.fetch())


def test_dxy_unexpected_format_raises(monkeypatch):
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client("<html>not a csv</html>"))
    provider = dxy.DXYProvider()
    with pytest.raises(RuntimeError, match="formato de CSV inesperado"):
        asyncio.run(provider.fetch())


def test_dxy_custom_symbol_is_passed_through(monkeypatch):
    seen = {}

    class _RecordingClient(_Client):
        async def get(self, url, params=None):
            seen["params"] = params
            return await super().get(url, params)

    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _RecordingClient(_CSV))
    provider = dxy.DXYProvider(symbol="usdx")
    asyncio.run(provider.fetch())
    assert seen["params"]["s"] == "usdx"
