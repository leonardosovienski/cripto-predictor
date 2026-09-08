"""Economic invariants, causal boundaries and missingness for the new study."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import numpy as np
import pytest

from scripts.backtest_absolute_carry import (
    ENTRY,
    carry_decisions,
    common_step,
    hourly_surplus,
    past_funding_signal,
    rounded_quantity,
    simulate,
)
from scripts.backtest_absolute_spot import block_interval, momentum_decisions
from scripts.backtest_altcoin_payoff import BASE, portfolio_factor
from scripts.backtest_altcoin_payoff import END as DATE_END
from scripts.collect_absolute_carry import DAY, END, HOUR, START


@pytest.fixture
def flat_asset():
    def bar(t, interval, mark=False):
        return [t, "100", "100", "100", "100", "100000", t + interval - 1, "10000000"]

    return {
        "spot_daily": {t: bar(t, DAY) for t in range(START, END + DAY, DAY)},
        "perp_daily": {t: bar(t, DAY) for t in range(START, END + DAY, DAY)},
        "mark_hourly": {t: bar(t, HOUR) for t in range(START, END + HOUR, HOUR)},
        "funding": [
            {"fundingTime": t, "fundingRate": "0", "markPrice": "100", "symbol": "BTCUSDT"}
            for t in range(START, END, 8 * HOUR)
        ],
        "step": Decimal("0.001"),
        "filters": {
            k: {"min_qty": 0.001, "max_qty": 1000, "min_notional": 5} for k in ("spot", "perp")
        },
    }


def cost(**kwargs):
    return {
        "spot_fee_bps_side": 0,
        "perp_fee_bps_side": 0,
        "slippage_bps_each_leg": 0,
        "annual_residual_usdt": 0,
        "positive_funding_multiplier": 1,
        "entry_unhedged_shock_fraction_notional": 0,
    } | kwargs


def test_equal_hedge_flat_prices_cannot_manufacture_profit(flat_asset):
    result = simulate(
        flat_asset,
        carry_decisions(flat_asset, "AR1"),
        cost(spot_fee_bps_side=10, perp_fee_bps_side=5, slippage_bps_each_leg=5),
    )
    assert result["profit_usdt_mechanical"] == pytest.approx(-6.25)
    assert result["round_trip_hedges"] == 1
    assert result["leg_transactions"] == 4
    assert sum(r["pnl_usdt"] for r in result["weekly"]) == pytest.approx(-6.25)
    assert sum(r["pnl_usdt"] for r in result["by_year"].values()) == pytest.approx(-6.25)


def test_delta_neutral_portfolio_can_still_fail_separate_margin(flat_asset):
    for k in ("spot_daily", "perp_daily", "mark_hourly"):
        for t, row in flat_asset[k].items():
            if t >= ENTRY + DAY:
                row[1:5] = ["410"] * 4
    result = simulate(flat_asset, carry_decisions(flat_asset, "AR1"), cost())
    assert result["profit_usdt_mechanical"] == pytest.approx(0)
    assert result["first_conservative_margin_breach"] is not None
    assert result["executable_net_profit"] is None
    assert result["minimum_hourly_collateral_surplus_usdt"] < 0


def test_entry_hour_funding_is_not_free_income_and_exit_event_excluded(flat_asset):
    for r in flat_asset["funding"]:
        r["fundingRate"] = "0.0001"
    plan = carry_decisions(flat_asset, "AR1")
    result = simulate(flat_asset, plan, cost())
    expected_count = (END - ENTRY) // (8 * HOUR) - 1
    assert result["spells"][0]["settlements"] == expected_count
    assert result["funding_usdt"] == pytest.approx(expected_count * 1250 * 0.0001)


def test_compression_never_forgives_negative_funding(flat_asset):
    for index, row in enumerate(flat_asset["funding"]):
        row["fundingRate"] = "-0.0001" if index % 2 else "0.0001"
    plan = carry_decisions(flat_asset, "AR1")
    base, stress = [
        simulate(flat_asset, plan, cost(positive_funding_multiplier=m)) for m in (1, 0.5)
    ]
    assert (
        stress["spells"][0]["negative_funding_usdt"] == base["spells"][0]["negative_funding_usdt"]
    )
    assert stress["spells"][0]["positive_funding_usdt"] == pytest.approx(
        0.5 * base["spells"][0]["positive_funding_usdt"]
    )
    assert stress["ending_usdt_mechanical"] < base["ending_usdt_mechanical"]


def test_future_or_recent_funding_cannot_change_entry_signal(flat_asset):
    before = past_funding_signal(flat_asset["funding"], ENTRY)
    for r in flat_asset["funding"]:
        if r["fundingTime"] >= ENTRY - DAY:
            r["fundingRate"] = "100"
    assert past_funding_signal(flat_asset["funding"], ENTRY) == before
    assert not carry_decisions(flat_asset, "AR2")[0]["enter"]


def test_missing_funding_bucket_is_not_filled(flat_asset):
    rows = [r for r in flat_asset["funding"] if r["fundingTime"] != ENTRY - 2 * DAY]
    assert past_funding_signal(rows, ENTRY)[0] is None


def test_rolling_spells_close_then_reopen_and_cashflows_reconcile(flat_asset):
    for row in flat_asset["funding"]:
        row["fundingRate"] = "0.0002"
    result = simulate(
        flat_asset,
        carry_decisions(flat_asset, "AR2"),
        cost(spot_fee_bps_side=10, annual_residual_usdt=25),
    )
    assert result["round_trip_hedges"] == 35
    assert result["cash_weeks"] == 0
    assert result["spells"][0]["exit_ms"] == result["spells"][1]["entry_ms"]
    assert sum(
        s["net_trading_pnl_usdt"] for s in result["spells"]
    ) - 25 * 980 / 365 == pytest.approx(result["profit_usdt_mechanical"])


def test_no_trade_has_no_profit_no_residual_cost_or_win_rate(flat_asset):
    result = simulate(flat_asset, carry_decisions(flat_asset, "AR2"), cost(annual_residual_usdt=25))
    assert result["profit_usdt_mechanical"] == 0
    assert result["residual_cost_usdt"] == 0
    assert result["cash_weeks"] == 140
    assert result["bootstrap"]["interval_95_usdt"] is None


def test_reserve_stress_cannot_use_spot_gains_or_positive_future_funding():
    assert hourly_surplus(3750, -10, 12.5, 100, 200) == pytest.approx(2452.5)
    assert hourly_surplus(3750, -10, 12.5, 100, 200, 0.3) < hourly_surplus(
        3750, -10, 12.5, 100, 200
    )


def test_quantity_satisfies_both_grids_and_never_exceeds_budget():
    step = common_step("0.003", "0.002")
    assert step == Decimal("0.006")
    q = rounded_quantity(1250, 42765.4, step)
    assert Decimal(str(q)) % Decimal("0.003") == 0
    assert Decimal(str(q)) % Decimal("0.002") == 0
    assert q * 42765.4 <= 1250


def test_spot_future_outcomes_cannot_select_assets():
    length = (DATE_END - BASE).days
    close = np.linspace(100, 200, length)
    bars = np.column_stack(
        (close, close * 1.01, close * 0.99, close, np.ones(length) * 1e5, np.ones(length) * 1e7)
    )
    data = {"BTCUSDT": bars.copy()} | {f"COIN{x:02}USDT": bars.copy() for x in range(12)}
    expected = momentum_decisions(data)[0]
    assert len(expected["selected"]) == 5
    modified = deepcopy(data)
    index = (ENTRY // DAY) - (BASE - __import__("datetime").date(1970, 1, 1)).days
    for x in modified.values():
        x[index - 1 :] = np.nan
    assert momentum_decisions(modified)[0] == expected


def test_selected_missing_asset_retains_allocation():
    holdings = [{"gross_return": None, "sell_legs": 1}, {"gross_return": 0.1, "sell_legs": 1}]
    assert portfolio_factor(holdings, 10) is None
    assert portfolio_factor(holdings, 10, "total_loss") < portfolio_factor(
        holdings, 10, "flat_gross"
    )


def test_bootstrap_is_deterministic_and_cash_is_not_evidence():
    assert block_interval([0.0] * 140)["interval_95_usdt"] is None
    values = [10.0, -2, 0, -1] * 35
    assert block_interval(values) == block_interval(values)
