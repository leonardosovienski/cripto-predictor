import inspect

import pytest

from GarimpoInvestimentos.v3 import backtest_v3
from GarimpoInvestimentos.v3.costs import CostModel
from GarimpoInvestimentos.v3.economic_gate import decide_cost_aware, estimate_edge


def test_gate_is_opt_in_and_does_not_rewrite_frozen_v3_default():
    parameter = inspect.signature(backtest_v3.run_wfa).parameters["cost_aware_filter"]
    assert parameter.default is False


def test_estimate_requires_predeclared_sample_floor():
    assert estimate_edge([0.02] * 19, minimum_sample=20) is None
    estimate = estimate_edge([0.02] * 20, minimum_sample=20)
    assert estimate is not None
    assert estimate.sample_size == 20
    assert estimate.lower_signed_return == pytest.approx(0.02)


def test_costs_turn_small_predictive_edge_into_no_trade():
    estimate = estimate_edge([0.002] * 30)
    decision = decide_cost_aware(
        estimate,
        direction=1,
        funding_rate=0.0,
        horizon_hours=24,
        costs=CostModel(taker_fee_bps=10, slippage_bps=5),
    )
    assert decision.estimated_round_trip_friction == pytest.approx(0.003)
    assert decision.conservative_net_return == pytest.approx(-0.001)
    assert decision.action == "NO_TRADE"
    assert decision.capital_enabled is False


def test_large_conservative_edge_can_only_create_shadow_trade():
    estimate = estimate_edge([0.02] * 30)
    decision = decide_cost_aware(
        estimate,
        direction=-1,
        funding_rate=0.0001,
        horizon_hours=24,
        costs=CostModel(taker_fee_bps=10, slippage_bps=5),
        minimum_net_edge=0.005,
    )
    assert decision.action == "SHADOW_TRADE"
    assert decision.conservative_net_return is not None
    assert decision.conservative_net_return > 0.005
    assert decision.capital_enabled is False


def test_missing_calibration_fails_closed():
    decision = decide_cost_aware(
        None,
        direction=1,
        funding_rate=0.0,
        horizon_hours=8,
        costs=CostModel(),
    )
    assert decision.action == "NO_TRADE"
    assert decision.reason == "INSUFFICIENT_EDGE_CALIBRATION"


def test_non_finite_observable_funding_fails_high():
    with pytest.raises(ValueError):
        decide_cost_aware(
            estimate_edge([0.02] * 20),
            direction=1,
            funding_rate=float("nan"),
            horizon_hours=8,
            costs=CostModel(),
        )
