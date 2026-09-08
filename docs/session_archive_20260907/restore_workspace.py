"""Verify preserved session files; optionally restore research data into a new directory."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path, PurePosixPath


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, help="New directory to create; omit to verify only"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    inventory = json.loads((root / "inventory.json").read_text(encoding="utf-8"))
    for name, record in inventory["files"].items():
        path = root / name
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != record["sha256"] or path.stat().st_size != record["bytes"]:
            raise ValueError(f"Archive file differs: {name}")
    archive_record = inventory["workspace_archive"]
    payload = b"".join((root / name).read_bytes() for name in archive_record["parts"])
    if hashlib.sha256(payload).hexdigest() != archive_record["sha256"]:
        raise ValueError("Reassembled workspace archive differs")
    destination = args.destination.resolve() if args.destination else None
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        index = json.loads(archive.read("WORKSPACE_FILES_SHA256.json"))
        if set(archive.namelist()) != set(index) | {"WORKSPACE_FILES_SHA256.json"}:
            raise ValueError("Unexpected or missing archive entries")
        if len(archive.namelist()) != len(index) + 1:
            raise ValueError("Duplicate archive entries")
        for name, record in index.items():
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
                raise ValueError(f"Invalid relative archive path: {name}")
            data = archive.read(name)
            if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise ValueError(f"Workspace file differs: {name}")
        if destination:
            destination.mkdir(parents=True, exist_ok=False)
            for name in index:
                target = destination.joinpath(*PurePosixPath(name).parts)
                if not target.resolve().is_relative_to(destination):
                    raise ValueError(f"Destination escapes restoration root: {name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(archive.read(name))
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "archived_files_verified": len(inventory["files"]),
                    "workspace_files_verified": len(index),
                    "restored_to": str(destination) if destination else None,
                    "automation_changed": False,
                    "public_requests": 0,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
