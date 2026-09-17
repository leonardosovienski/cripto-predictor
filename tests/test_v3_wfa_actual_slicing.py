"""Observe inputs used by run_wfa itself; no copied fold generator.

Only CSV input and the expensive HMM/signal boundaries are replaced. The real
feature builder, slicing, warmup and label-maturity conditions still execute.
Inactive signals deliberately prevent creation of an economic result.
"""

import random
from types import SimpleNamespace

import pytest

from GarimpoInvestimentos.v3 import backtest_v3 as wfa

HOUR = 3_600_000
DAY = 24 * HOUR
ORIGIN = 1_704_067_200_000


@pytest.mark.parametrize("cost_aware", [False, True])
def test_real_wfa_consumes_only_its_declared_fit_and_evaluation_intervals(
    monkeypatch, tmp_path, cost_aware
):
    rng = random.Random(1087)
    times = [ORIGIN + i * 8 * HOUR for i in range(247 * 3 + 1)]
    funding = [
        SimpleNamespace(
            symbol="BTCUSDT", funding_time_ms=t, funding_rate=rng.uniform(-0.001, 0.001)
        )
        for t in times
    ]
    oi = [
        SimpleNamespace(symbol="BTCUSDT", timestamp_ms=t, oi_notional_usd=1e6 + i * 17)
        for i, t in enumerate(times)
    ]
    spot = []
    price = 30_000.0
    for hour in range(-32, 247 * 24 + 32):
        price *= 1 + rng.uniform(-0.001, 0.001)
        spot.append(
            SimpleNamespace(
                symbol="BTCUSDT", open_ms=ORIGIN + hour * HOUR, close=price, volume=500.0
            )
        )
    monkeypatch.setattr(wfa, "DATA_DIR", tmp_path)
    monkeypatch.setattr(wfa, "load_funding_csv", lambda _: funding)
    monkeypatch.setattr(wfa, "load_oi_csv", lambda _: oi)
    monkeypatch.setattr(wfa, "load_spot_csv", lambda _: spot)
    original_builder = wfa.build_feature_vectors
    built = []

    def observe_builder(*args, **kwargs):
        vectors = original_builder(*args, **kwargs)
        built.extend(vectors)
        return vectors

    monkeypatch.setattr(wfa, "build_feature_vectors", observe_builder)
    engines = []

    class SpyEngine:
        def __init__(self, *, extra_features):
            assert extra_features == ()
            self.signals = []
            engines.append(self)

        def fit(self, returns, volatility, *, extra_covariates):
            assert extra_covariates is None
            self.fit_inputs = (returns, volatility)

        def predict_series(self, returns, volatility, *, extra_covariates):
            assert extra_covariates is None
            self.infer_inputs = (returns, volatility)
            return [None] * len(returns)

    def inactive_signal(feature, regime, **kwargs):
        engines[-1].signals.append(feature.timestamp_exchange_ms)
        return SimpleNamespace(active=False, direction=0, strength=0.0)

    monkeypatch.setattr(wfa, "RegimeEngine", SpyEngine)
    monkeypatch.setattr(wfa, "generate_signal", inactive_signal)
    # The runtime processes both real folds but cannot claim a result with no active signals.
    with pytest.raises(RuntimeError, match="Nenhum fold completado"):
        wfa.run_wfa("BTCUSDT", fr_window=3, horizon_hours=24, cost_aware_filter=cost_aware)
    assert len(engines) == 2
    # Independent, explicit expectations from the documented 180/7/30-day contract.
    for engine, (is_start, is_end, oos_start, oos_end) in zip(
        engines, [(0, 180, 187, 217), (30, 210, 217, 247)], strict=True
    ):
        train = [
            v
            for v in built
            if is_start * DAY <= v.timestamp_exchange_ms - ORIGIN < is_end * DAY
        ]
        inference = [
            v
            for v in built
            if is_start * DAY <= v.timestamp_exchange_ms - ORIGIN < oos_end * DAY
        ]
        evaluation = [
            v
            for v in built
            if oos_start * DAY <= v.timestamp_exchange_ms - ORIGIN < oos_end * DAY
        ]
        assert train and inference and evaluation
        assert engine.fit_inputs == (
            [v.log_return_8h for v in train],
            [v.realized_vol_24h for v in train],
        )
        assert engine.infer_inputs == (
            [v.log_return_8h for v in inference],
            [v.realized_vol_24h for v in inference],
        )
        # Purge observations are legitimate causal warmup, not fit/evaluation observations.
        assert any(
            is_end * DAY <= v.timestamp_exchange_ms - ORIGIN < oos_start * DAY
            for v in inference
        )
        calibration = (
            [
                v.timestamp_exchange_ms
                for v in train
                if v.timestamp_exchange_ms + DAY <= ORIGIN + is_end * DAY
            ]
            if cost_aware
            else []
        )
        assert engine.signals == calibration + [v.timestamp_exchange_ms for v in evaluation]
