"""Independent price/cash-flow examples; no market calls or strategy promotion."""

import asyncio
import math

import pytest

from GarimpoInvestimentos.analyzers.trials import FrozenFamilyError
from GarimpoInvestimentos.v3.backtest_v3 import (
    _barrier_exit,
    _find_barrier_return,
    _realized_funding_pnl,
)
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord
from GarimpoInvestimentos.v3.costs import CostModel
from GarimpoInvestimentos.v3.economic_gate import estimate_edge
from GarimpoInvestimentos.v3.paper_trader import run_paper

H = 3_600_000


def test_stop_uses_observed_gap_price_and_actual_duration():
    result = _barrier_exit(H, 24, 1, {0: 100.0, H: 90.0}, stop_loss_bps=100)
    assert result is not None
    assert result.elapsed_hours == 1
    assert result.reason == "stop_loss"
    assert math.expm1(result.log_return) == pytest.approx(-0.10)


def test_partial_history_is_not_a_mature_horizon_return():
    assert _find_barrier_return(H, 24, 1, {0: 100, H: 101}) is None


def test_unobserved_barrier_path_is_not_filled_from_future_prices():
    assert _barrier_exit(H, 2, 1, {0: 100, 2 * H: 95}, stop_loss_bps=100) is None


def test_realized_funding_uses_each_settlement_rate_and_mark():
    rates = [
        FundingRecord("BTCUSDT", 8 * H, 0.01, 110),
        FundingRecord("BTCUSDT", 16 * H, -0.02, 120),
    ]
    assert _realized_funding_pnl(0.5, 0, 16 * H, 100, rates) == pytest.approx(0.0065)
    assert _realized_funding_pnl(0.5, 0, 16 * H, 100, rates[:1]) is None
    assert _realized_funding_pnl(0.5, 0, 4 * H, 100, []) == 0


def test_friction_charges_the_actual_exit_notional():
    assert CostModel(10, 0).friction(1, exit_price_ratio=2) == pytest.approx(0.003)


def test_edge_estimator_does_not_drop_invalid_observations():
    with pytest.raises(ValueError, match="finite"):
        estimate_edge([0.1] * 20 + [float("nan")])


def test_frozen_paper_family_stops_before_market_or_pipeline_calls(monkeypatch):
    async def forbidden(**_kwargs):
        pytest.fail("pipeline must not run for a frozen family")

    monkeypatch.setattr("GarimpoInvestimentos.v3.paper_trader.run_symbol", forbidden)
    with pytest.raises(FrozenFamilyError):
        asyncio.run(run_paper("BTCUSDT", "2024-01-01"))
