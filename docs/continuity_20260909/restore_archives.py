"""Verify and recover the published continuity archives without overwriting files."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_target(destination: Path, member: str) -> Path:
    name = PurePosixPath(member)
    if name.is_absolute() or ".." in name.parts or "\\" in member or ":" in member:
        raise ValueError("Archive member has an unsafe path")
    target = (destination / Path(*name.parts)).resolve()
    if not target.is_relative_to(destination):
        raise ValueError("Archive member escapes the recovery folder")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", action="append", default=[])
    args = parser.parse_args()
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
    count = 0
    # Validate every selected archive and every existing destination before writing.
    for archive in selected:
        path = safe_target(pack, archive["file"])
        if digest(path.read_bytes()) != archive["sha256"]:
            raise ValueError("Archive hash mismatch")
        entries = {e["path"]: e for e in archive["entries"]}
        with zipfile.ZipFile(path) as z:
            if len(z.infolist()) != len(entries) or set(z.namelist()) != set(entries):
                raise ValueError("Archive members differ from the manifest")
            for info in z.infolist():
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError("Archive links are not allowed")
                payload = z.read(info.filename)
                entry = entries[info.filename]
                if len(payload) != entry["bytes"] or digest(payload) != entry["sha256"]:
                    raise ValueError("Archive member hash mismatch")
                target = safe_target(destination or pack, info.filename)
                if (
                    destination
                    and target.exists()
                    and (not target.is_file() or target.read_bytes() != payload)
                ):
                    raise ValueError("Refusing to overwrite a different existing file")
                count += 1
    if destination:
        for archive in selected:
            with zipfile.ZipFile(pack / archive["file"]) as z:
                for info in z.infolist():
                    target = safe_target(destination, info.filename)
                    if target.exists():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target = safe_target(destination, info.filename)
                    with target.open("xb") as handle:
                        handle.write(z.read(info.filename))
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
