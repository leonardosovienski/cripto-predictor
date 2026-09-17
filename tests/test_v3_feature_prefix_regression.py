"""Prefix invariance of the actual numerical builder, not a copied formula.

These tests cover supplied event-time series and closed spot candles. They do
not prove real provider publication timestamps or missing historical vintages.
"""

from dataclasses import asdict

import pytest

from GarimpoInvestimentos.v3.crowding_features import build_oi_volume_ratio
from GarimpoInvestimentos.v3.feature_builder import build_feature_vectors

HOUR = 3_600_000
ORIGIN = 1_704_067_200_000


def market():
    times = [ORIGIN + hour * HOUR for hour in range(0, 201, 8)]
    rates = [0.0001 * ((i * 7) % 11 - 5) for i in range(len(times))]
    oi = {t: 1_000_000.0 + i * i * 137 for i, t in enumerate(times)}
    spot = {ORIGIN + h * HOUR: 30_000.0 + h * 11 + h % 7 for h in range(-32, 210)}
    return times, rates, oi, spot


def build(times, rates, oi, spot):
    return build_feature_vectors(times, rates, oi, spot, "BTCUSDT", fr_window=3)


@pytest.mark.parametrize("cutoff_hour", [48, 96, 160])
def test_all_feature_fields_match_the_actual_truncated_input(cutoff_hour):
    times, rates, oi, spot = market()
    cutoff = ORIGIN + cutoff_hour * HOUR
    prefix_times = [t for t in times if t <= cutoff]
    prefix_oi = {t: v for t, v in oi.items() if t <= cutoff}
    # A candle keyed by its OPEN time is available only after its close.
    prefix_spot = {t: v for t, v in spot.items() if t + HOUR <= cutoff}
    expected = build(prefix_times, rates[: len(prefix_times)], prefix_oi, prefix_spot)
    assert len(expected) >= 3
    full = [v for v in build(times, rates, oi, spot) if v.timestamp_exchange_ms <= cutoff]
    assert [asdict(v) for v in full] == [asdict(v) for v in expected]
    changed_rates = [r if t <= cutoff else r + 10 for t, r in zip(times, rates, strict=True)]
    changed_oi = {t: v if t <= cutoff else v * 100 for t, v in oi.items()}
    changed_spot = {t: v if t + HOUR <= cutoff else v * 100 for t, v in spot.items()}
    changed = [
        v
        for v in build(times, changed_rates, changed_oi, changed_spot)
        if v.timestamp_exchange_ms <= cutoff
    ]
    assert changed == expected


def test_future_oi_does_not_fill_a_missing_asof_observation():
    times, rates, oi, spot = market()
    target = times[10]
    oi.pop(target)
    oi[target + 60_000] = 99_000_000.0
    actual = build(times, rates, oi, spot)
    assert target not in {v.timestamp_exchange_ms for v in actual}


def test_missing_closed_candle_is_not_replaced_by_future_or_gap_bridging():
    times, rates, oi, spot = market()
    target = times[10]
    spot.pop(target - 3 * HOUR)
    actual = build(times, rates, oi, spot)
    assert target not in {v.timestamp_exchange_ms for v in actual}


def test_crowding_feature_ignores_unclosed_and_future_volume():
    times, rates, oi, spot = market()
    cutoff = times[12]
    vectors = [v for v in build(times, rates, oi, spot) if v.timestamp_exchange_ms <= cutoff]
    volume = {t: 500.0 + i for i, t in enumerate(spot)}
    prefix = {t: v for t, v in volume.items() if t + HOUR <= cutoff}
    changed = {t: v if t + HOUR <= cutoff else v * 1000 for t, v in volume.items()}
    expected = build_oi_volume_ratio(vectors, prefix)
    assert expected
    assert build_oi_volume_ratio(vectors, volume) == expected
    assert build_oi_volume_ratio(vectors, changed) == expected
