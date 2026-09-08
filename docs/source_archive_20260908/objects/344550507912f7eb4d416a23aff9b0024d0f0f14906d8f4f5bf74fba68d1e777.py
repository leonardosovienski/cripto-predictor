"""USDT shadow-account arithmetic; public quotes are never actual fills."""

from __future__ import annotations

from decimal import Decimal

from scripts.diagnose_btc_execution import common_grid
from scripts.plan_btc_hedge_v2 import number, validate_book, validate_filters
from scripts.plan_btc_hedge_v3 import walk_decimal
from scripts.research_io import integer

HOUR = 3_600_000
D = Decimal


def executable(snapshot, quantity, spot_price, future_price):
    for book in (snapshot["spot"], snapshot["future"]):
        validate_book(book)
    for constraints, price in ((snapshot["sf"], spot_price), (snapshot["ff"], future_price)):
        validate_filters(constraints)
        if (
            quantity % number(constraints["step"]) != 0
            or not number(constraints["min_qty"]) <= quantity <= number(constraints["max_qty"])
            or quantity * price < number(constraints["min_notional"])
        ):
            raise ValueError("Quote violates published lot or minimum constraint")


def cost(q, spot, future, scenario):
    return (
        q
        * (
            spot * number(scenario["spot_bps"] + scenario["extra_slippage_bps"])
            + future * number(scenario["future_bps"] + scenario["extra_slippage_bps"])
        )
        / 10000
    )


def opening(snapshot: dict, protocol: dict):
    q = (
        number(protocol["spot_budget_usdt"])
        / number(snapshot["spot"]["asks"][0][0])
        // number(common_grid(snapshot["sf"]["step"], snapshot["ff"]["step"]))
    ) * number(common_grid(snapshot["sf"]["step"], snapshot["ff"]["step"]))
    s = walk_decimal(snapshot["spot"]["asks"], q)
    f = walk_decimal(snapshot["future"]["bids"], q)
    if q * s > number(protocol["spot_budget_usdt"]):
        raise ValueError("Published entry depth exceeds fixed spot budget")
    executable(snapshot, q, s, f)
    cases = {}
    for name, scenario in protocol["costs"].items():
        fees = cost(q, s, f, scenario)
        mismatch = q * s * number(scenario["entry_mismatch_fraction"])
        cash = number(protocol["capital_usdt"]) - q * s - fees - mismatch
        if cash <= 0:
            raise ValueError("Insufficient modeled entry collateral")
        cases[name] = {
            "cash_after_entry": str(cash),
            "entry_cost_usdt": str(fees),
            "mismatch_usdt": str(mismatch),
        }
    return {
        "quantity_btc": str(q),
        "spot_entry": str(s),
        "future_entry": str(f),
        "entry_ms": snapshot["quote_ns"] // 1_000_000,
        "cases": cases,
        "fee_asset_assumption": "USDT-equivalent; actual account commission asset/rate unknown",
        "net_delta_btc_model": "0",
        "real_fills": False,
    }


