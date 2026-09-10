import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[1] / "docs/continuity_20260909"
spec = importlib.util.spec_from_file_location("continuity_restore", PACK / "restore_archives.py")
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


def archive(root, name, members):
    path = root / name
    with zipfile.ZipFile(path, "w") as z:
        for member, data in members.items():
            z.writestr(member, data)
    return {
        "file": name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "entries": [
            {"path": member, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for member, data in members.items()
        ],
    }


@pytest.mark.parametrize(
    "path",
    [
        "operacao/dados/api_guard_budget.db",
        "operacao/dados/api_guard_budget.db-wal",
        "operacao/dados/api_guard_budget.db-shm",
        "operacao/dados/another.db-journal",
        "configuracao/pipeline.env",
        "nested/.env",
    ],
)
def test_transient_state_and_credentials_rejected_before_recovery(tmp_path, path):
    item = archive(tmp_path, "data.zip", {"first.txt": b"public", path: b"synthetic"})
    output = tmp_path / "recovered"
    with pytest.raises(ValueError, match="Operational state"):
        restore.verify_archives(tmp_path, [item], output)
    assert not output.exists()


@pytest.mark.parametrize(
    "path",
    ["../escape", "a/../escape", "a\\escape", "C:/escape", "CON", "a/../b", "a//b", "a./b", "a/ "],
)
def test_unsafe_and_windows_ambiguous_paths_rejected(tmp_path, path):
    item = archive(tmp_path, "data.zip", {path: b"public"})
    with pytest.raises(ValueError, match="unsafe path"):
        restore.verify_archives(tmp_path, [item], tmp_path / "out")


@pytest.mark.parametrize("other_path", ["same.txt", "SAME.txt"])
def test_conflicting_archives_rejected_before_writes(tmp_path, other_path):
    first = archive(tmp_path, "a.zip", {"same.txt": b"original"})
    second = archive(tmp_path, "b.zip", {other_path: b"different"})
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="Conflicting or ambiguous"):
        restore.verify_archives(tmp_path, [first, second], output)
    assert not output.exists()


def test_existing_parent_file_and_internal_parent_collision_are_preflight_errors(tmp_path):
    first = archive(tmp_path, "a.zip", {"a/b.txt": b"original"})
    out = tmp_path / "out"
    out.mkdir()
    (out / "a").write_bytes(b"owner")
    with pytest.raises(ValueError, match="parent is an existing file"):
        restore.verify_archives(tmp_path, [first], out)
    assert (out / "a").read_bytes() == b"owner"
    second = archive(tmp_path, "b.zip", {"a": b"parent", "a-other.txt": b"intervening name"})
    with pytest.raises(ValueError, match="also an archive directory"):
        restore.verify_archives(tmp_path, [first, second], tmp_path / "fresh")
    assert not (tmp_path / "fresh").exists()


def test_hash_tampering_and_existing_different_file_refused(tmp_path):
    item = archive(tmp_path, "data.zip", {"data.txt": b"original"})
    item["entries"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="member hash mismatch"):
        restore.verify_archives(tmp_path, [item])
    item["entries"][0]["sha256"] = hashlib.sha256(b"original").hexdigest()
    out = tmp_path / "out"
    out.mkdir()
    (out / "data.txt").write_bytes(b"owner")
    with pytest.raises(ValueError, match="different existing file"):
        restore.verify_archives(tmp_path, [item], out)
    assert (out / "data.txt").read_bytes() == b"owner"


def test_identical_existing_files_and_duplicate_content_are_valid(tmp_path):
    first = archive(tmp_path, "a.zip", {"same.txt": b"original"})
    second = archive(tmp_path, "b.zip", {"same.txt": b"original"})
    out = tmp_path / "out"
    out.mkdir()
    (out / "same.txt").write_bytes(b"original")
    assert restore.verify_archives(tmp_path, [first, second], out) == 2
    assert (out / "same.txt").read_bytes() == b"original"


def test_published_archives_match_manifest_and_exclude_runtime_state():
    manifest = json.loads((PACK / "MANIFEST.json").read_text(encoding="utf-8"))
    assert restore.verify_archives(PACK, manifest["archives"]) == sum(
        len(a["entries"]) for a in manifest["archives"]
    )
