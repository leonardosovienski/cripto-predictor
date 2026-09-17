"""Preserve partial integration results without overriding any failing gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def summarize(work: Path, exit_code: int) -> dict[str, Any]:
    """Summarize recorded commands; absent evidence never becomes approval."""
    work = work.resolve()
    commands_path = work / "commands.json"
    records = json.loads(commands_path.read_text()) if commands_path.exists() else []
    if not isinstance(records, list):
        raise ValueError("commands.json must contain a list")
    checks = []
    expired_reports = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid command receipt")
        passed = (
            isinstance(record.get("exit_code"), int)
            and isinstance(record.get("expected_exit"), int)
            and record["exit_code"] == record["expected_exit"]
        )
        checks.append({"name": record.get("name"), "status": "PASS" if passed else "FAIL"})
        if record.get("name") == "ecosystem-offline" and not passed:
            relative = Path(record.get("log", ""))
            path = (work / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(work):
                raise ValueError("log path outside integration work directory")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != record.get("log_sha256"):
                raise ValueError("integration log digest mismatch")
            expired_reports.extend(
                line.strip()
                for line in raw.decode("utf-8", errors="replace").splitlines()
                if "atestado venceu em" in line and "segue ALIGNED" in line
            )
    result_path = work / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    completed = isinstance(result, dict) and result.get("status") == "PASS"
    passed = (
        exit_code == 0 and completed and bool(checks) and all(c["status"] == "PASS" for c in checks)
    )
    return {
        "schema_version": 1,
        "summarized_at": datetime.now(UTC).isoformat(),
        "overall": "PASS" if passed else "FAIL",
        "process_exit_code": exit_code,
        "validation_completed": completed,
        "checks": checks,
        "expired_attestation_reports": expired_reports,
        "current_validity": "BLOCKED_EXPIRED_ATTESTATION" if expired_reports else "NOT_DETERMINED",
        "economic_validation": False,
        "note": "Subcheck success is not approval of the full combination or economic validity.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crypto-sha", required=True)
    parser.add_argument("--work", required=True, type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    if work.exists():
        parser.error("--work must be a new directory; existing evidence is never overwritten")
    root = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        str(root / ".ci/integration-audit/validate.py"),
        "--crypto-sha",
        args.crypto_sha,
        "--work",
        str(work),
    ]
    exit_code = 1
    try:
        exit_code = subprocess.run(command, cwd=root, check=False, timeout=2600).returncode
    except subprocess.TimeoutExpired:
        print("Integration executor timed out; validation remains incomplete.", file=sys.stderr)
        exit_code = 124
    finally:
        work.mkdir(parents=True, exist_ok=True)
        try:
            summary = summarize(work, exit_code)
        except (OSError, ValueError, TypeError) as exc:
            summary = {
                "overall": "FAIL",
                "process_exit_code": exit_code,
                "receipt_error": str(exc),
                "economic_validation": False,
            }
        with (work / "remediation-summary.json").open("x", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        print(json.dumps(summary, indent=2))
    # Do not convert an expired attestation or incomplete run into success.
    return exit_code if exit_code else (0 if summary["overall"] == "PASS" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
