"""Separate research source snapshots in Git from a data-only migration archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import tarfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CODE_SUFFIXES = {
    ".py",
    ".pyi",
    ".ps1",
    ".bat",
    ".cmd",
    ".sh",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".rs",
    ".go",
    ".patch",
    ".diff",
}
BINARY_SUFFIXES = {
    ".bundle",
    ".whl",
    ".exe",
    ".dll",
    ".pyd",
    ".pyc",
    ".pyo",
    ".so",
    ".a",
    ".lib",
    ".001",
    ".002",
    ".7z",
}
CODE_NAMES = {"dockerfile", "makefile", "justfile"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe_path(name: str) -> str:
    if "\\" in name:
        raise ValueError("Archive paths must use forward slashes")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or any(p in {"..", "."} or ":" in p for p in name.split("/")):
        raise ValueError("Unsafe archive path: " + name)
    return path.as_posix()


def category(name: str) -> str:
    path = PurePosixPath(name)
    if any(part in {".venv", "__pycache__", "node_modules", ".git"} for part in path.parts):
        return "runtime_or_cache"
    if path.suffix.lower() in BINARY_SUFFIXES:
        return "binary_or_git_backup"
    if path.suffix.lower() in CODE_SUFFIXES or path.name.lower() in CODE_NAMES:
        return "source"
    if name.lower().endswith((".tar.gz", ".tgz", ".tar", ".zip")):
        return "container"
    return "data"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def export(snapshot: Path, output: Path, source_archive: Path, extras: list[Path]) -> dict:
    """Preserve exact source bytes in Git and every non-code archive member as data."""
    old = json.loads(snapshot.read_text(encoding="utf-8"))
    source_archive.mkdir(parents=True, exist_ok=True)
    blobs = source_archive / "objects"
    blobs.mkdir(exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    sources, data, omitted, containers = [], [], [], []
    written_data: set[str] = set()
    source_names: set[str] = set()
    data_names: set[str] = set()
    seen_containers: dict[str, str] = {}
    records = [
        {"path": row["path"], "source": row["source"], "expected": row["sha256"]}
        for row in old["files"]
    ]
    for path in extras:
        records.append(
            {"path": "ferramentas-migracao/" + path.name, "source": str(path), "expected": None}
        )
    manifest = {
        "version": 2,
        "created_utc": datetime.now(UTC).isoformat(),
        "original_snapshot_utc": old["created_utc"],
        "git_repository": "https://github.com/leonardosovienski/cripto-predictor",
        "source_index": (
            source_archive.relative_to(ROOT).as_posix()
            if source_archive.is_relative_to(ROOT)
            else source_archive.name
        )
        + "/sources.json",
        "files": data,
        "omitted": omitted,
        "expanded_containers": containers,
        "automation_transferred": False,
    }
    payload_path = snapshot.parent / "dados.zip"
    if output.resolve() == payload_path.resolve():
        raise ValueError("Export cannot overwrite its source snapshot")
    frozen_payload = zipfile.ZipFile(payload_path) if payload_path.exists() else nullcontext(None)
    with (
        frozen_payload as payload,
        zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive,
    ):

        def add(name: str, raw: bytes, depth: int = 0) -> None:
            name = safe_path(name)
            kind = category(name)
            sha = digest(raw)
            if kind in {"runtime_or_cache", "binary_or_git_backup"}:
                omitted.append({"path": name, "sha256": sha, "reason": kind})
            elif kind == "source":
                if name in source_names:
                    raise ValueError("Duplicate source path: " + name)
                source_names.add(name)
                suffix = PurePosixPath(name).suffix.lower() or ".source"
                blob = blobs / (sha + suffix)
                if not blob.exists():
                    blob.write_bytes(raw)
                elif digest(blob.read_bytes()) != sha:
                    raise ValueError("Conflicting archived source: " + str(blob))
                sources.append(
                    {
                        "path": name,
                        "sha256": sha,
                        "size": len(raw),
                        "object": "objects/" + blob.name,
                    }
                )
            elif kind == "container":
                if depth >= 10:
                    raise ValueError("Archive nesting exceeds export limit")
                if sha in seen_containers:
                    containers.append(
                        {"path": name, "sha256": sha, "same_contents_as": seen_containers[sha]}
                    )
                    return
                seen_containers[sha] = name
                containers.append({"path": name, "sha256": sha, "expanded_to": name + ".extraido"})
                if name.lower().endswith(".zip"):
                    with zipfile.ZipFile(io.BytesIO(raw)) as nested:
                        for item in nested.infolist():
                            if not item.is_dir():
                                add(
                                    name + ".extraido/" + safe_path(item.filename),
                                    nested.read(item),
                                    depth + 1,
                                )
                else:
                    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as nested:
                        for item in nested:
                            if item.isfile():
                                stream = nested.extractfile(item)
                                if stream is None:
                                    raise ValueError("Missing tar member")
                                add(
                                    name + ".extraido/" + safe_path(item.name),
                                    stream.read(),
                                    depth + 1,
                                )
                            elif not item.isdir():
                                raise ValueError("Non-regular tar member")
            else:
                if name in data_names:
                    raise ValueError("Duplicate data path: " + name)
                data_names.add(name)
                if sha not in written_data:
                    archive.writestr("dados/" + sha, raw)
                    written_data.add(sha)
                data.append({"path": name, "sha256": sha, "size": len(raw)})

        for i, row in enumerate(records, 1):
            name = row["path"]
            if category(name) in {"runtime_or_cache", "binary_or_git_backup"}:
                omitted.append({"path": name, "sha256": row["expected"], "reason": category(name)})
                continue
            raw = (
                payload.read("objetos/" + row["expected"])
                if payload is not None and row["expected"] is not None
                else Path(row["source"]).read_bytes()
            )
            if row["expected"] is not None and digest(raw) != row["expected"]:
                raise ValueError("Source changed since snapshot: " + row["source"])
            add(name, raw)
            if i % 10000 == 0:
                print(f"Classified {i}/{len(records)}", flush=True)
        index = {"version": 1, "created_utc": manifest["created_utc"], "files": sources}
        write_json(source_archive / "sources.json", index)
        manifest["source_index_sha256"] = digest((source_archive / "sources.json").read_bytes())
        manifest["logical_data_bytes"] = sum(row["size"] for row in data)
        archive.writestr(
            "MANIFESTO.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
    validate(output, source_archive)
    result = {
        "status": "PASS",
        "data_files": len(data),
        "source_paths_in_git": len(sources),
        "source_objects": len({r["object"] for r in sources}),
        "data_zip_bytes": output.stat().st_size,
        "logical_data_bytes": manifest["logical_data_bytes"],
        "unique_data_objects": len(written_data),
        "expanded_unique_containers": len(seen_containers),
    }
    write_json(output.with_suffix(".validation.json"), result)
    output.with_suffix(output.suffix + ".sha256").write_text(
        digest(output.read_bytes()) + "  " + output.name + "\n", encoding="ascii"
    )
    return result


def validate(data_zip: Path, source_archive: Path) -> tuple[dict, dict]:
    with zipfile.ZipFile(data_zip) as archive:
        manifest = json.loads(archive.read("MANIFESTO.json"))
        index_raw = (source_archive / "sources.json").read_bytes()
        if digest(index_raw) != manifest["source_index_sha256"]:
            raise ValueError("Git source index does not match the data snapshot")
        index = json.loads(index_raw)
        targets = set()
        for row in [*manifest["files"], *index["files"]]:
            name = safe_path(row["path"])
            if name.casefold() in targets:
                raise ValueError("Duplicate destination: " + name)
            targets.add(name.casefold())
        expected = {"MANIFESTO.json", *("dados/" + r["sha256"] for r in manifest["files"])}
        if set(archive.namelist()) != expected or len(archive.namelist()) != len(expected):
            raise ValueError("Unexpected or repeated files in data-only ZIP")
        checked = set()
        for row in manifest["files"]:
            if category(row["path"]) != "data":
                raise ValueError("Code or container in data-only manifest")
            if row["sha256"] not in checked:
                raw = archive.read("dados/" + row["sha256"])
                if digest(raw) != row["sha256"] or len(raw) != row["size"]:
                    raise ValueError("Corrupted data object")
                checked.add(row["sha256"])
        for row in index["files"]:
            obj = source_archive / safe_path(row["object"])
            if digest(obj.read_bytes()) != row["sha256"]:
                raise ValueError("Corrupted Git source object")
    return manifest, index


def restore(data_zip: Path, destination: Path, source_archive: Path) -> dict:
    if destination.exists():
        raise ValueError(
            "Destination must be a new directory; existing data will not be overwritten"
        )
    manifest, index = validate(data_zip, source_archive)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(data_zip) as archive:

        def copy_data(row: dict) -> None:
            target = destination / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open("dados/" + row["sha256"]) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            if digest(target.read_bytes()) != row["sha256"]:
                raise ValueError("Restored data hash mismatch")

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(copy_data, manifest["files"]))
        (destination / "MANIFESTO_DADOS.json").write_bytes(archive.read("MANIFESTO.json"))
    for row in index["files"]:
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_archive / row["object"], target)
        if digest(target.read_bytes()) != row["sha256"]:
            raise ValueError("Restored source hash mismatch")
    result = {
        "status": "PASS",
        "data_files": len(manifest["files"]),
        "source_files_from_git": len(index["files"]),
        "destination": str(destination),
        "runtime_installed": False,
        "automation_installed": False,
    }
    write_json(destination / "RESTAURACAO_DADOS.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["export", "validate", "restore"])
    parser.add_argument("--data-zip", required=True, type=Path)
    parser.add_argument(
        "--source-archive", type=Path, default=ROOT / "docs/source_archive_20260908"
    )
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--extra-source", action="append", type=Path, default=[])
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.mode == "export":
        if args.snapshot is None:
            parser.error("export requires --snapshot")
        result = export(args.snapshot, args.data_zip, args.source_archive, args.extra_source)
    elif args.mode == "restore":
        if args.destination is None:
            parser.error("restore requires --destination")
        result = restore(args.data_zip, args.destination, args.source_archive)
    else:
        manifest, index = validate(args.data_zip, args.source_archive)
        result = {
            "status": "PASS",
            "data_files": len(manifest["files"]),
            "source_files_in_git": len(index["files"]),
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
