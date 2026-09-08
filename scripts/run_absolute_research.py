"""Reproduce the registered five streams offline into a new output directory."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.backtest_absolute_carry import load_dataset, run_carry
from scripts.backtest_absolute_spot import run_spot, selector_diagnosis
from scripts.collect_absolute_carry import write

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/absolute_research_20260908"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carry-data", type=Path, required=True)
    parser.add_argument("--altcoin-data", type=Path, required=True)
    parser.add_argument("--old-scores", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    protocol_path = EVIDENCE / "protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    registry = json.loads((EVIDENCE / "trials.json").read_text(encoding="utf-8"))
    if hashlib.sha256(protocol_path.read_bytes()).hexdigest() != registry["protocol_sha256"]:
        raise ValueError("Registered protocol mismatch")
    assets, manifest = load_dataset(args.carry_data, protocol_path)
    print("Carry sources and chronology verified:", len(manifest["sources"]), flush=True)
    diagnosis = selector_diagnosis(args.old_scores)
    write(args.output / "selector_diagnosis.json", diagnosis)
    carry = run_carry(assets, protocol["carry_costs"], args.output / "carry")
    print("Four carry streams complete", flush=True)
    spot = run_spot(args.altcoin_data, args.output / "spot", ROOT)
    print("One spot stream complete", flush=True)
    result = {
        "protocol_id": protocol["id"],
        "protocol_sha256": registry["protocol_sha256"],
        "causality_amendment_sha256": hashlib.sha256(
            (EVIDENCE / "causality_amendment.json").read_bytes()
        ).hexdigest(),
        "strategy_streams": 5,
        "evidence_class": "ADAPTIVE_HISTORICAL",
        "carry": carry,
        "spot": spot,
        "selector_diagnosis": diagnosis,
        "source_responses": len(manifest["sources"]),
        "future_data_used": False,
        "real_profit_certified": False,
    }
    write(args.output / "results.json", result)
    files = {
        p.relative_to(args.output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.output.rglob("*"))
        if p.is_file()
    }
    write(args.output / "FILES_SHA256.json", files)
    compact = {
        name: {
            scenario: round(row["profit_usdt_mechanical"], 6)
            for scenario, row in item["scenarios"].items()
        }
        for name, item in carry.items()
    }
    compact["AR3_UNIVERSE"] = {
        k: v["simulated_profit_5000_usdt"] for k, v in spot["overall"]["cost_scenarios"].items()
    }
    print(json.dumps(compact, indent=2), flush=True)


if __name__ == "__main__":
    main()
