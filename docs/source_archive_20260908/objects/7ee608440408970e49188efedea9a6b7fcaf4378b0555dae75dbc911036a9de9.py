"""Quantity conservation, censoring and payoff controls; no alpha claims."""

from datetime import date

import pytest

from scripts.prepare_altcoin_payoff import (
    adjusted_gross,
    exact_close,
    is_known_leveraged_symbol,
    net_factor,
    payoff_summary,
    repair_samples,
)


@pytest.mark.parametrize(
    "entry,close,ratio",
    [("0.01", "10", "0.001"), ("0.2", "0.02", "10"), ("0.002", "0.000002", "1000")],
)
def test_redenomination_alone_does_not_create_gain_or_loss(entry, close, ratio):
    assert adjusted_gross(entry, close, ratio) == 0


def test_cross_quote_uses_observed_conversion_instead_of_assumed_peg():
    assert adjusted_gross("100", "100", "1", "0.9") == pytest.approx(-0.1)
    assert net_factor(0, 2) < net_factor(0, 1)


def test_later_listing_cannot_fill_earlier_missing_exit():
    row = [1643068800000, "1", "1", "1", "1", "100", 1643155199999]
    assert exact_close([row], date(2022, 1, 23)) is None
    assert exact_close([row], date(2022, 1, 25)) == "1"


def test_censored_neighbor_forces_abstention_instead_of_silent_removal():
    neighbors = [{"date": f"week-{i}", "gross_return": 0.2} for i in range(200)]
    neighbors[99]["gross_return"] = None
    result = payoff_summary(neighbors)
    assert result["status"] == "ABSTAIN_CENSORED_NEIGHBOR"
    assert not result["qualified"]


def test_many_coins_in_one_week_are_not_many_independent_weeks():
    result = payoff_summary([{"date": "one-week", "gross_return": 0.9}] * 200)
    assert result["status"] == "ABSTAIN_TOO_FEW_DISTINCT_WEEKS"


def test_net_payoff_rejects_lottery_with_negative_expected_wealth():
    # In every independent week, two 30% winners and eight 20% losers.
    neighbors = [
        {"date": f"week-{w}", "gross_return": 0.3 if k < 2 else -0.2}
        for w in range(20)
        for k in range(10)
    ]
    assert not payoff_summary(neighbors)["qualified"]


def test_positive_control_can_qualify_and_fee_only_case_cannot():
    neighbors = [{"date": f"week-{i // 5}", "gross_return": 0.02} for i in range(200)]
    assert payoff_summary(neighbors)["qualified"]
    for row in neighbors:
        row["gross_return"] = 0.0
    assert not payoff_summary(neighbors)["qualified"]


def test_legitimate_names_ending_in_up_are_not_leveraged_products():
    assert not is_known_leveraged_symbol("JUPUSDT")
    assert not is_known_leveraged_symbol("SYRUPUSDT")
    assert is_known_leveraged_symbol("BTCUPUSDT")
    assert is_known_leveraged_symbol("ETHBEARUSDT")


def test_repair_preserves_original_evidence_and_censored_observations():
    original = [
        {
            "symbol": "XUSDT",
            "date": "2021-01-04",
            "period": "train",
            "gross_return": -1,
            "target": 0,
            "missing_outcome": "missing",
            "btc_gross_return": 0,
        }
    ]
    repaired = repair_samples(
        original,
        [
            {
                "symbol": "XUSDT",
                "entry": "2021-01-04",
                "gross_return": None,
                "sell_legs": 1,
                "status": "CENSORED",
            }
        ],
    )
    assert len(repaired) == 1
    assert original[0]["gross_return"] == -1
    assert repaired[0]["gross_return"] is None
    assert repaired[0]["target"] is None
    assert repaired[0]["gross_return_original_stress"] == -1
