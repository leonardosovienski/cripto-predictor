from decimal import Decimal

import pytest

from scripts.plan_btc_hedge import net_hedge_plan


def inputs(price=79340):
    book = {"asks": [[str(price + 1), "10"]], "bids": [[str(price - 1), "10"]]}
    sf = dict(step="0.00001", min_qty=0.00001, max_qty=100, min_notional=5, status="TRADING")
    ff = dict(step="0.001", min_qty=0.001, max_qty=100, min_notional=50, status="TRADING")
    return book, sf, ff


@pytest.mark.parametrize("price", [1000, 42283, 79340, 150000])
def test_net_quantity_matches_hedge_without_large_dust(price):
    book, sf, ff = inputs(price)
    plan = net_hedge_plan(book, book, sf, ff, 8)
    d = lambda key: Decimal(plan[key])
    assert d("spot_outlay_usdt") <= 1250
    assert d("net_received_btc") >= d("future_short_btc")
    assert d("unhedged_dust_btc") < Decimal("0.00001001")
    assert d("gross_spot_buy_btc") - d("spot_commission_btc_assumed") == d("net_received_btc")
    assert plan["orders_sent"] == 0


def test_unavailable_depth_or_market_is_not_a_feasible_plan():
    book, sf, ff = inputs()
    book["asks"][0][1] = "0.00001"
    with pytest.raises(ValueError):
        net_hedge_plan(book, book, sf, ff, 8)
    book, sf, ff = inputs()
    ff["status"] = "BREAK"
    with pytest.raises(ValueError):
        net_hedge_plan(book, book, sf, ff, 8)
