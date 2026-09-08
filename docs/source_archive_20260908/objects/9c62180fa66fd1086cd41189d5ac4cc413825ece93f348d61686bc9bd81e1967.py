"""Offline verification of frozen carry results; no strategy search or profit forecast."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from scripts.backtest_absolute_carry import load_dataset, run_carry
from scripts.basis_data import write
from scripts.reproduce_btc_basis import reproduce

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "docs/evidence/absolute_research_20260908"
NEW = ROOT / "docs/evidence/basis_research_20260908"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(carry_data: Path, basis_data: Path, diagnostic: Path, output: Path):
    output.mkdir(parents=True, exist_ok=False)
    old_spec = read(OLD / "protocol.json")
    new_spec = read(NEW / "protocol.json")
    if old_spec["period"]["evaluation_start"] != new_spec["period"]["start"][:10]:
        raise ValueError("Different starting periods")
    if old_spec["period"]["end_exclusive"] != new_spec["period"]["end"][:10]:
        raise ValueError("Different cutoff dates")
    if digest(OLD / "protocol.json") != read(OLD / "trials.json")["protocol_sha256"]:
        raise ValueError("Changed carry protocol")

    with (
        patch.object(socket.socket, "connect", side_effect=RuntimeError("Offline verification")),
        patch.object(socket.socket, "connect_ex", side_effect=RuntimeError("Offline verification")),
        patch.object(socket, "create_connection", side_effect=RuntimeError("Offline verification")),
    ):
        assets, manifest = load_dataset(carry_data, OLD / "protocol.json")
        carry = run_carry(assets, old_spec["carry_costs"], output / "carry")
        previous = OLD / "absolute-results-v3"
        reference = read(previous / "FILES_SHA256.json")
        count = 0
        for name, expected in reference.items():
            if name.startswith("carry/"):
                if digest(previous / name) != expected or digest(output / name) != expected:
                    raise ValueError("Changed carry result: " + name)
                count += 1
        if count != 14:
            raise ValueError("Incomplete carry comparison")
        print(f"Carry: {count} result files byte-identical; 12 cost cases", flush=True)
        reproduce(basis_data, NEW / "results-v2", output / "basis", diagnostic)

    basis = read(output / "basis/results/results.json")["streams"]
    rows = {}
    for name, item in carry.items():
        cases = {}
        for cost, result in item["scenarios"].items():
            if result["initial_usdt"] != 5000 or result["weeks"] != 140:
                raise ValueError("Unexpected carry horizon/capital")
            cases[cost] = {
                "profit_usdt": result["profit_usdt_mechanical"],
                "return_fraction": result["return_fraction"],
                "calendar_contributions_usdt": {
                    y: v["pnl_usdt"] for y, v in result["by_year"].items()
                },
                "hedges": result["round_trip_hedges"],
                "active_weeks": result["active_weeks"],
                "cash_weeks": result["cash_weeks"],
                "minimum_jump_surplus_usdt": result["minimum_30pct_mark_jump_surplus_usdt"],
            }
        rows[name] = {"implementation": "existing", "scenarios": cases}
    for name, item in basis.items():
        cases = {}
        for cost, result in item["scenarios"].items():
            if result["active_weeks"] + result["cash_weeks"] != 140:
                raise ValueError("Unexpected basis horizon")
            if abs(result["ending_usdt"] - result["profit_usdt"] - 5000) > 1e-7:
                raise ValueError("Unexpected basis capital")
            cases[cost] = {
                "profit_usdt": result["profit_usdt"],
                "return_fraction": result["return_fraction"],
                "calendar_contributions_usdt": result["calendar_year_contributions_usdt"],
                "hedges": result["hedges"],
                "active_weeks": result["active_weeks"],
                "cash_weeks": result["cash_weeks"],
                "minimum_jump_surplus_usdt": result["minimum_jump_surplus_usdt"],
            }
        rows[name] = {"implementation": "added", "verdict": item["verdict"], "scenarios": cases}
    for item in rows.values():
        for case in item["scenarios"].values():
            if abs(sum(case["calendar_contributions_usdt"].values()) - case["profit_usdt"]) > 1e-7:
                raise ValueError("Calendar contributions do not reconcile")

    deltas = {}
    for name in basis:
        deltas[name] = {
            cost: {
                "existing_scenario": old_cost,
                "new_minus_existing_profit_usdt": (
                    rows[name]["scenarios"][cost]["profit_usdt"]
                    - rows["AR1_BTCUSDT"]["scenarios"][old_cost]["profit_usdt"]
                ),
            }
            for cost, old_cost in (
                ("base", "base"),
                ("adverse", "adverse"),
                ("stress", "compression"),
            )
        }
    result = {
        "scope": read(ROOT / "docs/evidence/profit_comparison_20260908/scope.json"),
        "verification": {
            "existing_carry_result_files_byte_identical": count,
            "existing_carry_source_responses_verified": len(manifest["sources"]),
            "basis": read(output / "basis/reproduction_check.json"),
            "basis_decimal_audit": read(output / "basis/audit.json"),
            "network_socket_connections_disabled_during_replay": True,
            "network_requests": 0,
        },
        "rows": rows,
        "added_models_vs_existing_btc_carry": deltas,
        "validated_future_expected_profit_usdt": None,
        "new_evidence_of_improved_future_profit": False,
        "independent_confirmation": False,
        "historical_strategies_changed": False,
        "projection_warning": "Historical arithmetic under assumed costs; future expected profit remains unknown.",
    }
    write(output / "comparison.json", result)
    write(
        output / "run_receipt.json",
        {
            "completed_utc": datetime.now(UTC).isoformat(),
            "script_sha256": digest(Path(__file__)),
            "comparison_sha256": digest(output / "comparison.json"),
            "scope_sha256": digest(ROOT / "docs/evidence/profit_comparison_20260908/scope.json"),
        },
    )
    print(json.dumps(deltas, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carry-data", type=Path, required=True)
    parser.add_argument("--basis-data", type=Path, required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compare(args.carry_data, args.basis_data, args.diagnostic, args.output)
