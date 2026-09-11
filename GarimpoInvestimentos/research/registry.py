"""Immutable completed research runs; distinct from scientific trials/charters."""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from GarimpoInvestimentos.durable_io import atomic_write, strict_json_loads
from GarimpoInvestimentos.local_runtime import local_root, within_root


def encoded(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    ).encode()


class RunStore:
    def __init__(self, root: str | Path):
        configured = local_root()
        self.root = within_root(configured, root) if configured else Path(root).resolve()

    def create(
        self,
        config: dict,
        metrics: dict,
        *,
        artifacts: dict[str, object],
        inputs: dict[str, str],
        code_version: str,
        run_id: str | None = None,
    ) -> Path:
        ident = run_id or uuid4().hex
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", ident) or not code_version:
            raise ValueError("Invalid run identity/version")
        if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", k) for k in artifacts):
            raise ValueError("Artifact names must be simple identifiers")
        if any(not re.fullmatch(r"[a-f0-9]{64}", v) for v in inputs.values()):
            raise ValueError("Input SHA-256 required")
        files = {"config.json": encoded(config), "metrics.json": encoded(metrics)}
        files.update({name + ".json": encoded(value) for name, value in artifacts.items()})
        if len(files) != len(artifacts) + 2 or "manifest" in artifacts:
            raise ValueError("Reserved artifact name")
        manifest = {
            "schema": 1,
            "run_id": ident,
            "created_at": datetime.now(UTC).isoformat(),
            "code_version": code_version,
            "inputs": inputs,
            "economic_validation": False,
            "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
        }
        path = self.root / ident
        path.mkdir(parents=True, exist_ok=False)
        # Manifest is the commit marker. Interrupted runs without it are not completed runs.
        for name, raw in files.items():
            atomic_write(path / name, raw)
        atomic_write(path / "manifest.json", encoded(manifest))
        return path

    def verify(self, run_id: str) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
            raise ValueError("Invalid run ID")
        path = (self.root / run_id).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Run escapes registry")
        manifest = strict_json_loads((path / "manifest.json").read_text(encoding="utf-8"))
        if (
            not isinstance(manifest, dict)
            or manifest.get("run_id") != run_id
            or manifest.get("schema") != 1
        ):
            raise ValueError("Invalid manifest")
        if (
            not isinstance(manifest.get("files"), dict)
            or not {"config.json", "metrics.json"} <= manifest["files"].keys()
        ):
            raise ValueError("Missing required run artifacts")
        for name, expected in manifest["files"].items():
            if (
                not re.fullmatch(r"[A-Za-z0-9_-]+\.json", name)
                or not isinstance(expected, str)
                or not re.fullmatch(r"[a-f0-9]{64}", expected)
            ):
                raise ValueError("Invalid artifact path")
            target = (path / name).resolve()
            if (
                not target.is_relative_to(path)
                or hashlib.sha256(target.read_bytes()).hexdigest() != expected
            ):
                raise ValueError("Artifact hash mismatch")
        return manifest

    def list_runs(self) -> list[dict]:
        if not self.root.exists():
            return []
        return [
            self.verify(p.name)
            for p in sorted(self.root.iterdir())
            if p.is_dir() and (p / "manifest.json").is_file()
        ]

    def compare(self, left: str, right: str) -> dict:
        self.verify(left)
        self.verify(right)
        a = strict_json_loads((self.root / left / "metrics.json").read_text(encoding="utf-8"))
        b = strict_json_loads((self.root / right / "metrics.json").read_text(encoding="utf-8"))
        if not isinstance(a, dict) or not isinstance(b, dict):
            raise ValueError("Metrics must be objects")
        return {k: {"left": a.get(k), "right": b.get(k)} for k in sorted(a.keys() | b.keys())}
