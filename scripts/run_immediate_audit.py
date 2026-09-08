"""Registered recent-history diagnostic plus one brief live public shadow observation."""

from __future__ import annotations

import argparse
import math
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from scripts.carry_forward_math import HOUR, observations, opening, valuation
from scripts.carry_public import history as holding_history
from scripts.immediate_public import (
    Source,
    clock_offsets,
    collect_history,
    market_filters,
    snapshot,
    utc,
)
from scripts.plan_btc_hedge_v2 import number
from scripts.plan_btc_hedge_v3 import net_hedge_plan
from scripts.research_io import Ledger, integer, sha, strict_json, write_atomic

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/immediate_audit_20260908"
DAY = 24 * HOUR


def stamps(p):
    return tuple(
        int(datetime.fromisoformat(p[k]).timestamp() * 1000)
        for k in ("historical_start", "historical_end")
    )


def daily_rows(rows, start, end):
    result = {}
    for row in rows:
        t = integer(row[0], 1)
        if t in result or not start <= t <= end:
            raise ValueError("Duplicate/out-of-range daily candle")
        price = float(number(row[1]))
        if price <= 0:
            raise ValueError("Invalid candle open")
        if t == end:
            result[t] = [t, price]
            continue
        o, h, low, c, volume = map(lambda x: float(number(x)), row[1:6])
        if (
            min(o, h, low, c) <= 0
            or h < max(o, c)
            or low > min(o, c)
            or low > h
            or min(volume, float(number(row[7]))) < 0
            or integer(row[6], 1) != t + DAY - 1
        ):
            raise ValueError("Invalid daily OHLC/volume")
        result[t] = [t, o, h, low, c]
    if sorted(result) != list(range(start, end + DAY, DAY)):
        raise ValueError("Missing daily candle")
    return result


def fee(q, s, f, c):
    return (
        q
        * (
            s * (c["spot_bps"] + c["extra_slippage_bps"])
            + f * (c["future_bps"] + c["extra_slippage_bps"])
        )
        / 10000
    )


def historical(p, spot, future, funding, marks):
    start, end = stamps(p)
    s, f = daily_rows(spot, start, end), daily_rows(future, start, end)
    events, highs = observations(funding, marks, start, end)
    q = float(
        (
            Decimal(str(p["spot_budget_usdt"]))
            / Decimal(str(s[start][1]))
            // Decimal(p["model_step_btc"])
        )
        * Decimal(p["model_step_btc"])
    )
    if q <= 0:
        raise ValueError("No valid historical model quantity")
    s0, f0 = s[start][1], f[start][1]
    basis = q * (s[end][1] - s0 + f0 - f[end][1])
    cases = {}
    for name, c in p["costs"].items():
        flows = {
            t: q * float(mark) * float(rate) * (c["positive_funding_multiplier"] if rate > 0 else 1)
            for t, (mark, rate) in events.items()
        }
        entry_fee, exit_fee = fee(q, s0, f0, c), fee(q, s[end][1], f[end][1], c)
        mismatch = q * s0 * c["entry_mismatch_fraction"]
        overhead = c["annual_overhead_usdt"] * (end - start) / (365 * DAY)
        cash = p["capital_usdt"] - q * s0 - entry_fee - mismatch
        profit = basis + sum(flows.values()) - entry_fee - exit_fee - overhead - mismatch
        alt = (
            cash
            + sum(flows.values())
            - overhead
            + q * s[end][1]
            + q * (f0 - f[end][1])
            - exit_fee
            - p["capital_usdt"]
        )
        if abs(profit - alt) > 1e-7:
            raise ValueError("Historical account does not reconcile")
        minimum, jumped, breaches = math.inf, math.inf, 0
        for t, h in highs.items():
            cash_before = cash - c["annual_overhead_usdt"] * (t + HOUR - start) / (365 * DAY)
            cash_before += sum(v for k, v in flows.items() if k < t)
            cash_before += sum(v for k, v in flows.items() if t <= k < t + HOUR and v < 0)
            normal = cash_before + q * (f0 - float(h)) - 0.015 * q * float(h)
            shock = cash_before + q * (f0 - 1.3 * float(h)) - 0.015 * q * 1.3 * float(h)
            minimum, jumped = min(minimum, normal), min(jumped, shock)
            breaches += int(normal <= 0 or shock <= 0)
        curve = [float(p["capital_usdt"])]
        for day in range(start, end, DAY):
            stop = day + DAY
            sp, fp = (s[end][1], f[end][1]) if stop == end else (s[day][4], f[day][4])
            value = p["capital_usdt"] + q * (sp - s0 + f0 - fp)
            value += (
                sum(v for t, v in flows.items() if t < stop)
                - entry_fee
                - fee(q, sp, fp, c)
                - mismatch
            )
            value -= c["annual_overhead_usdt"] * (stop - start) / (365 * DAY)
            curve.append(value)
        weekly = [curve[i + 7] - curve[i] for i in range(0, len(curve) - 1, 7)]
        peak, dd = curve[0], 0.0
        for equity in curve[1:]:
            peak = max(peak, equity)
            dd = min(dd, equity / peak - 1)
        cases[name] = {
            "profit_usdt": profit,
            "basis_usdt": basis,
            "funding_usdt": sum(flows.values()),
            "entry_cost_usdt": entry_fee,
            "exit_cost_usdt": exit_fee,
            "overhead_usdt": overhead,
            "mismatch_usdt": mismatch,
            "minimum_surplus_usdt": minimum,
            "minimum_jump_surplus_usdt": jumped,
            "margin_breach_hours": breaches,
            "daily_liquidation_drawdown_fraction": dd,
            "weekly_profit_usdt": weekly,
            "negative_weeks": sum(v < 0 for v in weekly),
            "daily_equity_usdt": curve,
            "return_fraction": profit / p["capital_usdt"],
        }
    return {
        "status": "PASS",
        "start_ms": start,
        "end_ms": end,
        "days": (end - start) // DAY,
        "quantity_btc": q,
        "funding_events": len(events),
        "completed_mark_hours": len(highs),
        "cases": cases,
        "round_trip_hedges": 1,
        "hypothetical_legs": 4,
        "cash_weeks": 0,
        "net_btc_model_delta": 0,
        "historical_book_fills_certified": False,
        "independent_out_of_sample": False,
        "real_profit_usdt": None,
    }


