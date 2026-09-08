"""Verify/restore preserved data and audit offline. --full also replays all models."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/absolute_research_20260908"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        raise ValueError("Choose a new destination; never overwrite research or observer data")
    for name, expected in read(EVIDENCE / "reproduction_freeze.json").items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Code/specification bytes changed: {name}; use packaged exact bytes")
    archive = EVIDENCE / "RESEARCH_DATA.zip"
    if sha(archive) != read(EVIDENCE / "data_snapshot.json")["sha256"]:
        raise ValueError("Preserved data archive changed")
    destination.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            target = (destination / info.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Archive path escapes destination")
        z.extractall(destination)
    files = read(destination / "FILES_SHA256.json")
    for name, expected in files.items():
        if sha(destination / name) != expected["sha256"]:
            raise ValueError("Restored data bytes changed: " + name)
    completed = {
        "data_files_checked": len(files),
        "data_archive_sha256": sha(archive),
        "network_used": False,
    }
    common = [
        "--carry-data",
        str(destination / "carry"),
        "--altcoin-data",
        str(destination / "altcoin"),
    ]
    subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "scripts.audit_absolute_research",
            *common,
            "--results",
            str(EVIDENCE / "absolute-results-v3"),
            "--output",
            str(destination / "audit.json"),
        ],
        cwd=ROOT,
        check=True,
    )
    completed["independent_audit"] = "PASS"
    if args.full:
        replay = destination / "replay"
        subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "-m",
                "scripts.run_absolute_research",
                *common,
                "--old-scores",
                str(destination / "prior/scores.json.gz"),
                "--output",
                str(replay),
            ],
            cwd=ROOT,
            check=True,
        )
        expected_files = read(EVIDENCE / "absolute-results-v3/FILES_SHA256.json")
        for name, expected in expected_files.items():
            if sha(replay / name) != expected:
                raise ValueError("Replay differs from preserved result: " + name)
        completed["byte_identical_result_files"] = len(expected_files)
    (destination / "REPRODUCTION_CHECK.json").write_text(
        json.dumps(completed, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(completed, indent=2))


if __name__ == "__main__":
    main()
