from datetime import timedelta
from fractions import Fraction

import pytest

from scripts import recover_aave_history as aave


class Headers:
    def __init__(self):
        self.calls = 0

    def header(self, n):
        self.calls += 1
        return {
            "number": n,
            "timestamp": n // 4,
            "hash": "0x" + f"{n:064x}",
            "parent_hash": "0x" + f"{n - 1:064x}",
        }


def test_last_block_of_repeated_l2_timestamp():
    rpc = Headers()
    before, after = aave.boundary(rpc, 100, 1, 10000)
    assert before["number"] == 403 and after["number"] == 404
    assert rpc.calls < 40


def test_reject_missing_bracket_and_fork():
    rpc = Headers()
    with pytest.raises(ValueError):
        aave.boundary(rpc, 100, 500, 10000)
    original = rpc.header
    rpc.header = lambda n: {**original(n), "parent_hash": "0x" + "f" * 64}
    with pytest.raises(ValueError):
        aave.boundary(rpc, 100, 1, 10000)


def history():
    return [
        {
            "boundary_utc": (aave.START + timedelta(days=7 * i)).isoformat(),
            "normalized_income_ray": str(aave.RAY + i * aave.RAY // 1200),
            "unborrowed_liquidity_units": str(1000000 * 10**6),
            "scaled_supply_units": str(1000000 * 10**6),
            "supply_cap_tokens": "2000000",
            "active": True,
            "paused": False,
            "frozen": False,
        }
        for i in range(13)
    ]


def test_independent_integer_accounting_and_costs():
    rows = history()
    result = aave.calculate(rows)
    for case in result["cases"]:
        c = case["capital_usdc"]
        expected = Fraction(c) * (
            Fraction(int(rows[-1]["normalized_income_ray"]), int(rows[0]["normalized_income_ray"]))
            - 1
        )
        assert float(case["gross_interest_usdc"]) == pytest.approx(float(expected), abs=0.000002)
        assert float(case["partial_remainder_usdc"]) == pytest.approx(
            float(expected) - case["entry_exit_cost_scenario_usdc"]
        )
        assert case["all_in_personal_profit"] is None


def test_insufficient_liquidity_and_paused_reserve_do_not_become_executable():
    rows = history()
    rows[6]["unborrowed_liquidity_units"] = "0"
    rows[8]["paused"] = True
    rows[0]["frozen"] = True
    for case in aave.calculate(rows)["cases"]:
        assert not case["unborrowed_liquidity_sufficient_at_all_boundaries"]
        assert not case["entry_configuration_allows_supply"]
        assert not case["withdrawal_configuration_at_boundaries"]


def test_missing_or_different_period_refused():
    rows = history()
    with pytest.raises(ValueError):
        aave.calculate(rows[:-1])
    rows[0]["boundary_utc"] = (aave.START - timedelta(days=1)).isoformat()
    with pytest.raises(ValueError):
        aave.calculate(rows)


def test_unknown_operator_costs_have_explicit_sensitivity_not_zero_assumption():
    cases = aave.calculate(history(), ["0", "7.25"])["cases"]
    for case in cases:
        scenarios = case["additional_total_cost_scenarios_usdc"]
        assert float(scenarios["0"]) - float(scenarios["7.25"]) == pytest.approx(7.25)
        assert case["all_in_personal_profit"] is None
    for values in (["NaN"], ["Infinity"], ["-1"], []):
        with pytest.raises(ValueError):
            aave.calculate(history(), values)


@pytest.mark.parametrize("data", ["0x1", "garbage", "0x" + "a" * 63, "0x" + "z" * 64])
def test_invalid_abi(data):
    with pytest.raises(ValueError):
        aave.words(data)
