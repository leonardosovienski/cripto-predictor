"""Published source evidence must match its original byte-level manifest."""

import hashlib
import json
from pathlib import Path


def test_dependency_execution_evidence_preserves_original_bytes():
    evidence = Path(__file__).resolve().parents[1] / "docs/evidence/dependency_execution_20260910"
    files = json.loads((evidence / "manifest.json").read_bytes())["files"]
    assert files
    for name, expected in files.items():
        path = (evidence / name).resolve()
        assert path.is_relative_to(evidence.resolve()), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
