"""Economic identities, temporal boundaries and incomplete execution evidence."""

import copy

import pytest

from scripts.backtest_btc_basis import (
    lagged_basis,
    make_plan,
    settlement_price,
    simulate,
    trade_cost,
)
from scripts.basis_data import END, ENTRY, HOUR, START, contracts, normalize_bars, protocol
from scripts.diagnose_btc_execution import common_grid, estimate, walk

ZERO = dict(
    spot_fee_bps=0,
    future_fee_bps=0,
    slippage_bps=0,
    settlement_fee_bps=0,
    annual_residual_usdt=0,
    positive_funding_multiplier=1,
    entry_mismatch_fraction=0,
)


def candle(t, price):
    return [t, str(price), str(price), str(price), str(price), "1000", t + HOUR - 1, "1000000"]


def fixture(end=ENTRY + 12 * HOUR):
    spot = {t: candle(t, 1000) for t in range(START, end + HOUR, HOUR)}
    future = {t: candle(t, 1030) for t in range(START, end + HOUR, HOUR)}
    return {
        "spot": spot,
        "perp": copy.deepcopy(future),
        "mark": copy.deepcopy(future),
        "X_trade": copy.deepcopy(future),
        "X_mark": copy.deepcopy(future),
        "funding": [],
        "delivery": [{"deliveryTime": ENTRY, "deliveryPrice": "1000"}],
    }


def direct_plan(dated=False, exit_time=ENTRY + 8 * HOUR):
    return {
        "id": "BR1_DATED_BTC" if dated else "BR2_CONVERGENCE_BTC",
        "spells": [
            {
                "symbol": "X" if dated else "BTCUSDT",
                "entry_ms": ENTRY,
                "exit_ms": exit_time,
                "expiry_ms": exit_time if dated else None,
                "exit_reason": "SETTLEMENT" if dated else "CONVERGED",
            }
        ],
    }


@pytest.mark.parametrize("terminal", [600, 1400])
def test_dated_locked_payoff_both_directions(terminal):
    data = fixture()
    data["spot"][ENTRY + 8 * HOUR] = candle(ENTRY + 8 * HOUR, terminal)
    data["delivery"][0]["deliveryPrice"] = str(terminal)
    result = simulate(data, direct_plan(True), ZERO, ENTRY + 12 * HOUR)
    assert result["summary"]["profit_usdt"] == pytest.approx(1.25 * 30)
    assert result["spells"][0]["settlement_record_date_ms"] == ENTRY
    assert result["spells"][0]["exit_ms"] == ENTRY + 8 * HOUR


def test_spot_settlement_mismatch_is_not_erased():
    data = fixture()
    data["delivery"][0]["deliveryPrice"] = "1010"
    result = simulate(data, direct_plan(True), ZERO, ENTRY + 12 * HOUR)
    assert result["summary"]["profit_usdt"] == pytest.approx(1.25 * 20)


def test_settlement_not_exposed_at_date_label():
    with pytest.raises(ValueError):
        settlement_price(fixture(), ENTRY)


@pytest.mark.parametrize("missing", ["settlement", "mark", "spot_exit"])
def test_missing_held_outcome_is_unknown(missing):
    data = fixture()
    if missing == "settlement":
        data["delivery"] = []
    elif missing == "mark":
        del data["X_mark"][ENTRY + HOUR]
    else:
        del data["spot"][ENTRY + 8 * HOUR]
    result = simulate(data, direct_plan(True), ZERO, ENTRY + 12 * HOUR)
    assert result["summary"]["profit_usdt"] is None
    assert result["summary"]["status"] == "UNKNOWN_HELD_OUTCOME"


def test_funding_boundaries_and_asymmetric_stress():
    data = fixture()
    for hour, rate in [(0, 0.9), (1, 0.01), (2, -0.02), (8, 0.9)]:
        data["funding"].append(
            {"fundingTime": ENTRY + hour * HOUR, "markPrice": "1000", "fundingRate": str(rate)}
        )
    result = simulate(
        data, direct_plan(), ZERO | {"positive_funding_multiplier": 0.5}, ENTRY + 12 * HOUR
    )
    assert result["summary"]["funding_usdt"] == pytest.approx(1.25 * 1000 * (0.005 - 0.02))
    assert len(result["funding"]) == 2


def test_margin_breach_does_not_become_profitable_executable_result():
    data = fixture()
    data["mark"][ENTRY + HOUR][2] = "10000"
    result = simulate(data, direct_plan(), ZERO, ENTRY + 12 * HOUR)["summary"]
    assert result["profit_usdt"] == pytest.approx(0)
    assert not result["margin_pass"]
    assert result["attainable_result_if_margin_breach"] is None


def test_positive_current_hour_funding_cannot_finance_earlier_high():
    data = fixture()
    data["mark"][ENTRY + HOUR][2] = "5000"
    data["funding"] = [{"fundingTime": ENTRY + HOUR, "markPrice": "1000", "fundingRate": "10"}]
    result = simulate(data, direct_plan(), ZERO, ENTRY + 12 * HOUR)["summary"]
    assert not result["margin_pass"]


