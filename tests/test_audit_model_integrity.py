"""Timeline correctness and model-state integrity, using synthetic data only."""

from types import SimpleNamespace

import pytest

from GarimpoInvestimentos.analyzers.hypothesis_loop_runner import _build_dados_e_retornos
from GarimpoInvestimentos.v3.crowding_features import build_oi_volume_ratio
from GarimpoInvestimentos.v3.feature_builder import FeatureVector, build_feature_vectors
from GarimpoInvestimentos.v3.timeindex import SortedTimeIndex

HOUR = 3_600_000


def vector(ts, price=100):
    return FeatureVector(ts, "BTCUSDT", 0.0001, 1000, price, 1, 0.1, 0.1, 0.01, 0.01, 1)


def test_h8_missing_period_is_not_a_shorter_horizon():
    rows = [vector(hour * HOUR, 100 + hour) for hour in (0, 8, 24, 32, 40)]
    _, returns = _build_dados_e_retornos(rows, 1)
    import math

    assert returns[0] == pytest.approx(math.log(124 / 100))
    assert returns[1] == pytest.approx(math.log(132 / 108))
    assert returns[2] is None


def test_volume_of_open_candle_never_enters_crowding():
    fv = vector(32 * HOUR)
    past = build_oi_volume_ratio([fv], {31 * HOUR: 10, 32 * HOUR: 1})
    changed_future = build_oi_volume_ratio([fv], {31 * HOUR: 10, 32 * HOUR: 100000})
    assert past == changed_future == [0.0]


def test_volatility_requires_all_hourly_intervals():
    times = [index * 8 * HOUR for index in range(8)]
    rates = [0.0001 * (index % 3) for index in range(8)]
    oi = dict.fromkeys(times, 1000.0)
    spot = {index * HOUR: 100.0 + index for index in range(56)}
    complete = build_feature_vectors(times, rates, oi, spot, "BTCUSDT", fr_window=2)
    assert 32 * HOUR in [row.timestamp_exchange_ms for row in complete]
    del spot[30 * HOUR]
    incomplete = build_feature_vectors(times, rates, oi, spot, "BTCUSDT", fr_window=2)
    assert 32 * HOUR not in [row.timestamp_exchange_ms for row in incomplete]


def test_time_index_is_independent_of_later_mapping_mutation():
    data = {1: 100.0}
    index = SortedTimeIndex(data)
    data[1] = 500.0
    assert index.nearest(1) == 100.0


def test_failed_refit_preserves_the_previous_model_and_scaler(monkeypatch):
    pytest.importorskip("hmmlearn")
    from GarimpoInvestimentos.v3 import regime_engine as module

    engine = module.RegimeEngine()
    old_model, old_scaler = object(), object()
    engine._model, engine._scaler = old_model, old_scaler
    engine._state_map = {0: "bull"}

    def fail(_values):
        raise ValueError("synthetic fit failure")

    monkeypatch.setattr(module._hmmlearn, "GaussianHMM", lambda **_kw: SimpleNamespace(fit=fail))
    with pytest.raises(RuntimeError, match="nao convergiu"):
        engine.fit([float(index % 5) for index in range(35)], [0.01] * 35)
    assert engine._model is old_model
    assert engine._scaler is old_scaler
    assert engine._state_map == {0: "bull"}


def test_forward_computes_covariance_inverses_once_per_state(monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("hmmlearn")
    from GarimpoInvestimentos.v3.regime_engine import _forward_causal

    original = np.linalg.inv
    calls = []

    def counted(matrix):
        calls.append(matrix.copy())
        return original(matrix)

    monkeypatch.setattr(np.linalg, "inv", counted)
    result = _forward_causal(
        np.zeros((100, 2)),
        np.ones(3) / 3,
        np.ones((3, 3)) / 3,
        np.zeros((3, 2)),
        np.array([np.eye(2)] * 3),
    )
    assert len(calls) == 3
    np.testing.assert_allclose(result, np.ones((100, 3)) / 3)
