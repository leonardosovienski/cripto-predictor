"""Consistent, non-overwriting backup/restore for research integration state."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def _hash(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _sqlite_snapshot(source: Path, target: Path) -> None:
    source_db = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    target_db = sqlite3.connect(target)
    try:
        source_db.backup(target_db)
        if target_db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("backup SQLite integrity check failed")
    finally:
        target_db.close()
        source_db.close()


def create_recovery_bundle(
    destination: str | Path,
    *,
    sqlite_databases: dict[str, str | Path],
    artifact_roots: dict[str, str | Path],
) -> dict:
    """Create an atomic immutable bundle without modifying any source state."""
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        files = []
        for name, raw_path in sorted(sqlite_databases.items()):
            source = Path(raw_path).resolve(strict=True)
            if not source.is_file():
                raise ValueError("SQLite backup source must be a file")
            target = staging / "sqlite" / f"{name}.sqlite"
            target.parent.mkdir(parents=True, exist_ok=True)
            _sqlite_snapshot(source, target)
            files.append({"role": "sqlite", "name": name, "path": target.relative_to(staging).as_posix()})
        for name, raw_root in sorted(artifact_roots.items()):
            source_root = Path(raw_root).resolve(strict=True)
            if not source_root.is_dir():
                raise ValueError("artifact backup source must be a directory")
            for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
                if source.is_symlink() or getattr(source, "is_junction", lambda: False)():
                    raise PermissionError("recovery source contains link/reparse point")
                relative = source.relative_to(source_root)
                target = staging / "artifacts" / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                files.append({
                    "role": "artifact", "name": name,
                    "path": target.relative_to(staging).as_posix(),
                })
        for item in files:
            path = staging / item["path"]
            item["size"] = path.stat().st_size
            item["sha256"] = _hash(path)
        manifest = {
            "schema_version": "ResearchRecoveryBundleV1",
            "created_at": datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "source_mutated": False,
            "restore_policy": "EMPTY_DESTINATION_ONLY",
            "files": files,
        }
        manifest_path = staging / "manifest.json"
        encoded_manifest = json.dumps(
            manifest, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        with manifest_path.open("wb") as handle:
            handle.write(encoded_manifest)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return verify_recovery_bundle(destination)


def verify_recovery_bundle(bundle: str | Path) -> dict:
    bundle = Path(bundle).resolve(strict=True)
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "ResearchRecoveryBundleV1":
        raise ValueError("unsupported recovery bundle")
    for item in manifest.get("files", []):
        path = (bundle / item["path"]).resolve(strict=True)
        if not path.is_relative_to(bundle) or path.is_symlink():
            raise PermissionError("recovery bundle path escapes root")
        if path.stat().st_size != item["size"] or _hash(path) != item["sha256"]:
            raise ValueError("recovery bundle hash mismatch")
        if item["role"] == "sqlite":
            db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
            try:
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("recovery SQLite integrity check failed")
            finally:
                db.close()
    return manifest


def restore_recovery_bundle(bundle: str | Path, destination: str | Path) -> dict:
    """Restore into a new directory; canonical/current history is never overwritten."""
    bundle = Path(bundle).resolve(strict=True)
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("restore destination must be empty")
    manifest = verify_recovery_bundle(bundle)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        shutil.copyfile(bundle / "manifest.json", staging / "manifest.json")
        for item in manifest["files"]:
            source = bundle / item["path"]
            target = staging / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if destination.exists():
            destination.rmdir()
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    restored = verify_recovery_bundle(destination)
    return {"status": "RESTORED_TO_NEW_ROOT", "files": len(restored["files"])}


__all__ = ["create_recovery_bundle", "restore_recovery_bundle", "verify_recovery_bundle"]
