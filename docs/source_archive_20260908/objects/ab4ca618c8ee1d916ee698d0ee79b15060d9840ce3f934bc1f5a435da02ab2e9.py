"""Standalone stdlib reconstruction from raw responses; same author, separate calculation."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

D = Decimal
HOUR, DAY = 3600000, 86400000


def parse(raw):
    def pairs(rows):
        obj = {}
        for key, value in rows:
            if key in obj:
                raise ValueError("Duplicate JSON key")
            obj[key] = value
        return obj

    def invalid(_):
        raise ValueError("Nonfinite JSON")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def number(value):
    n = D(str(value))
    if not n.is_finite():
        raise ValueError("Nonfinite financial value")
    return n


def timestamp(value):
    if type(value) is not int or value <= 0:
        raise ValueError("Invalid timestamp")
    return value


def candles(rows, start, stop, interval, cutoff=False):
    out = {}
    for r in rows:
        t = timestamp(r[0])
        if t in out or t < start or t > stop or (t == stop and not cutoff):
            raise ValueError("Duplicate or unexpected candle")
        o = number(r[1])
        if o <= 0:
            raise ValueError("Bad open")
        if t == stop:
            out[t] = [o]
            continue
        h, low, c = map(number, r[2:5])
        if (
            min(h, low, c) <= 0
            or h < max(o, c)
            or low > min(o, c)
            or low > h
            or timestamp(r[6]) != t + interval - 1
        ):
            raise ValueError("Bad OHLC")
        if number(r[5]) < 0 or number(r[7]) < 0:
            raise ValueError("Bad volume")
        out[t] = [o, h, low, c]
    if sorted(out) != list(range(start, stop + (interval if cutoff else 0), interval)):
        raise ValueError("Missing candle")
    return out


def fee(q, s, f, case):
    slip = number(case["extra_slippage_bps"])
    return (
        q
        * (s * (number(case["spot_bps"]) + slip) + f * (number(case["future_bps"]) + slip))
        / 10000
    )


def rebuild(p, groups):
    begin, end = (
        int(datetime.fromisoformat(p[k]).timestamp() * 1000)
        for k in ("historical_start", "historical_end")
    )
    spot = candles(groups["spot_daily"], begin, end, DAY, True)
    future = candles(groups["future_daily"], begin, end, DAY, True)
    marks = candles(groups["mark"], begin, end, HOUR)
    settlements = {}
    for row in groups["funding"]:
        t = timestamp(row["fundingTime"])
        if row["symbol"] != "BTCUSDT" or t in settlements or not begin + HOUR <= t < end:
            raise ValueError("Invalid funding identity/time")
        rate, mark = number(row["fundingRate"]), number(row["markPrice"])
        if mark <= 0:
            raise ValueError("Invalid settlement mark")
        settlements[t] = (rate, mark)
    expected = set(range((begin + HOUR + 8 * HOUR - 1) // (8 * HOUR), (end - 1) // (8 * HOUR) + 1))
    if not expected.issubset({t // (8 * HOUR) for t in settlements}):
        raise ValueError("Missing settlement bucket")
    q = (number(p["spot_budget_usdt"]) / spot[begin][0] // number(p["model_step_btc"])) * number(
        p["model_step_btc"]
    )
    s0, f0 = spot[begin][0], future[begin][0]
    calculated = {}
    for name, case in p["costs"].items():
        flows = {
            t: q * rate * mark * (number(case["positive_funding_multiplier"]) if rate > 0 else 1)
            for t, (rate, mark) in settlements.items()
        }
        entry_fee, exit_fee = fee(q, s0, f0, case), fee(q, spot[end][0], future[end][0], case)
        mismatch = q * s0 * number(case["entry_mismatch_fraction"])
        overhead = number(case["annual_overhead_usdt"]) * D(end - begin) / (365 * DAY)
        reserve = number(p["capital_usdt"]) - q * s0 - entry_fee - mismatch
        funding = sum(flows.values(), D(0))
        basis = q * (spot[end][0] - s0 + f0 - future[end][0])
        profit = (
            reserve
            + funding
            - overhead
            + q * spot[end][0]
            + q * (f0 - future[end][0])
            - exit_fee
            - number(p["capital_usdt"])
        )
        bounds, jumps, breaches = [], [], 0
        for t in sorted(marks):
            collateral = reserve - number(case["annual_overhead_usdt"]) * D(t + HOUR - begin) / (
                365 * DAY
            )
            collateral += sum(
                (v for k, v in flows.items() if k < t or (t <= k < t + HOUR and v < 0)), D(0)
            )
            high = marks[t][1]
            normal = collateral + q * f0 - D("1.015") * q * high
            jump = collateral + q * f0 - D("1.015") * q * high * D("1.3")
            bounds.append(normal)
            jumps.append(jump)
            breaches += int(normal <= 0 or jump <= 0)
        curve = [number(p["capital_usdt"])]
        for day in range(begin, end, DAY):
            until = day + DAY
            s, f = (
                (spot[end][0], future[end][0]) if until == end else (spot[day][3], future[day][3])
            )
            value = reserve + q * s + q * (f0 - f) - fee(q, s, f, case)
            value += sum((v for t, v in flows.items() if t < until), D(0))
            value -= number(case["annual_overhead_usdt"]) * D(until - begin) / (365 * DAY)
            curve.append(value)
        weekly = [curve[i + 7] - curve[i] for i in range(0, len(curve) - 1, 7)]
        peak, dd = curve[0], D(0)
        for equity in curve[1:]:
            peak, dd = max(peak, equity), min(dd, equity / max(peak, equity) - 1)
        calculated[name] = {
            "profit_usdt": profit,
            "basis_usdt": basis,
            "funding_usdt": funding,
            "entry_cost_usdt": entry_fee,
            "exit_cost_usdt": exit_fee,
            "overhead_usdt": overhead,
            "mismatch_usdt": mismatch,
            "minimum_surplus_usdt": min(bounds),
            "minimum_jump_surplus_usdt": min(jumps),
            "margin_breach_hours": breaches,
            "daily_liquidation_drawdown_fraction": dd,
            "weekly_profit_usdt": weekly,
            "negative_weeks": sum(v < 0 for v in weekly),
            "daily_equity_usdt": curve,
            "return_fraction": profit / number(p["capital_usdt"]),
        }
    return q, calculated


def walk(levels, quantity, side):
    remaining, total, prior = quantity, D(0), None
    for row in levels:
        price, size = map(number, row[:2])
        if min(price, size) <= 0 or (
            prior is not None
            and ((side == "asks" and price <= prior) or (side == "bids" and price >= prior))
        ):
            raise ValueError("Invalid book ordering/level")
        prior = price
        taken = min(remaining, size)
        total += taken * price
        remaining -= taken
    if remaining != 0:
        raise ValueError("Insufficient depth")
    return total / quantity


def live_calculation(p, first, last, funding):
    a, b = number(first["sf"]["step"]), number(first["ff"]["step"])
    scale = 10 ** max(-int(a.as_tuple().exponent), -int(b.as_tuple().exponent), 0)
    step = D(math.lcm(int(a * scale), int(b * scale))) / scale
    q = (number(p["spot_budget_usdt"]) / number(first["spot"]["asks"][0][0]) // step) * step
    s0, f0 = walk(first["spot"]["asks"], q, "asks"), walk(first["future"]["bids"], q, "bids")
    s1, f1 = walk(last["spot"]["bids"], q, "bids"), walk(last["future"]["asks"], q, "asks")
    duration = D(last["quote_ns"] // 1000000 - first["quote_ns"] // 1000000)
    out = {}
    for name, c in p["costs"].items():
        receipts = sum(
            (
                q
                * number(r["fundingRate"])
                * number(r["markPrice"])
                * (number(c["positive_funding_multiplier"]) if number(r["fundingRate"]) > 0 else 1)
                for r in funding
            ),
            D(0),
        )
        out[name] = q * (s1 - s0 + f0 - f1) + receipts - fee(q, s0, f0, c) - fee(q, s1, f1, c)
        out[name] -= q * s0 * number(c["entry_mismatch_fraction"]) + number(
            c["annual_overhead_usdt"]
        ) * duration / (365 * DAY)
    return out


def audit(directory, protocol_path):
    p = parse(protocol_path.read_bytes())
    result = parse((directory / "results.json").read_bytes())
    sources = parse((directory / "sources.json").read_bytes())
    groups = {k: [] for k in ("spot_daily", "future_daily", "funding", "mark")}
    end = int(datetime.fromisoformat(p["historical_end"]).timestamp() * 1000)
    identifiers, payloads = set(), {}
    for meta in sources:
        if meta["id"] in identifiers:
            raise ValueError("Duplicate raw source")
        identifiers.add(meta["id"])
        path = (directory / meta["raw_file"]).resolve()
        if not path.is_relative_to((directory / "raw").resolve()):
            raise ValueError("Source path escaped")
        u = urlsplit(meta["url"])
        if (
            u.scheme != "https"
            or u.netloc not in {"api.binance.com", "fapi.binance.com", "www.okx.com"}
            or any(v in u.path.lower() for v in ("account", "order", "trade/"))
        ):
            raise ValueError("Unexpected public source URL")
        raw = gzip.decompress(path.read_bytes())
        if (
            hashlib.sha256(raw).hexdigest() != meta["sha256"]
            or parse(path.with_name(meta["id"] + ".json").read_bytes()) != meta
        ):
            raise ValueError("Raw source changed")
        if meta["error"]:
            continue
        payload = parse(raw)
        payloads[meta["id"]] = payload
        if meta["name"] in groups:
            selected = [
                r
                for r in payload
                if (r["fundingTime"] if meta["name"] == "funding" else r[0]) <= end
            ]
            groups[meta["name"]].extend(selected)
    differences = []

    def equal(actual, expected):
        if isinstance(expected, list):
            if len(actual) != len(expected):
                raise ValueError("Audit array length mismatch")
            for x, y in zip(actual, expected, strict=True):
                equal(x, y)
        else:
            diff = abs(number(actual) - number(expected))
            differences.append(diff)
            if diff > D("0.0000001"):
                raise ValueError("Accounting disagreement: " + str(diff))

    historical_status = "NOT_AUDITED_FAILED_COMPONENT"
    if result["historical"]["status"] == "PASS":
        q, cases = rebuild(p, groups)
        equal(result["historical"]["quantity_btc"], q)
        for name, metrics in cases.items():
            for field, expected in metrics.items():
                equal(result["historical"]["cases"][name][field], expected)
        historical_status = "PASS"
    live_status = "NOT_AUDITED_FAILED_COMPONENT"
    if result["live"]["status"] == "QUOTED_SHADOW_ROUND_TRIP":
        rows = parse((directory / "live_samples.json").read_bytes())
        previous, decisions, recorded_samples = "0" * 64, {}, []
        journal = (directory / "ledger.jsonl").read_bytes()
        if not journal.endswith(b"\n"):
            raise ValueError("Incomplete decision journal")
        for index, line in enumerate(journal.splitlines()):
            item = parse(line)
            digest = item.pop("sha256")
            canonical = json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
            if (
                item["sequence"] != index
                or item["previous"] != previous
                or hashlib.sha256(canonical).hexdigest() != digest
            ):
                raise ValueError("Decision journal changed")
            previous = digest
            if item["kind"] == "SAMPLE_DECISION":
                if item["slot"] in decisions:
                    raise ValueError("Duplicate sample decision")
                decisions[item["slot"]] = item["known_at"]
            elif item["kind"] == "SAMPLE_RESULT":
                if item["slot"] not in decisions:
                    raise ValueError("Quote without prior decision")
                row = item["payload"]
                recorded_samples.append(row)
                snap = row["snapshot"]
                if snap:
                    if (
                        snap["quote_ns"] / 1e9
                        < datetime.fromisoformat(decisions[item["slot"]]).timestamp()
                    ):
                        raise ValueError("Backdated quote")
                    metas = {r["name"]: r for r in snap["sources"]}
                    for venue in ("spot", "future"):
                        meta = metas[venue + "_book"]
                        if snap[venue] != payloads[meta["id"]]:
                            raise ValueError("Live book differs from raw response")
        if rows != recorded_samples:
            raise ValueError("Derived samples differ from durable journal")
        fund = parse((directory / "live_cashflow_inputs.json").read_bytes())["funding"]
        values = live_calculation(p, rows[0]["snapshot"], rows[-1]["snapshot"], fund)
        for name, expected in values.items():
            equal(
                result["live"]["value"]["cases"][name]["modeled_liquidation_profit_usdt"], expected
            )
        live_status = "PASS"
    return {
        "status": "PASS" if historical_status == live_status == "PASS" else "PARTIAL",
        "raw_sources_verified": len(sources),
        "historical_accounting": historical_status,
        "live_accounting": live_status,
        "numeric_comparisons": len(differences),
        "maximum_difference_usdt": str(max(differences, default=D(0))),
        "production_modules_imported": False,
        "author_independence": False,
        "actual_execution_certified": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data, args.protocol)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2)
    print(json.dumps(result))
    raise SystemExit(int(result["status"] != "PASS"))