def test_residual_continues_after_exit():
    data = fixture()
    result = simulate(
        data, direct_plan(), ZERO | {"annual_residual_usdt": 8760}, ENTRY + 12 * HOUR
    )["summary"]
    assert result["residual_usdt"] == pytest.approx(12)
    assert result["profit_usdt"] == pytest.approx(-12)


def test_market_and_settlement_costs_differ_only_in_future_close():
    cost = protocol()["costs"]["adverse"]
    assert trade_cost(2, 1000, 1100, cost) == pytest.approx(14.6)
    assert trade_cost(2, 1000, 1100, cost, True) == pytest.approx(10.2)


def test_signal_has_full_hour_delay():
    data = fixture()
    data["perp"][ENTRY - HOUR][4] = "5000"
    data["perp"][ENTRY][4] = "9000"
    assert lagged_basis(data["spot"], data["perp"], ENTRY) == pytest.approx(0.03)


def test_future_prices_do_not_change_earlier_entry_decision():
    data = fixture()
    rule = protocol()["streams"][1]
    original = make_plan(data, rule, ENTRY + 12 * HOUR)
    mutated = copy.deepcopy(data)
    for t in range(ENTRY, ENTRY + 13 * HOUR, HOUR):
        mutated["perp"][t] = candle(t, 500)
        mutated["spot"][t][7] = "0"
    changed = make_plan(mutated, rule, ENTRY + 12 * HOUR)
    assert original["decisions"][0] == changed["decisions"][0]
    assert original["spells"][0]["entry_ms"] == changed["spells"][0]["entry_ms"]
    assert changed["spells"][0]["exit_ms"] == ENTRY + 2 * HOUR


def test_no_forced_entry_on_small_basis():
    data = fixture()
    data["perp"] = copy.deepcopy(data["spot"])
    plan = make_plan(data, protocol()["streams"][1], ENTRY + 12 * HOUR)
    assert plan["spells"] == []
    result = simulate(data, plan, protocol()["costs"]["stress"], ENTRY + 12 * HOUR)["summary"]
    assert result["profit_usdt"] == 0
    assert result["residual_usdt"] == 0


def test_missing_lagged_liquidity_prevents_entry():
    data = fixture()
    del data["spot"][START]
    assert not make_plan(data, protocol()["streams"][1], ENTRY + 12 * HOUR)["spells"]


def test_earliest_eligible_dated_contract_is_not_replaced_after_gate_failure(monkeypatch):
    data = fixture()
    data["X_trade"] = copy.deepcopy(data["spot"])
    data["Y_trade"] = copy.deepcopy(data["perp"])
    monkeypatch.setattr(
        "scripts.backtest_btc_basis.contracts",
        lambda: {"X": ENTRY + 40 * 24 * HOUR, "Y": ENTRY + 90 * 24 * HOUR},
    )
    plan = make_plan(data, protocol()["streams"][0], ENTRY + 12 * HOUR)
    assert plan["decisions"][0]["symbol"] == "X"
    assert not plan["spells"]


def test_cutoff_close_and_microseconds_do_not_leak():
    row = candle(ENTRY, 1000)
    row[0] *= 1000
    row[6] = row[6] * 1000 + 999
    assert normalize_bars([row])[0][0] == ENTRY
    final = candle(END, 1000)
    final[2:5] = ["999999", "0", "999999"]
    assert normalize_bars([final]) == [[END, "1000"]]


def test_conflicting_raw_rows_rejected():
    with pytest.raises(ValueError):
        normalize_bars([candle(ENTRY, 1000), candle(ENTRY, 999)])


def test_expiry_calendar_is_not_current_survivors():
    result = contracts()
    assert len(result) == 12
    assert "BTCUSDT_240329" in result and "BTCUSDT_261225" in result
    assert all(t % (24 * HOUR) == 8 * HOUR for t in result.values())


def test_book_walk_and_insufficient_liquidity():
    assert walk([["100", "1"], ["102", "1"]], 1.5, True) == pytest.approx(100 + 2 / 3)
    with pytest.raises(ValueError):
        walk([["100", "1"]], 1.5, True)
    with pytest.raises(ValueError):
        walk([["100", "1"], ["99", "1"]], 1, True)


def test_fee_in_base_creates_rounding_dust():
    book = {"bids": [["999", "10"]], "asks": [["1001", "10"]]}
    filters = dict(step="0.001", min_qty=0.001, max_qty=100, min_notional=5, status="TRADING")
    row = estimate(book, book, filters, filters)
    alternative = row["spot_fee_in_btc_alternative"]
    assert alternative["received_btc"] < alternative["gross_spot_btc"]
    assert 0 <= alternative["unhedged_dust_btc"] < 0.001
    assert not row["simultaneous_execution_certified"]
    assert common_grid("0.002", "0.003") == "0.006"
