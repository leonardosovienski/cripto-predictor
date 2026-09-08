"""Cashflow and conservative collateral accounting; never an execution engine."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import numpy as np

from scripts.backtest_absolute_spot import block_interval, concentration
from scripts.collect_absolute_carry import DAY, END, HOUR, START, SYMBOLS, write

ENTRY = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)


def stamp(t: int) -> str:
    return datetime.fromtimestamp(t / 1000, UTC).isoformat()


def common_step(a: str, b: str) -> Decimal:
    da, db = Decimal(a), Decimal(b)
    if not da.is_finite() or not db.is_finite() or min(da, db) <= 0:
        raise ValueError("Invalid quantity grid")
    scale = 10 ** max(-int(da.as_tuple().exponent), -int(db.as_tuple().exponent), 0)
    return Decimal(math.lcm(int(da * scale), int(db * scale))) / Decimal(scale)


def rounded_quantity(budget: float, price: float, step: Decimal) -> float:
    if not math.isfinite(budget) or not math.isfinite(price) or budget <= 0 or price <= 0:
        raise ValueError("Invalid sizing input")
    return float((Decimal(str(budget)) / Decimal(str(price)) // step) * step)


def get_filters(info: dict, symbol: str) -> dict:
    row = next(r for r in info["symbols"] if r["symbol"] == symbol)
    filters = {r["filterType"]: r for r in row["filters"]}
    lot = filters["LOT_SIZE"]
    steps = [Decimal(lot["stepSize"])]
    market = filters.get("MARKET_LOT_SIZE")
    if market and Decimal(market["stepSize"]) > 0:
        steps.append(Decimal(market["stepSize"]))
    step = steps[0]
    for extra in steps[1:]:
        step = common_step(str(step), str(extra))
    notional = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
    return {
        "step": str(step),
        "min_qty": float(lot["minQty"]),
        "max_qty": min(
            float(lot["maxQty"]), float(market["maxQty"]) if market else float(lot["maxQty"])
        ),
        "min_notional": float(notional.get("minNotional", notional.get("notional", 0))),
        "status": row["status"],
        "historical_constraints_certified": False,
    }


def load_dataset(directory: Path, protocol_path: Path):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    sha = lambda b: hashlib.sha256(b).hexdigest()
    if sha(protocol_path.read_bytes()) != manifest["protocol_sha256"]:
        raise ValueError("Registered acquisition protocol changed")
    for name, expected in manifest["normalized"].items():
        if sha((directory / name).read_bytes()) != expected:
            raise ValueError("Normalized data changed: " + name)
    for source in manifest["sources"]:
        raw = gzip.decompress((directory / source["raw"]).read_bytes())
        if sha(raw) != source["sha256"] or source["status"] != 200:
            raise ValueError("Raw source changed")
    info = {
        kind: json.loads((directory / f"{kind}_exchangeInfo.json").read_text(encoding="utf-8"))
        for kind in ("spot", "perp")
    }
    assets = {}
    for symbol in SYMBOLS:
        asset = {
            kind: json.loads(gzip.decompress((directory / f"{symbol}_{kind}.json.gz").read_bytes()))
            for kind in ("spot_daily", "perp_daily", "mark_hourly", "funding")
        }
        for kind in ("spot_daily", "perp_daily", "mark_hourly"):
            interval = HOUR if kind == "mark_hourly" else DAY
            rows = asset[kind]
            if [r[0] for r in rows] != list(range(START, END + interval, interval)):
                raise ValueError("Non-contiguous price data")
            for row in rows[:-1]:
                o, h, low, c = map(float, row[1:5])
                if (
                    not all(math.isfinite(v) and v > 0 for v in (o, h, low, c))
                    or h < max(o, c)
                    or low > min(o, c)
                    or int(row[6]) != row[0] + interval - 1
                ):
                    raise ValueError("Invalid completed OHLC candle")
            if (
                len(rows[-1]) != 2
                or not math.isfinite(float(rows[-1][1]))
                or float(rows[-1][1]) <= 0
            ):
                raise ValueError("Cutoff candle must expose opening price only")
            asset[kind] = {r[0]: r for r in rows}
        times = [r["fundingTime"] for r in asset["funding"]]
        if times != sorted(set(times)) or any(not START <= t < END for t in times):
            raise ValueError("Duplicate/out-of-range funding")
        if set(t // (8 * HOUR) for t in times) != set(
            range(START // (8 * HOUR), END // (8 * HOUR))
        ):
            raise ValueError("Missing baseline settlement buckets")
        for r in asset["funding"]:
            if (
                r["symbol"] != symbol
                or not math.isfinite(float(r["fundingRate"]))
                or not math.isfinite(float(r["markPrice"]))
                or float(r["markPrice"]) <= 0
            ):
                raise ValueError("Invalid funding event")
        asset["filters"] = {kind: get_filters(info[kind], symbol) for kind in ("spot", "perp")}
        asset["step"] = common_step(*(asset["filters"][k]["step"] for k in ("spot", "perp")))
        assets[symbol] = asset
    return assets, manifest


def past_funding_signal(rows: list[dict], anchor: int) -> tuple[float | None, int]:
    lo, hi = anchor - 29 * DAY, anchor - DAY
    past = [r for r in rows if lo <= r["fundingTime"] < hi]
    buckets = {r["fundingTime"] // (8 * HOUR) for r in past}
    if buckets != set(range(lo // (8 * HOUR), hi // (8 * HOUR))):
        return None, len(past)
    return sum(float(r["fundingRate"]) for r in past), len(past)


def carry_decisions(asset: dict, policy: str) -> list[dict]:
    if policy not in ("AR1", "AR2"):
        raise ValueError("Unregistered policy")
    anchors = [ENTRY] if policy == "AR1" else list(range(ENTRY, END, 28 * DAY))
    decisions = []
    for anchor in anchors:
        liq = {}
        for kind in ("spot_daily", "perp_daily"):
            past = [asset[kind].get(t) for t in range(anchor - 31 * DAY, anchor - DAY, DAY)]
            liq[kind] = float(np.median([float(r[7]) for r in past])) if all(past) else None
        rate, count = past_funding_signal(asset["funding"], anchor)
        liquidity_ok = all(v is not None and v >= 5_000_000 for v in liq.values())
        enter = liquidity_ok and (policy == "AR1" or (rate is not None and rate > 0.0135))
        decisions.append(
            {
                "anchor_ms": anchor,
                "anchor": stamp(anchor),
                "exit_ms": END if policy == "AR1" else min(anchor + 28 * DAY, END),
                "enter": enter,
                "lagged_signed_28d_funding": rate,
                "lagged_settlements": count,
                "lagged_liquidity": liq,
                "reason": "ENTER"
                if enter
                else "MISSING_OR_LOW_LIQUIDITY"
                if not liquidity_ok
                else "MISSING_PAST_FUNDING"
                if rate is None
                else "FUNDING_BELOW_FIXED_COST_GATE",
            }
        )
    return decisions


def transaction_cost(q: float, spot: float, perp: float, cost: dict) -> float:
    return (
        q
        * (
            spot * (cost["spot_fee_bps_side"] + cost["slippage_bps_each_leg"])
            + perp * (cost["perp_fee_bps_side"] + cost["slippage_bps_each_leg"])
        )
        / 10000
    )


def hourly_surplus(
    cash_before_hour: float,
    negative_current_funding: float,
    q: float,
    short_entry: float,
    mark_high: float,
    jump: float = 0,
) -> float:
    stressed_mark = mark_high * (1 + jump)
    lower_collateral = (
        cash_before_hour + negative_current_funding + q * (short_entry - stressed_mark)
    )
    return lower_collateral - q * stressed_mark * 0.015


def simulate(asset: dict, decisions: list[dict], cost: dict) -> dict:
    plan = {r["anchor_ms"]: r for r in decisions}
    funding_by_hour = defaultdict(list)
    for row in asset["funding"]:
        funding_by_hour[row["fundingTime"] // HOUR * HOUR].append(row)
    cash = 5000.0
    current = None
    spells, daily, orders = [], [], []
    first_entry = None
    total_overhead = 0.0
    min_surplus = min_jump_surplus = math.inf
    first_breach = first_jump_breach = None
    for day in range(ENTRY, END + DAY, DAY):
        s_open, f_open = float(asset["spot_daily"][day][1]), float(asset["perp_daily"][day][1])
        if current and current["exit_ms"] == day:
            q = current["quantity"]
            close_cost = transaction_cost(q, s_open, f_open, cost)
            cash += q * s_open + q * (current["perp_entry"] - f_open) - close_cost
            current.update(
                {
                    "spot_exit": s_open,
                    "perp_exit": f_open,
                    "exit_cost_usdt": close_cost,
                    "basis_pnl_usdt": q
                    * ((s_open - current["spot_entry"]) + (current["perp_entry"] - f_open)),
                }
            )
            current["net_trading_pnl_usdt"] = (
                current["funding_usdt"]
                + current["basis_pnl_usdt"]
                - current["entry_cost_usdt"]
                - close_cost
                - current["unhedged_shock_usdt"]
            )
            spells.append(current)
            orders.append(
                {
                    "time": stamp(day),
                    "action": "HYPOTHETICAL_CLOSE_BOTH_LEGS",
                    "quantity": q,
                    "account_equity_usdt": cash,
                }
            )
            current = None
        if day == END:
            if current:
                raise ValueError("Unclosed final hedge")
            break
        decision = plan.get(day)
        if decision and decision["enter"]:
            if current or cash <= 0:
                raise ValueError("Invalid account/overlapping hold")
            q = rounded_quantity(0.25 * cash, s_open, asset["step"])
            feasible = all(
                f["min_qty"] <= q <= f["max_qty"]
                and q * (s_open if kind == "spot" else f_open) >= f["min_notional"]
                for kind, f in asset["filters"].items()
            )
            if not feasible:
                orders.append(
                    {
                        "time": stamp(day),
                        "action": "NO_ENTRY_CURRENT_QUANTITY_FILTER",
                        "quantity": q,
                    }
                )
            else:
                entry_cost = transaction_cost(q, s_open, f_open, cost)
                shock = q * s_open * cost["entry_unhedged_shock_fraction_notional"]
                current = {
                    "entry_ms": day,
                    "entry": stamp(day),
                    "exit_ms": decision["exit_ms"],
                    "exit": stamp(decision["exit_ms"]),
                    "quantity": q,
                    "spot_entry": s_open,
                    "perp_entry": f_open,
                    "initial_equity_usdt": cash,
                    "entry_cost_usdt": entry_cost,
                    "unhedged_shock_usdt": shock,
                    "funding_usdt": 0.0,
                    "positive_funding_usdt": 0.0,
                    "negative_funding_usdt": 0.0,
                    "settlements": 0,
                }
                cash -= q * s_open + entry_cost + shock
                first_entry = day if first_entry is None else first_entry
                orders.append(
                    {
                        "time": stamp(day),
                        "action": "HYPOTHETICAL_OPEN_BOTH_LEGS",
                        "quantity": q,
                        "cash_collateral_usdt": cash,
                    }
                )
        overhead = cost["annual_residual_usdt"] / 365 if first_entry is not None else 0
        cash -= overhead
        total_overhead += overhead
        q = current["quantity"] if current else 0.0
        daily_funding = 0.0
        cash_before_day = cash
        day_negative = 0.0
        if current:
            for hour in range(day, day + DAY, HOUR):
                flows = []
                for event in funding_by_hour[hour]:
                    if event["fundingTime"] // HOUR <= current["entry_ms"] // HOUR:
                        continue
                    flow = q * float(event["markPrice"]) * float(event["fundingRate"])
                    flow = flow * cost["positive_funding_multiplier"] if flow > 0 else flow
                    flows.append(flow)
                    current["settlements"] += 1
                negative = sum(v for v in flows if v < 0)
                mark_high = float(asset["mark_hourly"][hour][2])
                surplus = hourly_surplus(cash, negative, q, current["perp_entry"], mark_high)
                jump_surplus = hourly_surplus(
                    cash, negative, q, current["perp_entry"], mark_high, 0.30
                )
                min_surplus = min(min_surplus, surplus)
                min_jump_surplus = min(min_jump_surplus, jump_surplus)
                if surplus <= 0 and first_breach is None:
                    first_breach = stamp(hour)
                if jump_surplus <= 0 and first_jump_breach is None:
                    first_jump_breach = stamp(hour)
                flow = sum(flows)
                cash += flow
                daily_funding += flow
                day_negative += negative
                current["funding_usdt"] += flow
                current["positive_funding_usdt"] += sum(v for v in flows if v > 0)
                current["negative_funding_usdt"] += negative
            s_close, f_close = (
                float(asset["spot_daily"][day][4]),
                float(asset["perp_daily"][day][4]),
            )
            equity = cash + q * s_close + q * (current["perp_entry"] - f_close)
            low_bound = (
                cash_before_day
                + day_negative
                + q * float(asset["spot_daily"][day][3])
                + q * (current["perp_entry"] - float(asset["perp_daily"][day][2]))
            )
            gross_notional = q * (s_close + f_close)
            spot_notional = q * s_close
        else:
            equity, low_bound, gross_notional, spot_notional = cash, cash, 0.0, 0.0
        daily.append(
            {
                "date": stamp(day)[:10],
                "equity_usdt": equity,
                "non_synchronous_low_bound_usdt": low_bound,
                "active": current is not None,
                "gross_notional_usdt": gross_notional,
                "spot_notional_usdt": spot_notional,
                "net_delta_base": 0.0,
                "funding_usdt": daily_funding,
                "residual_cost_usdt": overhead,
            }
        )
    # The final cutoff open exit replaces the final valuation with actual modeled unwind.
    daily[-1]["cutoff_open_equity_usdt"] = cash
    curve = np.asarray([5000.0] + [r["equity_usdt"] for r in daily] + [cash])
    peaks = np.maximum.accumulate(curve)
    drawdown = float((curve / peaks - 1).min())
    low_drawdown_bound = min(
        r["non_synchronous_low_bound_usdt"] / peaks[i + 1] - 1 for i, r in enumerate(daily)
    )
    expected = sum(r["net_trading_pnl_usdt"] for r in spells) - total_overhead
    if abs((cash - 5000) - expected) > 1e-7:
        raise ValueError("Cashflow reconciliation failed")
    weekly, previous = [], 5000.0
    for index in range(0, len(daily), 7):
        segment = daily[index : index + 7]
        end_equity = cash if index + 7 >= len(daily) else segment[-1]["equity_usdt"]
        weekly.append(
            {
                "week": segment[0]["date"],
                "ending_equity_usdt": end_equity,
                "pnl_usdt": end_equity - previous,
                "active_days": sum(r["active"] for r in segment),
            }
        )
        previous = end_equity
    yearly = {}
    previous = 5000.0
    for year in (2024, 2025, 2026):
        part = [r for r in daily if r["date"].startswith(str(year))]
        end_equity = cash if year == 2026 else part[-1]["equity_usdt"]
        yearly[str(year)] = {
            "pnl_usdt": end_equity - previous,
            "return_on_year_start_equity": end_equity / previous - 1,
            "active_days": sum(r["active"] for r in part),
        }
        previous = end_equity
    increments = [w["pnl_usdt"] for w in weekly]
    return {
        "initial_usdt": 5000,
        "ending_usdt_mechanical": cash,
        "profit_usdt_mechanical": cash - 5000,
        "return_fraction": cash / 5000 - 1,
        "funding_usdt": sum(s["funding_usdt"] for s in spells),
        "basis_pnl_usdt": sum(s["basis_pnl_usdt"] for s in spells),
        "fees_slippage_usdt": sum(s["entry_cost_usdt"] + s["exit_cost_usdt"] for s in spells),
        "residual_cost_usdt": total_overhead,
        "unhedged_shock_usdt": sum(s["unhedged_shock_usdt"] for s in spells),
        "round_trip_hedges": len(spells),
        "leg_transactions": 4 * len(spells),
        "active_weeks": sum(w["active_days"] > 0 for w in weekly),
        "cash_weeks": sum(w["active_days"] == 0 for w in weekly),
        "active_days": sum(d["active"] for d in daily),
        "weeks": len(weekly),
        "average_gross_notional_fraction_equity": float(
            np.mean([r["gross_notional_usdt"] / r["equity_usdt"] for r in daily])
        ),
        "average_spot_notional_fraction_equity": float(
            np.mean([r["spot_notional_usdt"] / r["equity_usdt"] for r in daily])
        ),
        "maximum_drawdown_daily_close_and_final_unwind": drawdown,
        "non_synchronous_low_drawdown_stress_bound": low_drawdown_bound,
        "low_bound_meaning": "Conservative non-synchronous low-spot/high-perp, positive current-day funding omitted; not observed intraday portfolio drawdown.",
        "minimum_hourly_collateral_surplus_usdt": None if min_surplus == math.inf else min_surplus,
        "minimum_30pct_mark_jump_surplus_usdt": None
        if min_jump_surplus == math.inf
        else min_jump_surplus,
        "first_conservative_margin_breach": first_breach,
        "first_jump_breach": first_jump_breach,
        "modeled_margin_bound_passed": first_breach is None if spells else None,
        "actual_liquidation_certified": False,
        "executable_net_profit": None,
        "additional_cost_budget_usdt": cash - 5000,
        "concentration": concentration(increments),
        "bootstrap": block_interval(increments),
        "by_year": yearly,
        "spells": spells,
        "orders": orders,
        "daily": daily,
        "weekly": weekly,
    }


def run_carry(assets: dict, costs: dict, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    # Persist all decisions for every stream before attaching any future cashflows.
    decisions = {
        f"{policy}_{symbol}": carry_decisions(assets[symbol], policy)
        for policy in ("AR1", "AR2")
        for symbol in SYMBOLS
    }
    write(output / "decisions.json", decisions)
    summaries = {}
    for name, plan in decisions.items():
        symbol = name.split("_", 1)[1]
        scenarios = {}
        for cost_name in ("base", "adverse", "compression"):
            result = simulate(assets[symbol], plan, costs[cost_name])
            write(output / f"{name}_{cost_name}_ledger.json", result)
            scenarios[cost_name] = {
                k: v for k, v in result.items() if k not in {"daily", "weekly", "spells", "orders"}
            }
        adverse = scenarios["adverse"]
        ci = adverse["bootstrap"]["interval_95_usdt"]
        summaries[name] = {
            "scenarios": scenarios,
            "current_quantity_step": str(assets[symbol]["step"]),
            "current_filters": assets[symbol]["filters"],
            "future_observation_candidate": bool(
                adverse["profit_usdt_mechanical"] > 0
                and ci
                and ci[0] > 0
                and adverse["modeled_margin_bound_passed"]
            ),
            "execution_ready": False,
            "real_profit": None,
        }
    write(output / "results.json", summaries)
    return summaries
