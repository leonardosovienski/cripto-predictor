import copy

import pytest

from scripts.plan_btc_hedge import net_hedge_plan as legacy_plan
from scripts.plan_btc_hedge_v2 import net_hedge_plan, validate_sample


def inputs():
    book = {"asks": [["1001", "10"]], "bids": [["999", "10"]]}
    sf = dict(step="0.00001", min_qty=0.00001, max_qty=100, min_notional=5, status="TRADING")
    ff = dict(step="0.001", min_qty=0.001, max_qty=100, min_notional=50, status="TRADING")
    return book, copy.deepcopy(book), sf, ff


def test_valid_economic_calculation_is_unchanged():
    values = inputs()
    assert net_hedge_plan(*values, 8) == legacy_plan(*values, 8)


@pytest.mark.parametrize("venue", [0, 1])
@pytest.mark.parametrize("bid", ["1001", "1100"])
def test_locked_or_crossed_book_cannot_produce_plan(venue, bid):
    values = inputs()
    values[venue]["bids"][0][0] = bid
    with pytest.raises(ValueError, match="Crossed or locked"):
        net_hedge_plan(*values, 8)


@pytest.mark.parametrize("side", ["bids", "asks"])
@pytest.mark.parametrize("bad_level", [["NaN", "10"], ["1000", "-1"], ["1000"], ["0", "10"]])
def test_all_levels_are_validated_even_beyond_needed_fill(side, bad_level):
    values = inputs()
    values[0][side].append(bad_level)
    with pytest.raises(ValueError):
        net_hedge_plan(*values, 8)


@pytest.mark.parametrize("key,value", [("step", "0"), ("max_qty", "NaN"), ("min_notional", -1)])
def test_invalid_lot_constraints_are_rejected(key, value):
    values = inputs()
    values[2][key] = value
    with pytest.raises(ValueError):
        net_hedge_plan(*values, 8)


def test_unordered_unused_book_side_is_rejected():
    values = inputs()
    values[1]["asks"].append(["1000", "10"])
    with pytest.raises(ValueError, match="Unordered"):
        net_hedge_plan(*values, 8)


@pytest.mark.parametrize("case", ["failed", "flag", "duration", "skew", "reverse_time"])
def test_failed_or_stale_sample_cannot_be_reused(case):
    sample = {"freshness_pass": True, "error": None}
    sm = {"status": 200, "request_start_ns": 0, "received_ns": 100_000_000}
    fm = sm.copy()
    if case == "failed":
        sample["error"] = "failed prior diagnostic"
    elif case == "flag":
        sample["freshness_pass"] = False
    elif case == "duration":
        sm["received_ns"] = 2_000_000_001
    elif case == "skew":
        fm.update(request_start_ns=1_000_000_000, received_ns=1_100_000_000)
    else:
        sm["request_start_ns"] = 200_000_000
    with pytest.raises(ValueError):
        validate_sample(sample, sm, fm)


def test_timely_successful_pair_passes():
    meta = {"status": 200, "request_start_ns": 0, "received_ns": 100_000_000}
    validate_sample({"freshness_pass": True, "error": None}, meta, meta)
