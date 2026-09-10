import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.dpl import DataUnavailableError, FallbackRouter
from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.feature_engineering import derive_features
from GarimpoInvestimentos.dpl.providers import coingecko


def point(day, price=100.0):
    ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day)
    return MarketDataPoint(
        symbol="bitcoin",
        timestamp=ts,
        published_at=ts + timedelta(days=1),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=2,
        source="binance",
        interval="1d",
    )


def test_seven_days_must_not_mean_fourteen_calendar_days():
    result = derive_features([point(i * 2, 100 + i) for i in range(8)])
    assert "change_7d" not in result
    assert "change_24h" not in result
    assert result["price_usd"] == 107


def test_indicators_use_only_contiguous_suffix_after_gap():
    result = derive_features(
        [point(i, 100 + i) for i in range(200)] + [point(202, 150), point(203, 165)]
    )
    assert result["change_24h"] == 10
    assert "sma_200" not in result


def test_duplicates_and_intraday_cannot_be_daily_features():
    for series in ([point(0), point(0)], [replace(point(0), interval="1h")]):
        with pytest.raises(ValueError):
            derive_features(series)


def fake_http(monkeypatch, payload):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(coingecko, "get_http_client", Client)


@pytest.mark.parametrize("interval", ["1m", "5m", "15m", "30m", "1h", "4h", "nonsense"])
def test_coingecko_refuses_unavailable_volume_before_network(interval, monkeypatch):
    def forbidden_network():
        pytest.fail("unsupported OHLCV must not request data or retry")

    monkeypatch.setattr(coingecko, "get_http_client", forbidden_network)
    with pytest.raises(ValueError, match="intervalo"):
        asyncio.run(coingecko.CoinGeckoProvider(api_key="").fetch_ohlcv("bitcoin", interval, 2))


def test_coingecko_daily_discards_partial_before_limit_and_normalizes_close(monkeypatch):
    midnight = datetime(2026, 1, 2, tzinfo=UTC)
    ms = int(midnight.timestamp() * 1000)
    fake_http(
        monkeypatch,
        {
            "prices": [[ms, 100], [ms + 86_400_000, 110], [ms + 90_000_000, 999]],
            "total_volumes": [[ms, 1000], [ms + 86_400_000, 2000], [ms + 90_000_000, 9999]],
        },
    )
    rows = asyncio.run(
        coingecko.CoinGeckoProvider(api_key="")._fetch_daily("bitcoin", "bitcoin", 2)
    )
    assert [p.close for p in rows] == [100, 110]
    assert rows[0].timestamp == midnight - timedelta(days=1)
    assert rows[0].published_at == midnight + timedelta(minutes=10)


def test_coingecko_daily_missing_volume_is_not_zero(monkeypatch):
    ms = int(datetime(2026, 1, 2, tzinfo=UTC).timestamp() * 1000)
    fake_http(monkeypatch, {"prices": [[ms, 100]], "total_volumes": []})
    with pytest.raises(ValueError, match="volume missing"):
        asyncio.run(coingecko.CoinGeckoProvider(api_key="")._fetch_daily("bitcoin", "bitcoin", 1))


def test_intraday_fallback_cannot_deliver_fabricated_zero_volume(monkeypatch, tmp_path):
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    fake_http(monkeypatch, [[1767312000000, 100, 110, 90, 105]])
    router = FallbackRouter([coingecko.CoinGeckoProvider(api_key="")])
    with pytest.raises(DataUnavailableError):
        asyncio.run(router.fetch_ohlcv("bitcoin", "4h", 1))

    expected = replace(point(0), interval="4h", source="available", volume=42)

    class AvailableProvider:
        name = "available"

        async def fetch_ohlcv(self, symbol, interval, limit):
            return [expected]

    router = FallbackRouter([coingecko.CoinGeckoProvider(api_key=""), AvailableProvider()])
    assert asyncio.run(router.fetch_ohlcv("bitcoin", "4h", 1)) == [expected]
