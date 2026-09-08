"""Separate Decimal replay of stored decisions, cashflows, marks and margin bounds."""

import argparse
import gzip
import json
from collections import defaultdict
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

from scripts.basis_data import DAY, END, ENTRY, HOUR, cost_scenarios, load, protocol, sha, write

D = lambda value: Decimal(str(value))


def read_gz(path: Path):
    return json.loads(gzip.decompress(path.read_bytes()))


def audit(data_dir: Path, result_dir: Path, output: Path) -> dict:
    data, manifest = load(data_dir)
    spec = protocol()
    expected_files = json.loads((result_dir / "FILES_SHA256.json").read_text(encoding="utf-8"))
    for name, digest in expected_files.items():
        if sha((result_dir / name).read_bytes()) != digest:
            raise ValueError("Changed result file")
    comparisons, max_difference = 0, D(0)
    margin_checks, decisions_checked, economic_cases = 0, 0, 0

    def same(actual, expected):
        nonlocal comparisons, max_difference
        difference = abs(D(actual) - D(expected))
        comparisons += 1
        max_difference = max(max_difference, difference)
        if difference > D("0.0000001"):
            raise AssertionError(f"Decimal audit difference: {actual} vs {expected}")

    for rule in spec["streams"]:
        directory = result_dir / rule["id"]
        plan = read_gz(directory / "plan.json.gz")
        dated = rule["id"] == "BR1_DATED_BTC"
        spells = plan["spells"]
        expected_decision_hours = [
            t
            for t in range(ENTRY, END, HOUR)
            if (not dated or t % DAY == 0)
            and not any(p["entry_ms"] < t <= p["exit_ms"] for p in spells)
        ]
        assert [r["execution_ms"] for r in plan["decisions"]] == expected_decision_hours
        for decision in plan["decisions"]:
            t = decision["execution_ms"]
            assert decision["last_signal_close_ms"] == t - HOUR - 1
            assert decision["signal_bar_ms"] == t - 2 * HOUR
            symbol = decision["symbol"]
            if symbol:
                future = data[symbol + "_trade"] if dated else data["perp"]
                a, b = data["spot"].get(t - 2 * HOUR), future.get(t - 2 * HOUR)
                if a is not None and b is not None:
                    basis = D(b[4]) / D(a[4]) - 1
                    same(basis, decision["basis"])
                    assert decision["enter"] == (basis > D(rule["entry_basis_threshold"]))
                else:
                    assert not decision["enter"]
                for name, bars in (("spot", data["spot"]), ("future", future)):
                    day = t // DAY * DAY
                    totals = [
                        sum(D(bars[h][7]) for h in range(d, d + DAY, HOUR))
                        for d in range(day - 31 * DAY, day - DAY, DAY)
                    ]
                    median = sum(sorted(totals)[14:16]) / 2
                    reported_volume = decision[name + "_median_daily_quote_volume"]
                    assert abs(float(median) - reported_volume) <= max(
                        0.00001, abs(float(median)) * 1e-12
                    )
                    assert median >= 5_000_000
                if dated:
                    expiry = manifest["contracts"][symbol]
                    assert 30 * DAY <= expiry - t <= 120 * DAY
            else:
                assert not decision["enter"]
            decisions_checked += 1
        assert [r["execution_ms"] for r in plan["decisions"] if r["enter"]] == [
            p["entry_ms"] for p in spells
        ]
        for name, cost in cost_scenarios(spec).items():
            result = read_gz(directory / (name + ".json.gz"))
            if result["summary"]["profit_usdt"] is None:
                assert result["summary"]["failure"]
                continue
            economic_cases += 1
            completed = {s["entry_ms"]: s for s in result["spells"]}
            assert set(completed) == {p["entry_ms"] for p in spells}
            observations = {r["time_ms"]: r for r in result["hourly"]}
            events = defaultdict(list)
            for event in data["funding"] if not dated else []:
                events[int(event["fundingTime"]) // HOUR * HOUR].append(event)
            cash, overhead, funding_total = D(5000), D(0), D(0)
            holding, first = None, None
            min_nominal = min_jump = None
            first_nominal_breach = first_jump_breach = None
            expected_payments = []
            for t in range(ENTRY, END + HOUR, HOUR):
                if holding and t == holding["exit_ms"]:
                    q = D(holding["quantity"])
                    s = D(data["spot"][t][1])
                    if holding["exit_reason"] == "SETTLEMENT":
                        assert t == holding["expiry_ms"] and t % DAY == 8 * HOUR
                        records = [
                            v for v in data["delivery"] if int(v["deliveryTime"]) // DAY == t // DAY
                        ]
                        assert len(records) == 1
                        f = D(records[0]["deliveryPrice"])
                        rate = D(cost["settlement_fee_bps"])
                    else:
                        f = D(data[holding["trade_kind"]][t][1])
                        rate = D(cost["future_fee_bps"] + cost["slippage_bps"])
                    fee = (
                        q * (s * D(cost["spot_fee_bps"] + cost["slippage_bps"]) + f * rate) / 10000
                    )
                    same(fee, holding["exit_cost_usdt"])
                    same(s, holding["spot_exit"])
                    same(f, holding["future_exit"])
                    cash += q * (s + D(holding["future_entry"]) - f) - fee
                    holding = None
                if t == END:
                    same(cash, observations[t]["equity_usdt"])
                    break
                if t in completed:
                    holding = completed[t]
                    s = D(data["spot"][t][1])
                    f = D(data[holding["trade_kind"]][t][1])
                    q = (cash * D("0.25") / s / D("0.001")).to_integral_value(
                        rounding=ROUND_FLOOR
                    ) * D("0.001")
                    same(q, holding["quantity"])
                    same(s, holding["spot_entry"])
                    same(f, holding["future_entry"])
                    fee = (
                        q
                        * (
                            s * D(cost["spot_fee_bps"] + cost["slippage_bps"])
                            + f * D(cost["future_fee_bps"] + cost["slippage_bps"])
                        )
                        / 10000
                    )
                    mismatch = q * s * D(cost["entry_mismatch_fraction"])
                    same(fee, holding["entry_cost_usdt"])
                    same(mismatch, holding["mismatch_usdt"])
                    cash -= q * s + fee + mismatch
                    if first is None:
                        first = t
                residual = (
                    D(cost["annual_residual_usdt"]) / (365 * 24) if first is not None else D(0)
                )
                overhead += residual
                cash -= residual
                if holding:
                    q = D(holding["quantity"])
                    amounts = []
                    for event in events[t] if t > holding["entry_ms"] else []:
                        amount = q * D(event["markPrice"]) * D(event["fundingRate"])
                        if amount > 0:
                            amount *= D(cost["positive_funding_multiplier"])
                        amounts.append(amount)
                        expected_payments.append((int(event["fundingTime"]), amount))
                    high = D(data[holding["mark_kind"]][t][2])
                    negative = sum((x for x in amounts if x < 0), D(0))
                    nominal = (
                        cash
                        + negative
                        + q * (D(holding["future_entry"]) - high)
                        - D("0.015") * q * high
                    )
                    jump = (
                        cash
                        + negative
                        + q * (D(holding["future_entry"]) - high * D("1.3"))
                        - D("0.015") * q * high * D("1.3")
                    )
                    min_nominal = nominal if min_nominal is None else min(min_nominal, nominal)
                    min_jump = jump if min_jump is None else min(min_jump, jump)
                    if nominal <= 0 and first_nominal_breach is None:
                        first_nominal_breach = t
                    if jump <= 0 and first_jump_breach is None:
                        first_jump_breach = t
                    margin_checks += 2
                    total = sum(amounts, D(0))
                    cash += total
                    funding_total += total
                    equity = cash + q * (
                        D(data["spot"][t][4])
                        + D(holding["future_entry"])
                        - D(data[holding["mark_kind"]][t][4])
                    )
                else:
                    equity = cash
                same(equity, observations[t + HOUR - 1]["equity_usdt"])
            same(cash - 5000, result["summary"]["profit_usdt"])
            same(overhead, result["summary"]["residual_usdt"])
            same(funding_total, result["summary"]["funding_usdt"])
            if min_nominal is not None:
                same(min_nominal, result["summary"]["minimum_margin_surplus_usdt"])
                same(min_jump, result["summary"]["minimum_jump_surplus_usdt"])
            assert first_nominal_breach == result["summary"]["first_margin_breach_ms"]
            assert first_jump_breach == result["summary"]["first_jump_breach_ms"]
            assert len(expected_payments) == len(result["funding"])
            for (t, value), payment in zip(expected_payments, result["funding"], strict=True):
                assert t == payment["time_ms"]
                same(value, payment["amount_usdt"])
    report = {
        "status": "PASS",
        "raw_sources_rebuilt": len(manifest["sources"]),
        "normalized_series_rebuilt": len(manifest["groups"]),
        "decision_records_checked": decisions_checked,
        "economic_cost_cases_checked": economic_cases,
        "decimal_comparisons": comparisons,
        "maximum_absolute_difference_usdt": str(max_difference),
        "hourly_margin_and_jump_checks": margin_checks,
        "economic_engine_imported": False,
        "real_profit_certified": False,
    }
    write(output, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.data, args.results, args.output), indent=2))
