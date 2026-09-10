"""Verify and recover the published continuity archives without overwriting files."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stream_digest(handle) -> tuple[int, str]:
    size = 0
    value = hashlib.sha256()
    while chunk := handle.read(1024 * 1024):
        size += len(chunk)
        value.update(chunk)
    return size, value.hexdigest()


def excluded_operational_path(member: str) -> bool:
    """State and credentials are never recovery data, including SQLite sidecars."""
    name = PurePosixPath(member).name.casefold()
    parts = {part.casefold() for part in PurePosixPath(member).parts}
    return (
        name.startswith("api_guard_budget.db")
        or name.endswith(("-wal", "-shm", "-journal"))
        or name in {"pipeline.env", ".env"}
        or bool(parts & {".venv", ".git", "__pycache__"})
    )


def safe_target(destination: Path, member: str) -> Path:
    name = PurePosixPath(member)
    if (
        not name.parts
        or name.is_absolute()
        or ".." in name.parts
        or "\\" in member
        or ":" in member
        or name.as_posix() != member
        or any(part.endswith((" ", ".")) for part in name.parts)
        or any(
            part.split(".", 1)[0].casefold()
            in {
                "con",
                "prn",
                "aux",
                "nul",
                *(f"com{i}" for i in range(1, 10)),
                *(f"lpt{i}" for i in range(1, 10)),
            }
            or any(ord(char) < 32 for char in part)
            for part in name.parts
        )
    ):
        raise ValueError("Archive member has an unsafe path")
    target = (destination / Path(*name.parts)).resolve()
    if not target.is_relative_to(destination):
        raise ValueError("Archive member escapes the recovery folder")
    return target


def verify_archives(pack: Path, selected: list[dict], destination: Path | None = None) -> int:
    count = 0
    targets: dict[str, tuple[str, str]] = {}
    # Validate the complete selection before creating any recovery file.
    for archive in selected:
        path = safe_target(pack, archive["file"])
        with path.open("rb") as handle:
            size, checksum = stream_digest(handle)
        if checksum != archive["sha256"] or ("bytes" in archive and size != archive["bytes"]):
            raise ValueError("Archive hash or size mismatch")
        entries = {e["path"]: e for e in archive["entries"]}
        if len(entries) != len(archive["entries"]):
            raise ValueError("Duplicate manifest member")
        with zipfile.ZipFile(path) as z:
            if len(z.infolist()) != len(entries) or set(z.namelist()) != set(entries):
                raise ValueError("Archive members differ from the manifest")
            for info in z.infolist():
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError("Archive links are not allowed")
                if excluded_operational_path(info.filename):
                    raise ValueError("Operational state or credentials cannot be recovered")
                target = safe_target(destination or pack, info.filename)
                entry = entries[info.filename]
                identity = (info.filename, entry["sha256"])
                key = info.filename.casefold()
                if key in targets and targets[key] != identity:
                    raise ValueError("Conflicting or ambiguous paths across archives")
                targets[key] = identity
                with z.open(info) as handle:
                    actual = stream_digest(handle)
                if actual != (entry["bytes"], entry["sha256"]):
                    raise ValueError("Archive member hash mismatch")
                if destination:
                    for parent in target.parents:
                        if parent == destination.parent:
                            break
                        if parent.exists() and not parent.is_dir():
                            raise ValueError("Recovery parent is an existing file")
                    if target.exists():
                        if not target.is_file():
                            raise ValueError("Refusing to overwrite a different existing file")
                        with target.open("rb") as handle:
                            existing = stream_digest(handle)
                        if existing != actual:
                            raise ValueError("Refusing to overwrite a different existing file")
                count += 1
    if any(
        parent.as_posix() in targets for path in targets for parent in PurePosixPath(path).parents
    ):
        raise ValueError("Recovery file is also an archive directory")
    return count


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", action="append", default=[])
    args = parser.parse_args(argv)
    pack = Path(__file__).resolve().parent
    manifest = json.loads((pack / "MANIFEST.json").read_text(encoding="utf-8"))
    selected = [a for a in manifest["archives"] if not args.archive or a["file"] in args.archive]
    if args.archive and set(args.archive) != {a["file"] for a in selected}:
        raise ValueError("Unknown archive selection")
    destination = args.output.resolve() if args.output else None
    if destination is not None:
        root = Path(r"C:\Cripto").resolve()
        if destination == root or not destination.is_relative_to(root):
            raise ValueError("Use a new recovery subfolder inside C:\\Cripto")
    count = verify_archives(pack, selected, destination)
    if destination:
        for archive in selected:
            with zipfile.ZipFile(pack / archive["file"]) as z:
                for info in z.infolist():
                    target = safe_target(destination, info.filename)
                    if target.exists():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target = safe_target(destination, info.filename)
                    with z.open(info) as source, target.open("xb") as handle:
                        shutil.copyfileobj(source, handle, length=1024 * 1024)
    print(
        json.dumps(
            {
                "verified_archives": len(selected),
                "verified_files": count,
                "extracted": destination is not None,
                "output": str(destination) if destination else None,
            }
        )
    )


if __name__ == "__main__":
    main()