def observations(funding, marks, entry_ms, cutoff_ms):
    first_hour, stop = entry_ms // HOUR * HOUR, cutoff_ms // HOUR * HOUR
    events = {}
    for row in funding:
        t = integer(row["fundingTime"], 1)
        if not first_hour + HOUR <= t < cutoff_ms or row["symbol"] != "BTCUSDT" or t in events:
            raise ValueError("Invalid or duplicate funding observation")
        mark = number(row["markPrice"])
        if mark <= 0:
            raise ValueError("Invalid funding mark")
        events[t] = (mark, number(row["fundingRate"]))
    first_due = (first_hour + HOUR + 8 * HOUR - 1) // (8 * HOUR)
    last_due = (cutoff_ms - 1) // (8 * HOUR)
    expected_buckets = set(range(first_due, last_due + 1))
    if not expected_buckets.issubset({t // (8 * HOUR) for t in events}):
        raise ValueError("Missing funding settlement bucket; profit unknown")
    high = {}
    for row in marks:
        if not isinstance(row, list) or len(row) < 7:
            raise ValueError("Invalid mark row shape")
        t = integer(row[0], 1)
        if t in high or not first_hour <= t < stop:
            raise ValueError("Invalid or duplicate completed mark hour")
        o, h, low, c = map(number, row[1:5])
        if (
            min(o, h, low, c) <= 0
            or h < max(o, c)
            or low > min(o, c)
            or low > h
            or integer(row[6], 1) != t + HOUR - 1
        ):
            raise ValueError("Invalid completed mark OHLC")
        high[t] = h
    if sorted(high) != list(range(first_hour, stop, HOUR)):
        raise ValueError("Missing completed mark hours; margin/profit observation unknown")
    return events, high


def valuation(entry, snapshot, funding, marks, protocol):
    start, end = integer(entry["entry_ms"], 1), snapshot["quote_ns"] // 1_000_000
    if end <= start:
        raise ValueError("Non-forward valuation time")
    events, highs = observations(funding, marks, start, end)
    q, s0, f0 = map(number, (entry["quantity_btc"], entry["spot_entry"], entry["future_entry"]))
    s = walk_decimal(snapshot["spot"]["bids"], q)
    f = walk_decimal(snapshot["future"]["asks"], q)
    executable(snapshot, q, s, f)
    cases = {}
    for name, scenario in protocol["costs"].items():
        flows = {
            t: q
            * mark
            * rate
            * (number(scenario["positive_funding_multiplier"]) if rate > 0 else 1)
            for t, (mark, rate) in events.items()
        }
        paid = sum(flows.values(), D(0))
        residual = number(scenario["annual_overhead_usdt"]) * D(end - start) / D(365 * 86400000)
        closing_cost = cost(q, s, f, scenario)
        original = entry["cases"][name]
        cash = number(original["cash_after_entry"])
        profit = (
            cash
            + paid
            - residual
            + q * s
            + q * (f0 - f)
            - closing_cost
            - number(protocol["capital_usdt"])
        )
        basis = q * (s - s0 + f0 - f)
        reconciled = (
            basis
            + paid
            - residual
            - number(original["entry_cost_usdt"])
            - closing_cost
            - number(original["mismatch_usdt"])
        )
        if abs(profit - reconciled) > D("0.00000001"):
            raise ValueError("Forward account does not reconcile")
        minimum, jumped, breaches = None, None, []
        for t, high in highs.items():
            overhead = (
                number(scenario["annual_overhead_usdt"])
                * D(max(0, t + HOUR - start))
                / D(365 * 86400000)
            )
            prior = sum((v for time, v in flows.items() if time < t), D(0))
            negative = sum((v for time, v in flows.items() if t <= time < t + HOUR and v < 0), D(0))
            for jump in (D(1), D("1.3")):
                price = high * jump
                surplus = (
                    cash - overhead + prior + negative + q * (f0 - price) - D("0.015") * q * price
                )
                if jump == 1:
                    minimum = surplus if minimum is None else min(minimum, surplus)
                else:
                    jumped = surplus if jumped is None else min(jumped, surplus)
                if surplus <= 0:
                    breaches.append({"hour_ms": t, "jump": str(jump)})
        cases[name] = {
            "modeled_liquidation_profit_usdt": str(profit),
            "basis_usdt": str(basis),
            "funding_usdt": str(paid),
            "entry_cost_usdt": original["entry_cost_usdt"],
            "exit_cost_usdt": str(closing_cost),
            "overhead_usdt": str(residual),
            "minimum_completed_hour_surplus_usdt": str(minimum) if minimum is not None else None,
            "minimum_completed_hour_jump_surplus_usdt": str(jumped) if jumped is not None else None,
            "margin_breaches": breaches,
            "complete_mark_hours": len(highs),
            "margin_checked_until_exclusive_ms": end // HOUR * HOUR,
            "actual_liquidation_certified": False,
        }
    return {
        "quote_ms": end,
        "cases": cases,
        "funding_events": len(events),
        "real_profit_usdt": None,
        "future_expected_profit_usdt": None,
        "incomplete_entry_exit_hours_certified": False,
    }
