"""Reproduce fixed BTC AR2 from preserved data and bound adjacent renewal costs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from GarimpoInvestimentos.renewal_research import renewal_bound
from scripts.backtest_absolute_carry import ENTRY, carry_decisions, load_dataset, simulate
from scripts.collect_absolute_carry import END, PROTOCOL, write

ROOT = Path(__file__).resolve().parents[1]


def diagnose(data: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(
            "Use a new output directory; historical results cannot be overwritten"
        )
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assets, manifest = load_dataset(data, PROTOCOL)
    asset = assets["BTCUSDT"]
    output.mkdir(parents=True)
    decisions = carry_decisions(asset, "AR2")
    write(output / "decisions.json", decisions)
    results = {}
    for scenario in ("base", "adverse", "compression"):
        costs = protocol["carry_costs"][scenario]
        reference = simulate(asset, decisions, costs)
        original_path = (
            ROOT
            / f"docs/evidence/absolute_research_20260908/absolute-results-v3/carry/AR2_BTCUSDT_{scenario}_ledger.json"
        )
        original = json.loads(original_path.read_text(encoding="utf-8"))
        errors = {
            key: abs(reference[key] - original[key])
            for key in (
                "profit_usdt_mechanical",
                "ending_usdt_mechanical",
                "funding_usdt",
                "basis_pnl_usdt",
                "fees_slippage_usdt",
                "residual_cost_usdt",
                "unhedged_shock_usdt",
            )
        }
        if max(errors.values()) > 1e-7 or reference["spells"] != original["spells"]:
            raise ValueError("Reproduced AR2 differs from the preserved reference")
        identities = ["BINANCE:SPOT:BTCUSDT:USDT", "BINANCE:USDM-PERP:BTCUSDT:USDT"]
        spec = {
            "currency": "USDT",
            "instruments": identities,
            "start_ms": ENTRY,
            "end_ms": END,
            "quantity_step": "0.001",
            "costs": costs,
            "reference": reference,
            "spells": [row | {"instruments": identities} for row in reference["spells"]],
            "funding_events": [
                row for row in asset["funding"] if ENTRY <= row["fundingTime"] < END
            ],
            "evidence_ref": original_path.relative_to(ROOT).as_posix(),
        }
        bound = renewal_bound(spec)
        results[scenario] = {
            "bound": bound,
            "baseline_max_numeric_error": max(errors.values()),
            "original_ledger_sha256": hashlib.sha256(original_path.read_bytes()).hexdigest(),
            "reference_risk": {
                key: reference[key]
                for key in (
                    "active_days",
                    "cash_weeks",
                    "maximum_drawdown_daily_close_and_final_unwind",
                    "minimum_hourly_collateral_surplus_usdt",
                    "minimum_30pct_mark_jump_surplus_usdt",
                    "first_conservative_margin_breach",
                    "first_jump_breach",
                    "by_year",
                    "concentration",
                    "bootstrap",
                )
            },
        }
        write(output / f"{scenario}_reference.json", reference)
        write(output / f"{scenario}_bound.json", results[scenario])
        print(
            json.dumps(
                {
                    "scenario": scenario,
                    "reference": bound["reference_partial_remainder"],
                    "renewals": bound["adjacent_renewals"],
                    "delta_savings": bound["delta_turnover_savings_only"],
                    "optimistic_upper_bound": bound["extended_optimistic_upper_bound_not_profit"],
                }
            ),
            flush=True,
        )
    report = {
        "id": "AR2-BTC-RENEWAL-BOUND-20260909",
        "capital_permission": False,
        "source_manifest_sha256": hashlib.sha256((data / "manifest.json").read_bytes()).hexdigest(),
        "source_protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "raw_sources_verified": len(manifest["sources"]),
        "normalized_files_verified": len(manifest["normalized"]),
        "signal_policy_variants": 1,
        "symbol": "BTCUSDT",
        "scenarios": results,
        "historical_data_directory": str(data.resolve()),
    }
    write(output / "results.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    diagnose(args.data, args.output)


if __name__ == "__main__":
    main()
