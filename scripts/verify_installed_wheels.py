from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

# Published 3.2.1 / 4.2.2rc1 assets, registered by sha256 in STACK_WHEELS.json (R01, 2026-10-07): the lock
# pins them to the local flat index .stack-wheels by name + version; no release URL lives in the lock.
EXPECTED = {
    "predictor-core": ("3.2.1", "10ef42f34ace8bb2df5f83ff7de2ceec79b035a25ea0a690e8942bd60d2fb4e3"),
    "predictor-ops": (
        "4.2.2rc1",
        "0be70bfbb2437dfb080baceb9af41043a09d03b15a358903b8bd7007f5f169b3",
    ),
}
# Stage A (qualificação): o domínio não depende de envelope; o protocolo V1 saiu do lock.
ABSENT = ("predictor-research-protocol", "cain-research")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    # predictor-core/predictor-ops are consumed from their published GitHub
    # Release through STACK_WHEELS.json (registry: repository, tag, asset, sha256)
    # and the flat index [[tool.uv.index]] .stack-wheels in pyproject.toml, not
    # vendored locally; the portable sources of truth are the registry and the lock.
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    packages = {pkg["name"]: pkg for pkg in lock["package"]}
    registry = json.loads((root / "STACK_WHEELS.json").read_text(encoding="utf-8"))
    registered = {entry["package"]: entry for entry in registry["wheels"]}
    for name, (version, digest) in EXPECTED.items():
        assert registered[name]["version"] == version
        assert registered[name]["sha256"] == digest
        package = packages[name]
        assert package["version"] == version
        assert package["source"] == {"registry": ".stack-wheels"}
        assert [wheel["path"] for wheel in package["wheels"]] == [registered[name]["asset"]]
        assert "url" not in package["source"]
    for name in ABSENT:
        assert name not in packages, f"{name} must not be locked in stage A"
    import predictor_core
    import predictor_ops

    assert importlib.metadata.version("predictor-core") == "3.2.1"
    assert importlib.metadata.version("predictor-ops") == "4.2.2rc1"
    for module in (predictor_core, predictor_ops):
        assert module.__file__ is not None
        assert "site-packages" in Path(module.__file__).resolve().as_posix().lower()
    entrypoint = next(
        item
        for item in importlib.metadata.entry_points(group="predictor.plugins")
        if item.name == "cripto"
    )
    with tempfile.TemporaryDirectory() as directory:
        env = os.environ | {"DATA_DIR": directory, "OUTPUT_DIR": str(Path(directory) / "output")}
        executable = Path(sys.executable).parent / (
            "cripto-predictor.exe" if os.name == "nt" else "cripto-predictor"
        )
        result = subprocess.run(
            [str(executable), "--help"],
            cwd=directory,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        assert "usage: cripto-predictor" in result.stdout
        research = subprocess.run(
            [
                str(
                    Path(sys.executable).parent
                    / ("cripto-research.exe" if os.name == "nt" else "cripto-research")
                ),
                "--help",
            ],
            cwd=directory,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        assert "usage: cripto-research" in research.stdout
        assert entrypoint.load().health().status in {
            "SUCCEEDED",
            "DEGRADED",
            "WAITING",
            "SOURCE_UNAVAILABLE",
        }
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
