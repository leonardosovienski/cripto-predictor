"""Detect missing/modified installed distribution files against their RECORD.

This is an integrity check, not a signature or a profitability attestation.
"""

import argparse
import base64
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path

PACKAGES = (
    "numpy",
    "scikit-learn",
    "scipy",
    "httpx",
    "predictor-core",
    "predictor-ops",
    "distlib",
    "virtualenv",
)


def verify():
    result = {}
    for name in PACKAGES:
        package = metadata.distribution(name)
        checked, missing, mismatches = 0, [], []
        for item in package.files or []:
            if item.hash is None:
                continue
            path = item.locate()
            if not path.exists():
                missing.append(str(item))
                continue
            actual = (
                base64.urlsafe_b64encode(hashlib.new(item.hash.mode, path.read_bytes()).digest())
                .rstrip(b"=")
                .decode()
            )
            checked += 1
            if actual != item.hash.value:
                mismatches.append(str(item))
        result[name] = {
            "version": package.version,
            "files_checked": checked,
            "missing": missing,
            "mismatches": mismatches,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    failed = [
        name
        for name, row in result.items()
        if row["missing"] or row["mismatches"] or not row["files_checked"]
    ]
    print(
        json.dumps(
            {
                "status": "FAIL" if failed else "PASS",
                "failed_packages": failed,
                "files_checked": sum(row["files_checked"] for row in result.values()),
            }
        )
    )
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