def verify():
    freeze = strict_json((EVIDENCE / "freeze.json").read_bytes())
    for name, digest in freeze["files"].items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError("Immediate diagnostic freeze changed: " + name)
    return strict_json((EVIDENCE / "protocol.json").read_bytes())


def run(directory):
    p = verify()
    directory.mkdir(parents=True, exist_ok=False)
    ledger = Ledger(directory / "ledger.jsonl")
    ledger.append(
        "RUN_DECISION",
        "one",
        {"protocol_sha256": sha((EVIDENCE / "protocol.json").read_bytes())},
        utc(),
    )
    source = Source(directory)
    result = {
        "protocol_id": p["id"],
        "started_utc": utc(),
        "historical": None,
        "live": None,
        "orders": 0,
        "real_profit": None,
    }
    try:
        try:
            data = collect_history(source, *stamps(p))
            write_atomic(directory / "historical_inputs.json", data)
            result["historical"] = historical(p, *data)
            write_atomic(directory / "results.json", result)
            print("Historical window collected and calculated", flush=True)
        except Exception as exc:
            result["historical"] = {"status": "FAILED", "error": repr(exc)}
        samples = []
        try:
            offsets, errors = clock_offsets(source)
            constraints = market_filters(source)
            start_mono = time.monotonic()
            for index in range(p["live_samples"]):
                remaining = start_mono + index * p["live_spacing_seconds"] - time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)
                decision = ledger.append("SAMPLE_DECISION", str(index), {"index": index}, utc())
                try:
                    snap = snapshot(source, offsets, constraints)
                    if (
                        snap["quote_ns"] / 1e9
                        < datetime.fromisoformat(decision["known_at"]).timestamp()
                    ):
                        raise ValueError("Quote predates durable decision")
                    sample = {"index": index, "snapshot": snap, "error": None}
                except Exception as exc:
                    sample = {"index": index, "snapshot": None, "error": repr(exc)}
                samples.append(sample)
                ledger.append("SAMPLE_RESULT", str(index), sample, utc())
                write_atomic(directory / "live_samples.json", samples)
                print(
                    f"Live observation {index + 1}/{p['live_samples']}: {'PASS' if sample['snapshot'] else sample['error']}",
                    flush=True,
                )
            live = {
                "samples": len(samples),
                "valid_binance_pairs": sum(s["snapshot"] is not None for s in samples),
                "clock_offsets_ms": offsets,
                "clock_errors": errors,
                "value": None,
                "entry": None,
                "net_btc_commission_diagnostic": None,
            }
            if samples[0]["snapshot"] and samples[-1]["snapshot"]:
                first, last = samples[0]["snapshot"], samples[-1]["snapshot"]
                position = opening(first, p)
                fund, marks = holding_history(
                    source, position["entry_ms"], last["quote_ns"] // 1_000_000
                )
                write_atomic(
                    directory / "live_cashflow_inputs.json", {"funding": fund, "marks": marks}
                )
                live["entry"], live["value"] = position, valuation(position, last, fund, marks, p)
                live["net_btc_commission_diagnostic"] = net_hedge_plan(
                    first["spot"],
                    first["future"],
                    first["sf"],
                    first["ff"],
                    first["base_commission_precision"],
                )
                live["observed_seconds"] = (last["quote_ns"] - first["quote_ns"]) / 1e9
                live["status"] = "QUOTED_SHADOW_ROUND_TRIP"
            else:
                live["status"] = "UNKNOWN_MISSING_FIRST_OR_FINAL_QUOTE"
            result["live"] = live
        except Exception as exc:
            result["live"] = {"status": "FAILED", "error": repr(exc), "samples_saved": len(samples)}
    finally:
        source.client.close()
        result.update(
            finished_utc=utc(), public_requests=source.requests, public_bytes=source.bytes
        )
        write_atomic(directory / "results.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    output = run(args.data)
    print({"historical": output["historical"]["status"], "live": output["live"]["status"]})
    raise SystemExit(
        int(
            output["historical"]["status"] != "PASS"
            or output["live"]["status"] != "QUOTED_SHADOW_ROUND_TRIP"
        )
    )
