from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts.research_migration import export, restore, safe_path, validate


def snapshot(tmp_path: Path) -> Path:
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("experiment.py", b"# frozen\r\nx = 1\r\n")
        archive.writestr("raw.json", b'{"negative_result":-1}\r\n')
    files = []
    for name, raw in {
        "observer/code.py": b"# original\r\nx = 2\r\n",
        "observer/ledger.jsonl": b'{"result":-1}\n',
        "mixed.zip": nested.getvalue(),
        "observer/.venv/runtime.py": b"# dependency",
    }.items():
        path = tmp_path / "original" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files.append({"path": name, "source": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps({"created_utc": "2026-09-08T00:00:00Z", "files": files}))
    return path


def test_split_preserves_code_bytes_and_nested_data_without_shipping_code(tmp_path):
    output, sources = tmp_path / "data.zip", tmp_path / "sources"
    result = export(snapshot(tmp_path), output, sources, [])
    assert result["source_paths_in_git"] == 2
    assert result["data_files"] == 2
    with zipfile.ZipFile(output) as archive:
        manifest = json.loads(archive.read("MANIFESTO.json"))
        assert all(not r["path"].endswith(".py") for r in manifest["files"])
        payloads = [archive.read(name) for name in archive.namelist() if name.startswith("dados/")]
        assert b"# frozen\r\nx = 1\r\n" not in payloads
    destination = tmp_path / "restored"
    restore(output, destination, sources)
    assert (destination / "observer/code.py").read_bytes() == b"# original\r\nx = 2\r\n"
    assert (
        destination / "mixed.zip.extraido/experiment.py"
    ).read_bytes() == b"# frozen\r\nx = 1\r\n"
    assert (
        destination / "mixed.zip.extraido/raw.json"
    ).read_bytes() == b'{"negative_result":-1}\r\n'
    assert not (destination / "observer/.venv").exists()
    with pytest.raises(ValueError, match="new directory"):
        restore(output, destination, sources)


def test_tampered_code_prevents_restoration_before_destination_creation(tmp_path):
    output, sources = tmp_path / "data.zip", tmp_path / "sources"
    export(snapshot(tmp_path), output, sources, [])
    next((sources / "objects").iterdir()).write_bytes(b"changed")
    with pytest.raises(ValueError, match="Corrupted Git source"):
        restore(output, tmp_path / "must-not-exist", sources)
    assert not (tmp_path / "must-not-exist").exists()


def test_tampered_data_rejected(tmp_path):
    output, sources = tmp_path / "data.zip", tmp_path / "sources"
    export(snapshot(tmp_path), output, sources, [])
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(output) as source, zipfile.ZipFile(altered, "w") as target:
        for name in source.namelist():
            target.writestr(name, b"corrupt" if name.startswith("dados/") else source.read(name))
    with pytest.raises(ValueError, match="Corrupted data"):
        validate(altered, sources)


@pytest.mark.parametrize(
    "path",
    ["../outside", "/absolute", "C:/outside", "a/../outside", "a\\..\\outside", "./relative"],
)
def test_invalid_paths_rejected(path):
    with pytest.raises(ValueError):
        safe_path(path)
