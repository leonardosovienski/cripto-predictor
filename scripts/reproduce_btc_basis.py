"""Offline replay with byte comparison and a separate Decimal accounting audit."""

import argparse
import json
from pathlib import Path

from scripts.audit_btc_basis import audit
from scripts.basis_data import sha, write
from scripts.plan_btc_hedge import replay
from scripts.run_btc_basis import run


def reproduce(data: Path, expected: Path, output: Path, diagnostic: Path | None = None):
    output.mkdir(parents=True, exist_ok=False)
    run(data, output / "results")
    reference = json.loads((expected / "FILES_SHA256.json").read_text(encoding="utf-8"))
    for name, digest in reference.items():
        if sha((expected / name).read_bytes()) != digest:
            raise ValueError("Changed expected result")
        if sha((output / "results" / name).read_bytes()) != digest:
            raise ValueError("Offline reproduction differs: " + name)
    accounting = audit(data, output / "results", output / "audit.json")
    diagnostic_equal = None
    if diagnostic:
        replay(diagnostic, output / "net_hedge_plans.json")
        diagnostic_equal = (output / "net_hedge_plans.json").read_bytes() == (
            diagnostic / "net_hedge_plans.json"
        ).read_bytes()
        if not diagnostic_equal:
            raise ValueError("Saved-quote execution plan differs")
    result = {
        "status": "PASS",
        "historical_result_files_byte_identical": len(reference),
        "public_source_responses_rebuilt": accounting["raw_sources_rebuilt"],
        "accounting_audit": accounting["status"],
        "saved_quote_plans_byte_identical": diagnostic_equal,
        "network_requests": 0,
    }
    write(output / "reproduction_check.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostic", type=Path)
    args = parser.parse_args()
    reproduce(args.data, args.expected, args.output, args.diagnostic)
