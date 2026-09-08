"""Scientific controls for the independent analog screen, before real outcomes."""

from datetime import date

import numpy as np
import pytest

from scripts.collect_altcoin_analogs import select_symbols, time_ms
from scripts.research_altcoin_analogs import (
    AnalogModel,
    block_ci,
    extract_features,
    net_returns,
    outcome,
    period_for,
)


def bars(n=200):
    result = np.ones((n, 6))
    result[:, :4] *= 100
    result[:, 1] = 102
    result[:, 2] = 98
    result[:, 4] = 100000
    result[:, 5] = 10000000
    return result


def test_future_prices_and_volume_cannot_change_past_features():
    data, btc = bars(), bars()
    expected, volume = extract_features(data, btc, 150)
    # Even the previous day's candle is unavailable to this deliberately lagged rule.
    data[149:] *= 500
    btc[149:] *= 0.01
    actual, actual_volume = extract_features(data, btc, 150)
    np.testing.assert_array_equal(expected, actual)
    assert volume == actual_volume


def test_feature_endpoint_is_saturday_for_monday_entry():
    data = bars()
    data[148, 3] = 101
    values, _ = extract_features(data, bars(), 150)
    assert values[0] == pytest.approx(np.log(1.01))
    assert values[3] == 0
    assert values[6] == pytest.approx((6 * 0.04 + 4 / 101) / 7)


def test_missing_past_history_disqualifies_but_missing_future_does_not():
    data = bars()
    data[153] = np.nan
    assert extract_features(data, bars(), 150) is not None
    assert outcome(data, 150) == (-1, "missing_or_invalid_outcome_bar")
    data[100] = np.nan
    assert extract_features(data, bars(), 150) is None


def test_missing_entry_is_preserved_as_full_loss_stress():
    data = bars()
    data[150] = np.nan
    assert outcome(data, 150) == (-1, "missing_entry")


def test_buy_and_sell_costs_reduce_quantity_and_proceeds():
    calculated = net_returns(np.array([0.2, -1.0, 0.0]), 20)
    units = 5000 / (100 * 1.002)
    proceeds = units * 120 * 0.998
    assert calculated[0] == pytest.approx(proceeds / 5000 - 1)
    assert calculated[1] == -1
    assert calculated[2] < 0


def test_archive_microseconds_and_api_milliseconds_match():
    assert time_ms(1735689600000000) == time_ms(1735689600000)
    assert time_ms(1735775999999999) == 1735775999999


def test_universe_sampling_ignores_input_order_and_duplicates():
    protocol = {"screen_id": "fixed", "data": {"exclude_bases": ["BTC", "USDC"], "max_assets": 3}}
    universe = [
        "BTCUSDT",
        "USDCUSDT",
        "ETHUSDT",
        "ABCUSDT",
        "XYZUSDT",
        "ETHDOWNUSDT",
        "XYZBTC",
        "DEADUSDT",
    ]
    a = select_symbols(universe, protocol)
    b = select_symbols(list(reversed(universe)) + universe, protocol)
    assert a == b
    assert len(a) == 3
    assert set(a) <= {"ETHUSDT", "ABCUSDT", "XYZUSDT", "DEADUSDT"}


def test_training_and_evaluation_label_boundary_purge():
    assert period_for(date(2023, 12, 25)) == "train"
    assert period_for(date(2024, 1, 1)) == "evaluation_1"
    assert period_for(date(2024, 12, 30)) is None
    assert period_for(date(2026, 8, 31)) == "evaluation_2"
    assert period_for(date(2026, 9, 7)) == "current"


def test_positive_control_detects_prior_state_but_permuted_null_does_not():
    rng = np.random.default_rng(719)
    x = rng.normal(size=(2000, 8))
    y = (x[:, 0] > 0.8).astype(int)
    x[:, 0] *= 5  # Same train-only robust scaler is still used.
    query = rng.normal(size=(400, 8))
    query[:200, 0] = 10
    query[200:, 0] = -10
    positive = AnalogModel(200).fit(x, y).predict(query)[0]
    null = AnalogModel(200).fit(x, rng.permutation(y)).predict(query)[0]
    assert positive[:200].mean() - positive[200:].mean() > 0.35
    assert abs(null[:200].mean() - null[200:].mean()) < 0.08


def test_scaler_uses_training_only_and_prediction_cannot_mutate_it():
    rng = np.random.default_rng(91)
    x = rng.normal(size=(500, 8))
    model = AnalogModel().fit(x, np.zeros(500))
    expected = model.median.copy()
    model.predict(np.full((2, 8), 999999.0))
    np.testing.assert_array_equal(model.median, expected)


def test_block_bootstrap_counts_weeks_not_individual_coins():
    result = block_ci(np.full(52, 0.01))
    assert result["n_paired_weeks"] == 52
    assert result["effective_n_power_heuristic"] == 13
    assert result["ci95_block4"] == pytest.approx([0.01, 0.01])
