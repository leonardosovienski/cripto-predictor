"""DXYProvider (httpx mockado — sem rede real, ver aviso em dpl/providers/dxy.py).

Fonte: FRED (fredgraph.csv), série DTWEXBGS. Trocado de stooq.com em 2026-08-14
depois que o endpoint de CSV de lá passou a exigir um desafio anti-bot em
JavaScript (confirmado ao vivo — HTTP 200 com página de "verify your browser",
não CSV) — ver histórico no dpl/providers/dxy.py.
"""

import asyncio

import pytest

from GarimpoInvestimentos.dpl.providers import dxy

_CSV = "DATE,DTWEXBGS\n2026-08-10,103.10\n2026-08-11,103.45\n2026-08-12,103.30\n"


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
    assert [p.value for p in points] == [103.10, 103.45, 103.30]
    assert all(p.source == "fred" and p.name == "dxy" for p in points)


def test_dxy_publish_lag_is_applied_conservatively(monkeypatch):
    """Default publish_lag_days=1: published_at fica 1 dia DEPOIS do timestamp —
    nunca antes, pra não arriscar look-ahead num dado que pode sair defasado."""
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client(_CSV))
    provider = dxy.DXYProvider()
    points = asyncio.run(provider.fetch(limit=90))
    for p in points:
        assert (p.published_at - p.timestamp).days == 1


def test_dxy_respects_limit(monkeypatch):
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client(_CSV))
    provider = dxy.DXYProvider()
    points = asyncio.run(provider.fetch(limit=2))
    assert len(points) == 2
    assert [p.value for p in points] == [103.45, 103.30]


def test_dxy_skips_missing_value_rows_without_interpolating(monkeypatch):
    """FRED marca feriado/sem dado com "." — nunca vira 0.0 nem é interpolado."""
    csv_with_gap = _CSV + "2026-08-13,.\n"
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client(csv_with_gap))
    provider = dxy.DXYProvider()
    points = asyncio.run(provider.fetch(limit=90))
    assert len(points) == 3  # a linha "." foi descartada, não virou 0.0


def test_dxy_empty_response_raises(monkeypatch):
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client("DATE,DTWEXBGS\n"))
    provider = dxy.DXYProvider()
    with pytest.raises(RuntimeError, match="dxy"):
        asyncio.run(provider.fetch())


def test_dxy_unexpected_format_raises(monkeypatch):
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client("<html>not a csv</html>"))
    provider = dxy.DXYProvider()
    with pytest.raises(RuntimeError, match="formato de CSV inesperado"):
        asyncio.run(provider.fetch())


def test_dxy_custom_series_is_passed_through(monkeypatch):
    seen = {}

    class _RecordingClient(_Client):
        async def get(self, url, params=None):
            seen["params"] = params
            return await super().get(url, params)

    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _RecordingClient(_CSV))
    provider = dxy.DXYProvider(series="DTWEXBGS")
    asyncio.run(provider.fetch())
    assert seen["params"]["id"] == "DTWEXBGS"


def test_dxy_custom_publish_lag(monkeypatch):
    monkeypatch.setattr(dxy, "get_http_client", lambda *a, **k: _Client(_CSV))
    provider = dxy.DXYProvider(publish_lag_days=0)
    points = asyncio.run(provider.fetch())
    assert all(p.published_at == p.timestamp for p in points)
