"""Registered causal decisions and separate collateral books; simulation only."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from decimal import Decimal
from typing import Any

import numpy as np

from scripts.basis_data import DAY, END, ENTRY, HOUR, START, contracts, stamp


class MissingOutcome(ValueError):
    pass


def liquidity_table(bars: dict, end=END) -> dict:
    daily = {}
    for day in range(START, end, DAY):
        rows = [bars.get(t) for t in range(day, day + DAY, HOUR)]
        if all(r is not None and len(r) >= 8 for r in rows):
            daily[day] = sum(float(r[7]) for r in rows if r is not None)
    result = {}
    for day in range(ENTRY, end, DAY):
        previous = [daily.get(d) for d in range(day - 31 * DAY, day - DAY, DAY)]
        result[day] = (
            statistics.median([v for v in previous if v is not None])
            if all(v is not None for v in previous)
            else None
        )
    return result


def lagged_basis(spot: dict, future: dict, execution: int) -> float | None:
    signal = execution - 2 * HOUR
    s, f = spot.get(signal), future.get(signal)
    if s is None or f is None or len(s) < 5 or len(f) < 5:
        return None
    return float(f[4]) / float(s[4]) - 1


def make_plan(data: dict, rule: dict, end=END) -> dict:
    dated = rule["id"] == "BR1_DATED_BTC"
    universe = contracts() if dated else {"BTCUSDT": None}
    liquid = {"spot": liquidity_table(data["spot"], end)}
    for symbol in universe:
        liquid[symbol] = liquidity_table(
            data.get(symbol + "_trade", {}) if dated else data["perp"], end
        )
    spells, decisions = [], []
    current: dict[str, Any] | None = None
    for t in range(ENTRY, end + HOUR, HOUR):
        just_closed = False
        if current:
            if t == end:
                reason = "CUTOFF"
            elif dated and t == current["expiry_ms"]:
                reason = "SETTLEMENT"
            elif not dated and t - current["entry_ms"] >= rule["maximum_hold_hours"] * HOUR:
                reason = "MAXIMUM_HOLD"
            elif (
                not dated
                and (basis := lagged_basis(data["spot"], data["perp"], t)) is not None
                and basis <= rule["exit_basis_threshold"]
            ):
                reason = "CONVERGED"
            else:
                reason = None
            if reason:
                current.update(
                    {
                        "exit_ms": t,
                        "exit_reason": reason,
                        "exit_signal_basis": None
                        if dated
                        else lagged_basis(data["spot"], data["perp"], t),
                    }
                )
                spells.append(current)
                current = None
                just_closed = True
        if current or just_closed or t == end or (dated and t % DAY):
            continue
        day = t // DAY * DAY
        s_liq = liquid["spot"].get(day)
        eligible = []
        if s_liq is not None and s_liq >= 5_000_000:
            for symbol, expiry in universe.items():
                f_liq = liquid[symbol].get(day)
                if (
                    (not dated or (expiry is not None and 30 * DAY <= expiry - t <= 120 * DAY))
                    and f_liq is not None
                    and f_liq >= 5_000_000
                ):
                    eligible.append(symbol)
        # Universe is chronological; do not search alternatives after a price-gate rejection.
        symbol = eligible[0] if eligible else None
        future = data[symbol + "_trade"] if dated and symbol else data["perp"]
        basis = lagged_basis(data["spot"], future, t) if symbol else None
        enter = basis is not None and basis > rule["entry_basis_threshold"]
        decisions.append(
            {
                "execution_ms": t,
                "signal_bar_ms": t - 2 * HOUR,
                "last_signal_close_ms": t - HOUR - 1,
                "symbol": symbol,
                "eligible_contracts": eligible,
                "spot_median_daily_quote_volume": s_liq,
                "future_median_daily_quote_volume": liquid[symbol].get(day) if symbol else None,
                "basis": basis,
                "enter": enter,
                "reason": "ENTER"
                if enter
                else "MISSING_OR_LOW_LIQUIDITY_OR_MATURITY"
                if not symbol
                else "MISSING_SIGNAL"
                if basis is None
                else "BASIS_BELOW_FIXED_GATE",
            }
        )
        if enter:
            assert symbol is not None
            current = {
                "symbol": symbol,
                "entry_ms": t,
                "entry_signal_basis": basis,
                "signal_bar_ms": t - 2 * HOUR,
                "expiry_ms": universe[symbol],
            }
    if current:
        raise ValueError("Open plan after cutoff")
    return {"id": rule["id"], "decisions": decisions, "spells": spells}


def bar(data: dict, kind: str, t: int, field: int) -> float:
    row = data.get(kind, {}).get(t)
    if row is None or len(row) <= field:
        raise MissingOutcome(f"Missing held {kind} field {field} at {stamp(t)}")
    value = float(row[field])
    if not math.isfinite(value) or value <= 0:
        raise MissingOutcome("Invalid held price")
    return value


def trade_cost(q: float, spot: float, future: float, cost: dict, settled=False) -> float:
    future_rate = (
        cost["settlement_fee_bps"] if settled else cost["future_fee_bps"] + cost["slippage_bps"]
    )
    return (
        q * (spot * (cost["spot_fee_bps"] + cost["slippage_bps"]) + future * future_rate) / 10_000
    )


def settlement_price(data: dict, expiry: int) -> tuple[float, int]:
    # The API date label is midnight; the price is only available to this engine at expiry 08:00.
    matching = [r for r in data["delivery"] if int(r["deliveryTime"]) // DAY == expiry // DAY]
    if len(matching) != 1 or expiry % DAY != 8 * HOUR:
        raise MissingOutcome("Missing or ambiguous settlement date")
    return float(matching[0]["deliveryPrice"]), int(matching[0]["deliveryTime"])


def bootstrap_total(weekly: list[float]) -> list[float]:
    values = np.asarray(weekly, dtype=float)
    rng = np.random.default_rng(20260908)
    starts = rng.integers(0, len(values), size=(5000, math.ceil(len(values) / 13)))
    indices = ((starts[:, :, None] + np.arange(13)) % len(values)).reshape(5000, -1)[
        :, : len(values)
    ]
    return np.quantile(values[indices].sum(axis=1), [0.025, 0.975]).tolist()


def simulate(data: dict, plan: dict, cost: dict, end=END) -> dict:
    dated = plan["id"] == "BR1_DATED_BTC"
    entries = {p["entry_ms"]: p for p in plan["spells"]}
    funding = defaultdict(list)
    if not dated:
        for event in data["funding"]:
            funding[int(event["fundingTime"]) // HOUR * HOUR].append(event)
    current: dict[str, Any] | None = None
    cash, first_entry = 5000.0, None
    spells, hourly, payments, orders = [], [], [], []
    total_residual = 0.0
    minimum, minimum_jump = math.inf, math.inf
    first_breach = first_jump_breach = None
    active_hours, active_weeks, gross_sum = 0, set(), 0.0
    failure = None
    try:
        for t in range(ENTRY, end + HOUR, HOUR):
            if current and t == current["exit_ms"]:
                q = current["quantity"]
                s = bar(data, "spot", t, 1)
                settled = current["exit_reason"] == "SETTLEMENT"
                if settled:
                    f, label = settlement_price(data, current["expiry_ms"])
                    current["settlement_record_date_ms"] = label
                else:
                    f = bar(data, current["trade_kind"], t, 1)
                closing_cost = trade_cost(q, s, f, cost, settled)
                cash += q * s + q * (current["future_entry"] - f) - closing_cost
                basis = q * ((s - current["spot_entry"]) + (current["future_entry"] - f))
                current.update(
                    {
                        "spot_exit": s,
                        "future_exit": f,
                        "exit_cost_usdt": closing_cost,
                        "basis_usdt": basis,
                        "net_before_residual_usdt": basis
                        + current["funding_usdt"]
                        - current["entry_cost_usdt"]
                        - closing_cost
                        - current["mismatch_usdt"],
                    }
                )
                spells.append(current)
                orders.append(
                    {
                        "time_ms": t,
                        "action": "SETTLE_FUTURE_SELL_SPOT" if settled else "CLOSE_BOTH",
                        "quantity": q,
                        "cash_after": cash,
                    }
                )
                current = None
            if t == end:
                hourly.append(
                    {"time_ms": t, "equity_usdt": cash, "active": False, "gross_fraction": 0.0}
                )
                break
            if t in entries:
                if current or cash <= 0:
                    raise MissingOutcome("Account cannot fund registered next position")
                p = entries[t]
                trade_kind = p["symbol"] + "_trade" if dated else "perp"
                mark_kind = p["symbol"] + "_mark" if dated else "mark"
                s, f = bar(data, "spot", t, 1), bar(data, trade_kind, t, 1)
                q = float(
                    (Decimal(str(cash * 0.25)) / Decimal(str(s)) // Decimal("0.001"))
                    * Decimal("0.001")
                )
                if q <= 0:
                    raise MissingOutcome("Capital below fixed simulation unit")
                opening_cost = trade_cost(q, s, f, cost)
                mismatch = q * s * cost["entry_mismatch_fraction"]
                cash -= q * s + opening_cost + mismatch
                current = dict(
                    p,
                    quantity=q,
                    spot_entry=s,
                    future_entry=f,
                    entry_cost_usdt=opening_cost,
                    mismatch_usdt=mismatch,
                    funding_usdt=0.0,
                    trade_kind=trade_kind,
                    mark_kind=mark_kind,
                )
                if first_entry is None:
                    first_entry = t
                orders.append(
                    {"time_ms": t, "action": "OPEN_BOTH", "quantity": q, "cash_after": cash}
                )
            residual = cost["annual_residual_usdt"] / (365 * 24) if first_entry is not None else 0.0
            cash -= residual
            total_residual += residual
            if current:
                q = current["quantity"]
                events = funding.get(t, []) if t > current["entry_ms"] else []
                amounts = []
                for event in events:
                    original = q * float(event["markPrice"]) * float(event["fundingRate"])
                    amount = original * (cost["positive_funding_multiplier"] if original > 0 else 1)
                    amounts.append(amount)
                    payments.append(
                        {
                            "time_ms": int(event["fundingTime"]),
                            "entry_ms": current["entry_ms"],
                            "quantity": q,
                            "mark": event["markPrice"],
                            "rate": event["fundingRate"],
                            "amount_usdt": amount,
                        }
                    )
                high = bar(data, current["mark_kind"], t, 2)
                negatives = sum(v for v in amounts if v < 0)
                for jump in (0, 0.3):
                    mark = high * (1 + jump)
                    surplus = (
                        cash + negatives + q * (current["future_entry"] - mark) - 0.015 * q * mark
                    )
                    if jump == 0:
                        minimum = min(minimum, surplus)
                        if surplus <= 0 and first_breach is None:
                            first_breach = t
                    else:
                        minimum_jump = min(minimum_jump, surplus)
                        if surplus <= 0 and first_jump_breach is None:
                            first_jump_breach = t
                cash += sum(amounts)
                current["funding_usdt"] += sum(amounts)
                s_close = bar(data, "spot", t, 4)
                f_close = bar(data, current["mark_kind"], t, 4)
                equity = cash + q * s_close + q * (current["future_entry"] - f_close)
                gross = q * (s_close + f_close) / equity if equity > 0 else None
                if gross is None:
                    raise MissingOutcome("Nonpositive marked account equity")
                active_hours += 1
                active_weeks.add((t - ENTRY) // (7 * DAY))
            else:
                equity, gross = cash, 0.0
            gross_sum += gross
            hourly.append(
                {
                    "time_ms": t + HOUR - 1,
                    "equity_usdt": equity,
                    "active": current is not None,
                    "gross_fraction": gross,
                }
            )
    except MissingOutcome as exc:
        failure = str(exc)
    if failure:
        return {
            "summary": {
                "profit_usdt": None,
                "ending_usdt": None,
                "status": "UNKNOWN_HELD_OUTCOME",
                "failure": failure,
                "completed_hedges": len(spells),
            },
            "spells": spells,
            "hourly": hourly,
            "funding": payments,
            "orders": orders,
            "unresolved_position": current,
        }
    profit = cash - 5000
    totals = {
        "funding_usdt": sum(s["funding_usdt"] for s in spells),
        "basis_usdt": sum(s["basis_usdt"] for s in spells),
        "trading_cost_usdt": sum(s["entry_cost_usdt"] + s["exit_cost_usdt"] for s in spells),
        "mismatch_usdt": sum(s["mismatch_usdt"] for s in spells),
        "residual_usdt": total_residual,
    }
    if (
        abs(
            profit
            - (
                totals["funding_usdt"]
                + totals["basis_usdt"]
                - totals["trading_cost_usdt"]
                - totals["mismatch_usdt"]
                - total_residual
            )
        )
        > 1e-7
    ):
        raise ValueError("Portfolio accounting reconciliation failed")
    weeks = math.ceil((end - ENTRY) / (7 * DAY))
    weekly = [0.0] * weeks
    years = defaultdict(float)
    previous, peak, drawdown = 5000.0, 5000.0, 0.0
    for row in hourly:
        equity = row["equity_usdt"]
        increment = equity - previous
        index = min((row["time_ms"] - ENTRY) // (7 * DAY), weeks - 1)
        weekly[index] += increment
        years[stamp(row["time_ms"])[:4]] += increment
        previous = equity
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1)
    positives = sorted((v for v in weekly if v > 0), reverse=True)
    top = sum(positives[:5])
    interval = bootstrap_total(weekly)
    summary = {
        "profit_usdt": profit,
        "ending_usdt": cash,
        "return_fraction": profit / 5000,
        **totals,
        "hedges": len(spells),
        "completed_hedges": sum(s["exit_reason"] != "CUTOFF" for s in spells),
        "cutoff_hedges": sum(s["exit_reason"] == "CUTOFF" for s in spells),
        "leg_transactions": 4 * len(spells),
        "active_hours": active_hours,
        "active_weeks": len(active_weeks),
        "cash_weeks": weeks - len(active_weeks),
        "mean_gross_exposure_fraction_equity": gross_sum / ((end - ENTRY) / HOUR),
        "maximum_drawdown_hourly_mark_close": drawdown,
        "minimum_margin_surplus_usdt": minimum if math.isfinite(minimum) else None,
        "minimum_jump_surplus_usdt": minimum_jump if math.isfinite(minimum_jump) else None,
        "first_margin_breach_ms": first_breach,
        "first_jump_breach_ms": first_jump_breach,
        "margin_pass": first_breach is None,
        "jump_margin_pass": first_jump_breach is None,
        "calendar_year_contributions_usdt": dict(years),
        "weekly_increments_usdt": weekly,
        "top_five_positive_weeks_share": top / sum(positives) if positives else None,
        "profit_excluding_top_five_week_contributions_usdt": profit - top,
        "descriptive_13week_block_total_interval_usdt": interval,
        "unmeasured_cost_breakeven_usdt": profit,
        "real_profit_certified": False,
        "execution_certified": False,
        "attainable_result_if_margin_breach": None
        if first_breach is not None
        else "UNCERTIFIED_PROXY",
        "status": "NO_REGISTERED_OPPORTUNITY"
        if not spells
        else "MECHANICAL_MARGIN_BREACH"
        if first_breach is not None
        else "HISTORICAL_PROXY",
    }
    return {
        "summary": summary,
        "spells": spells,
        "hourly": hourly,
        "funding": payments,
        "orders": orders,
    }


def verdict(results: dict) -> str:
    rows = [r["summary"] for r in results.values()]
    if any(r["profit_usdt"] is None for r in rows):
        return "UNKNOWN_DATA_OR_ACCOUNT_FAILURE"
    if not any(r["hedges"] for r in rows):
        return "NO_OPPORTUNITY_UNDER_REGISTERED_RULE"
    if any(not r["margin_pass"] or not r["jump_margin_pass"] for r in rows):
        return "MARGIN_FRAGILE_MECHANICAL_RESULT_ONLY"
    if any(r["profit_usdt"] <= 0 for r in rows):
        return "NOT_ROBUST_TO_REGISTERED_COSTS"
    if any(r["completed_hedges"] < 5 for r in rows):
        return "POSITIVE_BUT_INSUFFICIENT_COMPLETED_HEDGES"
    if results["adverse"]["summary"]["descriptive_13week_block_total_interval_usdt"][0] <= 0:
        return "POSITIVE_BUT_DESCRIPTIVELY_UNCERTAIN"
    return "CANDIDATE_FOR_SEPARATELY_FROZEN_FUTURE_OBSERVATION"
