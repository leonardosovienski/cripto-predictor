"""Independent Decimal reconciliation of the two already-observed carry cases.

No new markets, periods, trades or tuned parameters. No outside benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path

END = int(datetime(2026, 9, 7, tzinfo=UTC).timestamp() * 1000)
DAY = 86_400_000
START = END - 365 * DAY
SLOT = 8 * 3_600_000


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def review(directory: Path):
    manifest = read(directory / "manifest.json")
    checked = []
    for row in manifest:
        if row["artifact"].startswith(("BTCUSDT_", "ETHUSDT_")):
            path = directory / row["artifact"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError("raw source changed: " + row["artifact"])
            checked.append(row)
    if len(checked) != 8:
        raise ValueError("expected eight original raw responses")
    original = read(directory / "results.json")
    assets = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        raw = sorted(
            read(directory / f"{symbol}_funding_0.json")
            + read(directory / f"{symbol}_funding_1.json"),
            key=lambda r: r["fundingTime"],
        )
        if raw != read(directory / f"{symbol}_funding.json"):
            raise ValueError("normalized funding differs from original responses")
        buckets = [r["fundingTime"] // SLOT for r in raw]
        if buckets != list(range(START // SLOT, END // SLOT)):
            raise ValueError("missing, duplicated or out-of-period funding")
        if any(not START <= r["fundingTime"] < END for r in raw):
            raise ValueError("future funding")
        bars = {}
        for kind in ("spot", "mark"):
            rows = read(directory / f"{symbol}_{kind}_daily.json")
            if [r[0] for r in rows] != list(range(START, END + DAY, DAY)):
                raise ValueError("incomplete daily price endpoints")
            bars[kind] = rows
        # Only the opening field at the final cutoff is read. Later fields of
        # that candle cannot enter this accounting.
        s0, s1 = (Decimal(bars["spot"][i][1]) for i in (0, -1))
        f0, f1 = (Decimal(bars["mark"][i][1]) for i in (0, -1))
        quantity = Decimal(2500) / s0
        eligible = [r for r in raw if r["fundingTime"] // SLOT > START // SLOT]
        funding = sum(
            (quantity * Decimal(r["markPrice"]) * Decimal(r["fundingRate"]) for r in eligible),
            Decimal(0),
        )
        spot_pnl = quantity * (s1 - s0)
        short_pnl = quantity * (f0 - f1)
        basis = quantity * ((f0 - s0) - (f1 - s1))
        if abs(spot_pnl + short_pnl - basis) > Decimal("1e-25"):
            raise ValueError("hedged P&L identity does not reconcile")
        fees = quantity * (Decimal("0.001") * (s0 + s1) + Decimal("0.0005") * (f0 + f1))
        four_legs = quantity * (s0 + s1 + f0 + f1)
        slip = four_legs * Decimal("0.0005")
        net = funding + basis - fees - slip
        if abs(
            net - Decimal(str(original["assets"][symbol]["fixed_quantity"]["net_scenario_usdt"]))
        ) > Decimal("1e-8"):
            raise ValueError("independent calculation differs from saved result")
        scenarios = []
        for slip_bps in (0, 5, 10):
            after_trading = funding + basis - fees - four_legs * Decimal(slip_bps) / 10000
            for additional_fraction in ("0", "0.005", "0.01"):
                extra = Decimal(5000) * Decimal(additional_fraction)
                scenarios.append(
                    {
                        "slippage_bps_each_leg": slip_bps,
                        "additional_cost_fraction_of_capital": float(additional_fraction),
                        "simulated_net_usdt": float(after_trading - extra),
                        "meaning": "Pre-existing cost assumptions applied to the same fixed-quantity cashflows; not actual costs or a prediction.",
                    }
                )
        assets[symbol] = {
            "capital_reference_usdt": 5000,
            "spot_initial_notional_usdt": 2500,
            "cash_margin_reference_usdt": 2500,
            "quantity": str(quantity),
            "eligible_settlements": len(eligible),
            "funding_usdt": float(funding),
            "basis_pnl_usdt": float(basis),
            "assumed_trading_fees_usdt": float(fees),
            "assumed_slippage_usdt": float(slip),
            "simulated_profit_usdt": float(net),
            "simulated_return_on_total_capital": float(net / 5000),
            "simulated_ending_usdt": float(5000 + net),
            "additional_cost_budget_before_zero_profit_usdt": float(net),
            "additional_cost_budget_fraction_of_capital": float(net / 5000),
            "cost_scenarios": scenarios,
            "decision": "POSITIVE_HISTORICAL_PRICE_PROXY_NOT_VERIFIED_INVESTOR_PROFIT"
            if net > 0
            else "NONPOSITIVE_HISTORICAL_PRICE_PROXY",
            "actual_profit": None,
            "verified_net_brl_profit": None,
            "executable_margin_path_certified": False,
        }
    return {
        "id": "project-quality-review-20260907-v6-carry",
        "period": {"start": "2025-09-07", "end": "2026-09-07", "days": 365},
        "source_response_hashes_verified": len(checked),
        "raw_sources": checked,
        "arithmetic": "Independent Decimal reconstruction, fixed hedge quantity; eight raw responses and both normalized funding histories verified.",
        "assets": assets,
        "external_benchmark": False,
        "new_market_parameter_search": False,
        "prior_rejection": "Applied a benchmark later rejected by the user. Original evidence remains unchanged; that priority decision no longer determines the current absolute-profit objective.",
        "quality": "HISTORICAL_SIMULATED_POSITIVE_CARRY_EXISTS; NO_VERIFIED_INVESTOR_NET_PROFIT",
        "limitations": [
            "Already consumed single historical period; adaptive interpretation, not independent validation",
            "Spot and perpetual mark-price proxies are not executable fills",
            "Fees/slippage are assumptions, not account-specific realized costs",
            "Margin maintenance, intraday equity path and liquidation are not certified",
            "Account access, USDT/USD/BRL conversion, transfers and tax remain unknown",
            "Each asset uses its own hypothetical 5000 USDT; these are separate scenarios, not additive profits on one portfolio",
        ],
        "capital": False,
        "orders": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with localcontext() as context:
        context.prec = 40
        result = review(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                symbol: {
                    key: row[key]
                    for key in (
                        "simulated_profit_usdt",
                        "simulated_return_on_total_capital",
                        "decision",
                    )
                }
                for symbol, row in result["assets"].items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
