import json
import subprocess
from pathlib import Path

import pytest
from crypto_research_export.external import SOURCE, export_external
from research_bundle import digest, validate


def _source(root: Path, *, readable=True, derived=True, raw=False):
    path = root / SOURCE
    path.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "evidence_id": "fixture-evidence",
        "canonical_asset_id": "crypto:btc",
        "provider": "coinmetrics",
        "metric": "TxCnt.expanding_zscore",
        "feature_version": 1,
        "pit_grade": "RECEIPT_PIT",
        "observed_at": "2026-01-01T00:00:00+00:00",
        "effective_available_at": "2026-01-02T00:00:00+00:00",
        "derived_evidence": {"value": 1.25},
        "coverage": {"requested": 1, "supported": 1},
        "rights": {
            "derived_export": derived,
            "cain_read": readable,
            "cain_generate": False,
            "persistent_memory": False,
        },
    }
    if raw:
        item["raw_payload"] = {"forbidden": True}
    payload = {
        "schema_version": "ExternalIntelligenceExportV1",
        "dataset_snapshot_revision": "a" * 64,
        "evidence": [item],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", SOURCE], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "external fixture",
        ],
        check=True,
        capture_output=True,
    )
    return path


def test_external_bundle_is_separate_sanitized_stream(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    source = _source(root)
    bundle = export_external(
        root,
        digest(source.read_bytes()),
        tmp_path / "bundle",
        "2026-01-03T00:00:00Z",
    )
    validate(bundle)
    assert bundle["origin"]["stream"] == "external-intelligence-shadow"
    assert bundle["restrictions"]["generate"] is False
    entity = next(item for item in bundle["entities"] if item["entity_type"] == "external_evidence")
    assert entity["payload"]["rights"]["generate"] is False
    assert entity["payload"]["rights"]["persistent_memory"] is False


def test_external_bundle_excludes_unknown_rights(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    source = _source(root, readable=False)
    bundle = export_external(
        root, digest(source.read_bytes()), tmp_path / "bundle", "2026-01-03T00:00:00Z"
    )
    assert not [item for item in bundle["entities"] if item["entity_type"] == "external_evidence"]
    assert "fixture-evidence" in bundle["coverage"]["excluded"]


def test_external_bundle_rejects_raw_payload(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    source = _source(root, raw=True)
    with pytest.raises(ValueError, match="Raw or sensitive"):
        export_external(
            root, digest(source.read_bytes()), tmp_path / "bundle", "2026-01-03T00:00:00Z"
        )
