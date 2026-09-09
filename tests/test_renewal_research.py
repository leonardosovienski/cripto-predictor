"""Synthetic checks for cash accounting and the scope of renewal bounds."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from GarimpoInvestimentos.renewal_research import renewal_bound

DAY = 86_400_000
IDS = ["TEST:SPOT:BTCUSDT:USDT", "TEST:PERP:BTCUSDT:USDT"]


def fixture(second_quantity=1, gap=0, funding_rate="0"):
    spells = []
    for entry, exit_, quantity in [(0, DAY, 1), (DAY + gap, 2 * DAY + gap, second_quantity)]:
        execution = Decimal(str(quantity)) * Decimal("0.2")
        spells.append(
            {
                "entry_ms": entry,
                "exit_ms": exit_,
                "quantity": str(quantity),
                "instruments": IDS.copy(),
                "spot_entry": "100",
                "spot_exit": "100",
                "perp_entry": "100",
                "perp_exit": "100",
                "entry_cost_usdt": str(execution),
                "exit_cost_usdt": str(execution),
                "basis_pnl_usdt": "0",
                "funding_usdt": "0",
                "unhedged_shock_usdt": "0",
            }
        )
    fees = sum(Decimal(row["entry_cost_usdt"]) * 2 for row in spells)
    return {
        "currency": "USDT",
        "evidence_ref": "SYNTHETIC ONLY",
        "instruments": IDS.copy(),
        "start_ms": 0,
        "end_ms": 2 * DAY + gap,
        "quantity_step": "0.1",
        "costs": {
            "spot_fee_bps_side": 10,
            "perp_fee_bps_side": 10,
            "slippage_bps_each_leg": 0,
            "positive_funding_multiplier": 1,
            "entry_unhedged_shock_fraction_notional": 0,
            "annual_residual_usdt": 0,
        },
        "spells": spells,
        "funding_events": [
            {"fundingTime": DAY + gap, "fundingRate": funding_rate, "markPrice": "100"}
        ],
        "reference": {
            "initial_usdt": "5000",
            "ending_usdt_mechanical": str(5000 - fees),
            "profit_usdt_mechanical": str(-fees),
            "funding_usdt": "0",
            "basis_pnl_usdt": "0",
            "fees_slippage_usdt": str(fees),
            "residual_cost_usdt": "0",
            "unhedged_shock_usdt": "0",
        },
    }


def test_same_quantity_saves_only_adjacent_turnover_not_initial_or_final_costs():
    result = renewal_bound(fixture())
    assert result["adjacent_renewals"] == 1
    assert Decimal(result["delta_turnover_savings_only"]) == Decimal("0.4")
    assert Decimal(result["extended_optimistic_upper_bound_not_profit"]) == Decimal("-0.4")
    assert result["upper_bound_still_nonpositive"]
    assert result["net"] is None and result["capital_permission"] is False


@pytest.mark.parametrize("quantity", ["0.5", "1.5"])
def test_quantity_change_keeps_the_delta_cost_and_zero_cost_is_only_an_upper_bound(quantity):
    result = renewal_bound(fixture(quantity))
    renewal = result["renewals"][0]
    assert Decimal(renewal["delta_only_cost"]) == Decimal("0.1")
    assert Decimal(result["partial_remainder_with_delta_costs_only"]) < Decimal(
        result["zero_renewal_execution_cost_upper_bound"]
    )
    assert Decimal(renewal["delta_only_savings"]) == Decimal("0.4") * min(
        Decimal(quantity), Decimal(1)
    )


def test_gap_between_trades_cannot_save_entry_or_exit_costs():
    result = renewal_bound(fixture(gap=DAY))
    assert result["adjacent_renewals"] == 0
    assert Decimal(result["delta_turnover_savings_only"]) == 0
    assert (
        result["reference_partial_remainder"]
        == result["extended_optimistic_upper_bound_not_profit"]
    )


def test_negative_renewal_boundary_funding_remains_visible_not_positive_income():
    result = renewal_bound(fixture(funding_rate="-0.01"))
    renewal = result["renewals"][0]
    assert Decimal(renewal["additional_negative_boundary_diagnostic"]) == -1
    assert Decimal(renewal["signed_continuity_boundary_diagnostic"]) == -1
    assert Decimal(renewal["optimistic_extra_positive_boundary_funding"]) == 0
    assert Decimal(result["extended_optimistic_upper_bound_not_profit"]) == Decimal("-0.4")


def test_positive_boundary_upper_bound_uses_larger_quantity_but_diagnostic_uses_continuous_part():
    result = renewal_bound(fixture(second_quantity="1.5", funding_rate="0.01"))
    assert Decimal(result["renewals"][0]["optimistic_extra_positive_boundary_funding"]) == Decimal(
        "1.5"
    )
    assert Decimal(result["renewals"][0]["signed_continuity_boundary_diagnostic"]) == 1
    assert result["net"] is None


@pytest.mark.parametrize(
    "field",
    [
        "funding_usdt",
        "basis_pnl_usdt",
        "fees_slippage_usdt",
        "profit_usdt_mechanical",
        "ending_usdt_mechanical",
        "residual_cost_usdt",
    ],
)
def test_inconsistent_cash_and_principal_are_rejected(field):
    spec = fixture()
    spec["reference"][field] = str(Decimal(spec["reference"][field]) + 1)
    with pytest.raises(ValueError, match="accounting mismatch"):
        renewal_bound(spec)


def test_funding_reconstruction_rejects_a_plausible_but_unbacked_receipt():
    spec = fixture()
    spec["spells"][0]["funding_usdt"] = "10"
    for field in ("funding_usdt", "profit_usdt_mechanical", "ending_usdt_mechanical"):
        spec["reference"][field] = str(Decimal(spec["reference"][field]) + 10)
    with pytest.raises(ValueError, match="signed funding"):
        renewal_bound(spec)


@pytest.mark.parametrize(
    "mutation",
    [
        "venue",
        "price",
        "grid",
        "overlap",
        "funding_duplicate",
        "funding_unsorted",
        "funding_nan",
        "negative_cost",
        "currency",
    ],
)
def test_invalid_netting_and_market_inputs_are_rejected(mutation):
    spec = deepcopy(fixture())
    if mutation == "venue":
        spec["spells"][1]["instruments"][1] = "OTHER:PERP:BTCUSDT:USDT"
    elif mutation == "price":
        spec["spells"][1]["perp_entry"] = "101"
    elif mutation == "grid":
        spec["quantity_step"] = "0.3"
    elif mutation == "overlap":
        spec["spells"][1]["entry_ms"] = 0
    elif mutation == "funding_duplicate":
        spec["funding_events"] *= 2
    elif mutation == "funding_unsorted":
        spec["funding_events"].append({"fundingTime": 0, "fundingRate": "0", "markPrice": "100"})
    elif mutation == "funding_nan":
        spec["funding_events"][0]["fundingRate"] = "NaN"
    elif mutation == "negative_cost":
        spec["costs"]["spot_fee_bps_side"] = -1
    else:
        spec["currency"] = "USDC"
    with pytest.raises(ValueError):
        renewal_bound(spec)


def test_fixed_expenses_cannot_disappear_in_scale_scenarios():
    spec = fixture()
    spec["costs"]["annual_residual_usdt"] = 365
    spec["reference"]["residual_cost_usdt"] = "2"
    for field in ("profit_usdt_mechanical", "ending_usdt_mechanical"):
        spec["reference"][field] = str(Decimal(spec["reference"][field]) - 2)
    result = renewal_bound(spec)
    assert Decimal(result["extended_optimistic_upper_bound_not_profit"]) == Decimal("-2.4")
    assert Decimal(
        result["capital_sensitivities"][0]["optimistic_scale_only_remainder_usdt"]
    ) == Decimal("-2.08")


def test_reconciled_ledgers_with_different_boundary_prices_cannot_be_netted():
    spec = fixture()
    spec["spells"][1]["perp_entry"] = "101"
    spec["spells"][1]["entry_cost_usdt"] = "0.201"
    spec["spells"][1]["basis_pnl_usdt"] = "1"
    spec["reference"]["basis_pnl_usdt"] = "1"
    spec["reference"]["fees_slippage_usdt"] = "0.801"
    spec["reference"]["profit_usdt_mechanical"] = "0.199"
    spec["reference"]["ending_usdt_mechanical"] = "5000.199"
    with pytest.raises(ValueError, match="Renewal prices differ"):
        renewal_bound(spec)


def test_existing_negative_funding_is_retained_even_in_the_optimistic_bound():
    spec = fixture()
    spec["costs"]["positive_funding_multiplier"] = "0.5"
    spec["funding_events"].insert(
        0, {"fundingTime": 8 * 3_600_000, "fundingRate": "-0.01", "markPrice": "100"}
    )
    spec["spells"][0]["funding_usdt"] = "-1"
    spec["reference"]["funding_usdt"] = "-1"
    spec["reference"]["profit_usdt_mechanical"] = "-1.8"
    spec["reference"]["ending_usdt_mechanical"] = "4998.2"
    result = renewal_bound(spec)
    assert Decimal(result["accounting"]["funding"]) == -1
    assert Decimal(result["extended_optimistic_upper_bound_not_profit"]) == Decimal("-1.4")
