"""Independent Decimal and raw-source audit of saved results, no model imports."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path
from urllib.parse import parse_qs, urlparse

D = Decimal
DAY = 86_400_000
HOUR = DAY // 24
END = int(datetime(2026, 9, 7, tzinfo=UTC).timestamp() * 1000)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def timestamp(value):
    t = int(value)
    return t // 1000 if t > 100_000_000_000_000 else t


def assert_near(actual, expected, tolerance="0.000001"):
    if abs(D(str(actual)) - D(str(expected))) > D(tolerance):
        raise AssertionError(f"Independent discrepancy {actual} vs {expected}")


def audit_carry(directory: Path, results: Path, protocol: dict):
    manifest = read(directory / "manifest.json")
    raw_data = defaultdict(dict)
    for source in manifest["sources"]:
        payload = gzip.decompress((directory / source["raw"].replace("\\", "/")).read_bytes())
        assert sha(payload) == source["sha256"]
        url = urlparse(source["url"])
        query = parse_qs(url.query)
        values = json.loads(payload)
        if "symbol" not in query:
            continue
        symbol = query["symbol"][0]
        kind = (
            "funding"
            if "fundingRate" in url.path
            else "mark_hourly"
            if "markPrice" in url.path
            else "spot_daily"
            if url.netloc == "api.binance.com"
            else "perp_daily"
        )
        for row in values:
            t = row["fundingTime"] if kind == "funding" else row[0]
            if t in raw_data[symbol, kind]:
                assert raw_data[symbol, kind][t] == row
            raw_data[symbol, kind][t] = row
    for (symbol, kind), rows in raw_data.items():
        normalized = json.loads(
            gzip.decompress((directory / f"{symbol}_{kind}.json.gz").read_bytes())
        )
        expected = [r if kind == "funding" or t < END else r[:2] for t, r in sorted(rows.items())]
        assert normalized == expected, (symbol, kind)
    checked_spells, checked_hours = 0, 0
    maximum_difference = D(0)
    for path in sorted((results / "carry").glob("*_ledger.json")):
        name, symbol, scenario, _ = path.stem.split("_")
        row = read(path)
        c = protocol["carry_costs"][scenario]
        costs = {k: D(str(v)) for k, v in c.items()}
        spot, perp, mark, events = [
            raw_data[symbol, k] for k in ("spot_daily", "perp_daily", "mark_hourly", "funding")
        ]
        first = row["spells"][0]["entry_ms"] if row["spells"] else None
        total = D(5000)
        min_surplus = min_jump = D("Infinity")
        for spell in row["spells"]:
            entry, exit_t = spell["entry_ms"], spell["exit_ms"]
            overhead_before = costs["annual_residual_usdt"] * D((entry - first) // DAY) / 365
            before = total - overhead_before
            assert_near(before, spell["initial_equity_usdt"])
            s0, s1 = [D(spot[t][1]) for t in (entry, exit_t)]
            f0, f1 = [D(perp[t][1]) for t in (entry, exit_t)]
            q = D(str(spell["quantity"]))
            assert q * s0 <= D("0.25") * before + D("0.000001")
            for key, expected in (
                ("spot_entry", s0),
                ("spot_exit", s1),
                ("perp_entry", f0),
                ("perp_exit", f1),
            ):
                assert_near(spell[key], expected)
            event_flows = defaultdict(list)
            for t, e in events.items():
                if entry // HOUR < t // HOUR and t < exit_t:
                    amount = q * D(e["markPrice"]) * D(e["fundingRate"])
                    if amount > 0:
                        amount *= costs["positive_funding_multiplier"]
                    event_flows[t // HOUR * HOUR].append(amount)
            funding = sum((v for flows in event_flows.values() for v in flows), D(0))

            def fee(s, f):
                return (
                    q
                    * (
                        s * (costs["spot_fee_bps_side"] + costs["slippage_bps_each_leg"])
                        + f * (costs["perp_fee_bps_side"] + costs["slippage_bps_each_leg"])
                    )
                    / 10000
                )

            entry_cost, exit_cost = fee(s0, f0), fee(s1, f1)
            shock = q * s0 * costs["entry_unhedged_shock_fraction_notional"]
            basis = q * (s1 - s0 + f0 - f1)
            pnl = funding + basis - entry_cost - exit_cost - shock
            for key, expected in (
                ("funding_usdt", funding),
                ("basis_pnl_usdt", basis),
                ("entry_cost_usdt", entry_cost),
                ("exit_cost_usdt", exit_cost),
                ("net_trading_pnl_usdt", pnl),
            ):
                assert_near(spell[key], expected)
                maximum_difference = max(maximum_difference, abs(D(str(spell[key])) - expected))
            total += pnl
            cash = before - q * s0 - entry_cost - shock
            for h in range(entry, exit_t, HOUR):
                if h % DAY == 0:
                    cash -= costs["annual_residual_usdt"] / 365
                flows = event_flows[h]
                worst_cash = cash + sum((v for v in flows if v < 0), D(0))
                high = D(mark[h][2])
                min_surplus = min(min_surplus, worst_cash + q * f0 - q * high * D("1.015"))
                min_jump = min(min_jump, worst_cash + q * f0 - q * high * D("1.3") * D("1.015"))
                cash += sum(flows, D(0))
                checked_hours += 1
            checked_spells += 1
        overhead = costs["annual_residual_usdt"] * D((END - first) // DAY) / 365 if first else D(0)
        assert_near(row["ending_usdt_mechanical"], total - overhead)
        if row["spells"]:
            assert_near(row["minimum_hourly_collateral_surplus_usdt"], min_surplus)
            assert_near(row["minimum_30pct_mark_jump_surplus_usdt"], min_jump)
    return {
        "raw_responses": len(manifest["sources"]),
        "normalized_series_rebuilt_from_raw": len(raw_data),
        "hedge_spells_decimal_checked": checked_spells,
        "hourly_margin_checks_decimal": checked_hours,
        "maximum_cashflow_difference_usdt": str(maximum_difference),
        "all_twelve_cost_streams_reconciled": True,
    }


def audit_spot(history: Path, results: Path):
    manifest = read(history / "acquisition.json")
    data = {}
    for pair in manifest["pairs"]:
        path = history / "pairs" / f"{pair['symbol']}.json.gz"
        assert sha(path.read_bytes()) == pair["normalized_sha256"]
        rows = json.loads(gzip.decompress(path.read_bytes()))["rows"]
        data[pair["symbol"]] = {r[0]: r for r in rows}
    decisions = read(results / "spot/decisions.json")
    weekly = read(results / "spot/weekly_results.json")
    identity_path = (
        Path(__file__).resolve().parents[1] / "docs/evidence/altcoin_payoff_20260907/results.json"
    )
    resolutions = {
        (r["symbol"], r["entry"]): r for r in read(identity_path)["identity_resolutions"]
    }
    holds = {(h["symbol"], h["date"]): h for w in weekly for h in w["holdings"]}
    migration_checks = []
    requested = set()
    checked_eligible = 0
    for decision in decisions:
        t = int(datetime.fromisoformat(decision["date"]).replace(tzinfo=UTC).timestamp() * 1000)
        eligible = []
        for symbol, rows in data.items():
            bars = [rows.get(d) for d in range(t - 91 * DAY, t - DAY, DAY)]
            if any(
                r is None
                or r[7] != r[0] + DAY - 1
                or any(not math.isfinite(v) or v <= 0 for v in r[1:7])
                for r in bars
            ):
                continue
            if statistics.median(r[6] for r in bars[-30:]) < 5_000_000:
                continue
            eligible.append(
                (
                    symbol,
                    D(str(bars[-1][4])) / D(str(bars[-31][4])),
                    D(str(bars[-1][4])) / D(str(bars[-8][4])),
                )
            )
        assert len(eligible) == decision["eligible"]
        checked_eligible += len(eligible)
        qualified = sorted(
            (r for r in eligible if r[1] > 1 and r[2] > 1), key=lambda r: (-r[1], r[0])
        )
        assert (
            [r[0] for r in qualified[:5]] == decision["selected"]
            if len(eligible) >= 10
            else not decision["selected"]
        )
        for symbol in decision["selected"]:
            for d in range(t - 91 * DAY, t - DAY, DAY):
                requested.add((symbol, d))
            h = holds[symbol, decision["date"]]
            if h["outcome_status"] == "DIRECT_DAILY_PRICE_PROXY":
                for d in range(t, t + 7 * DAY, DAY):
                    requested.add((symbol, d))
            else:
                resolution = resolutions[symbol, decision["date"]]
                assert resolution["status"] == h["outcome_status"] == "QUANTITY_ADJUSTED_DAILY_MARK"
                assert resolution["source"] == h["resolution_source"]
                requested.add((symbol, t))
                requested.add((resolution["exit_pair"], t + 6 * DAY))
                migration_checks.append(
                    {
                        "symbol": symbol,
                        "entry": decision["date"],
                        "successor": resolution["exit_pair"],
                        "ratio": resolution["new_units_per_old"],
                        "source": resolution["source"],
                    }
                )
    raw = {}
    sources = 0
    for path in (history / "raw").glob("*.json"):
        meta = read(path)
        payload = gzip.decompress(path.with_suffix(".bin.gz").read_bytes())
        assert sha(payload) == meta["sha256"]
        sources += 1
        url = urlparse(meta["url"])
        if url.path != "/api/v3/klines":
            continue
        symbol = parse_qs(url.query)["symbol"][0]
        for row in json.loads(payload):
            key = (symbol, timestamp(row[0]))
            if key in requested:
                if key in raw:
                    assert raw[key] == row
                raw[key] = row
    # Only bars actually present are required for the causal Saturday window and held outcome.
    missing = requested - raw.keys()
    assert not missing, f"Selected source bars unavailable: {list(missing)[:3]}"
    for (symbol, t), row in raw.items():
        normalized = data[symbol][t]
        assert [float(row[i]) for i in (1, 2, 3, 4, 5, 7)] == normalized[1:7]
        assert timestamp(row[6]) == normalized[7]
    checks = 0
    for slip in (0, 10, 40, 90):
        equity = D(5000)
        for week in weekly:
            t = int(datetime.fromisoformat(week["date"]).replace(tzinfo=UTC).timestamp() * 1000)
            factor = 1 - D("0.2") * len(week["holdings"])
            for h in week["holdings"]:
                if h["outcome_status"] == "DIRECT_DAILY_PRICE_PROXY":
                    gross_factor = D(raw[h["symbol"], t + 6 * DAY][4]) / D(raw[h["symbol"], t][1])
                else:
                    resolution = resolutions[h["symbol"], week["date"]]
                    gross_factor = (
                        D(resolution["new_units_per_old"])
                        * D(raw[resolution["exit_pair"], t + 6 * DAY][4])
                        / D(raw[h["symbol"], t][1])
                    )
                    assert_near(
                        resolution["successor_close"], raw[resolution["exit_pair"], t + 6 * DAY][4]
                    )
                assert_near(h["gross_return"], gross_factor - 1, "0.00000000001")
                leg = D("0.999") * (1 - D(slip) / 10000)
                factor += D("0.2") * gross_factor * leg**2
                checks += 1
            assert_near(week["factors_by_extra_bps"][str(slip)], factor, "0.00000000001")
            equity *= factor
        summary = read(results / "spot/results.json")
        assert_near(summary["overall"]["cost_scenarios"][str(slip)]["ending_5000_usdt"], equity)
    return {
        "normalized_histories": len(data),
        "past_eligible_observations_ranked_independently": checked_eligible,
        "weekly_decisions_checked": len(decisions),
        "original_raw_hashes_verified": sources,
        "selected_feature_and_outcome_raw_bars_traced": len(raw),
        "selected_payoffs_decimal_checked_across_four_costs": checks,
        "selected_identity_resolutions": migration_checks,
        "selected_censored_outcomes": 0,
        "historical_universe_completeness_certified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carry-data", type=Path, required=True)
    parser.add_argument("--altcoin-data", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = read(root / "docs/evidence/absolute_research_20260908/protocol.json")
    with localcontext() as context:
        context.prec = 40
        result = {
            "carry": audit_carry(args.carry_data, args.results, protocol),
            "spot": audit_spot(args.altcoin_data, args.results),
            "status": "PASS",
        }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
