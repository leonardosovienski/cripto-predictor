"""Run the two preregistered BTC streams offline, preserving every cost scenario."""

import argparse
import gzip
import json
from pathlib import Path

from scripts.backtest_btc_basis import make_plan, simulate, verdict
from scripts.basis_data import EVIDENCE, ROOT, cost_scenarios, load, protocol, sha, write


def verify_code() -> dict:
    freeze = json.loads((EVIDENCE / "implementation_freeze.json").read_text(encoding="utf-8"))
    for name, expected in freeze["files"].items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError("Code changed since pre-evaluation freeze: " + name)
    return freeze


def run(data_dir: Path, output: Path) -> None:
    spec = protocol()
    freeze = verify_code()
    output.mkdir(parents=True, exist_ok=False)
    data, manifest = load(data_dir)
    print("Verified raw sources:", len(manifest["sources"]), flush=True)
    summaries = {}
    for rule in spec["streams"]:
        destination = output / rule["id"]
        destination.mkdir()
        plan = make_plan(data, rule)
        (destination / "plan.json.gz").write_bytes(
            gzip.compress(json.dumps(plan, separators=(",", ":")).encode(), mtime=0)
        )
        scenarios = {}
        for name, cost in cost_scenarios(spec).items():
            result = simulate(data, plan, cost)
            scenarios[name] = result
            (destination / (name + ".json.gz")).write_bytes(
                gzip.compress(
                    json.dumps(result, separators=(",", ":"), allow_nan=False).encode(), mtime=0
                )
            )
        summaries[rule["id"]] = {
            "verdict": verdict(scenarios),
            "decisions": len(plan["decisions"]),
            "registered_signaled_hedges": len(plan["spells"]),
            "scenarios": {k: v["summary"] for k, v in scenarios.items()},
        }
        print(
            rule["id"],
            summaries[rule["id"]]["verdict"],
            {k: v["summary"]["profit_usdt"] for k, v in scenarios.items()},
            flush=True,
        )
    result = {
        "protocol_id": spec["id"],
        "protocol_sha256": manifest["protocol_sha256"],
        "implementation_freeze": freeze,
        "data_manifest_sha256": sha((data_dir / "manifest.json").read_bytes()),
        "source_count": len(manifest["sources"]),
        "source_bytes": manifest["download_bytes"],
        "streams": summaries,
        "evidence_class": "ADAPTIVE_HISTORICAL_NOT_INDEPENDENT_CONFIRMATION",
        "real_profit_certified": False,
    }
    write(output / "results.json", result)
    hashes = {
        p.relative_to(output).as_posix(): sha(p.read_bytes())
        for p in sorted(output.rglob("*"))
        if p.is_file()
    }
    write(output / "FILES_SHA256.json", hashes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.data, args.output)
