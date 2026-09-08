"""A fresh checkout must preserve published research bytes on every platform."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_checkout_preserves_published_research_freezes():
    record = json.loads(
        (ROOT / "docs/evidence/git_consolidation_20260908/reconciliation.json").read_bytes()
    )
    for name, expected in record["frozen_files_and_manifests"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name


def test_archived_research_deliverables_match_original_hashes():
    archive = ROOT / "docs/session_archive_20260908"
    manifest = json.loads((archive / "DELIVERABLES_SHA256.json").read_bytes())
    for name, expected in manifest.items():
        assert (
            hashlib.sha256((archive / "deliverables" / name).read_bytes()).hexdigest() == expected
        ), name
