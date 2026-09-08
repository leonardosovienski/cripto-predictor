from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.v3.backtest_v3 import _find_spot_return

from GarimpoInvestimentos.config import Settings
from GarimpoInvestimentos.dpl.alignment import AlignmentEngine
from GarimpoInvestimentos.dpl.contracts import MarketDataPoint, SignalPoint
from GarimpoInvestimentos.v3.feature_builder import _find_asof
from GarimpoInvestimentos.v3.timeindex import SortedTimeIndex


def test_unknown_llm_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "multi")
    monkeypatch.setenv("LLM_MULTI_PROVIDERS", "gemini,grok")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("NEWS_PROVIDERS", "google_news_rss")
    with pytest.raises(ValueError, match="LLM_MULTI_PROVIDERS"):
        Settings(_env_file=None)


def test_asof_never_selects_future_neighbor():
    assert _find_asof(100, {96: 1.0, 101: 2.0}, 10) == 1.0
    assert SortedTimeIndex({96: 1.0, 101: 2.0}).as_of(100, 10) == 1.0


def test_revision_is_not_visible_before_its_vintage():
    candle_ts = datetime(2026, 1, 10, tzinfo=UTC)
    candle = MarketDataPoint(
        symbol="X", timestamp=candle_ts, open=1, high=1, low=1, close=1,
        volume=1, source="x", interval="1d", published_at=candle_ts,
    )
    original = SignalPoint(
        name="macro", timestamp=candle_ts - timedelta(days=5), value=1,
        source="x", published_at=candle_ts - timedelta(days=4),
        vintage=candle_ts - timedelta(days=4),
    )
    revision = SignalPoint(
        name="macro", timestamp=candle_ts - timedelta(days=5), value=99,
        source="x", published_at=candle_ts - timedelta(days=4),
        vintage=candle_ts + timedelta(days=30),
    )
    row = AlignmentEngine().align([candle], {"macro": [original, revision]})[0]
    assert row["macro"] == 1


def test_backtest_spot_return_uses_only_closed_candles():
    hour = 3_600_000
    # Em t=2h, a vela [2h,3h) tem um close extremo, mas ele ainda e futuro.
    spot = {hour: 100.0, 2 * hour: 1_000.0, 3 * hour: 110.0}
    result = _find_spot_return(2 * hour, 2, spot)
    assert result == pytest.approx(__import__("math").log(110.0 / 100.0))
