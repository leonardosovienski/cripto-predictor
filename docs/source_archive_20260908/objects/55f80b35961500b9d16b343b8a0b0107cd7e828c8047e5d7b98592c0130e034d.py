from datetime import UTC, datetime

from GarimpoInvestimentos.analyzers.score_engine import calculate_final_score
from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.feature_engineering import derive_features


def _point(day: int, close: float) -> MarketDataPoint:
    timestamp = datetime(2026, 1, day, tzinfo=UTC)
    return MarketDataPoint(
        symbol="bitcoin",
        timestamp=timestamp,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000 + day,
        source="fixture",
        interval="1d",
        published_at=timestamp,
    )


def test_score_golden_exact():
    cases = [
        ({"opportunity_score": 72.345}, 72.34),
        ({"opportunity_score": -1}, 0.0),
        ({"opportunity_score": 101}, 100.0),
        ({"opportunity_score": "bad"}, 50.0),
    ]
    assert [calculate_final_score(payload) for payload, _ in cases] == [
        expected for _, expected in cases
    ]


def test_features_golden_exact():
    features = derive_features([_point(1, 100.0), _point(2, 110.0), _point(3, 121.0)])
    assert features == {"price_usd": 121.0, "volume_usd": 1003, "change_24h": 10.0}
