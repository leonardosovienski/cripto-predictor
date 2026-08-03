from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

EXPECTED = {
    "predictor-core": (
        "https://github.com/leonardosovienski/core-predictor/releases/download/v2.1.0/predictor_core-2.1.0-py3-none-any.whl",
        "sha256:83de1d4415700dedaf387bc46dd9685e046de1fa47f37367bf2167462b09761b",
    ),
    "predictor-ops": (
        "https://github.com/leonardosovienski/tools-predictor/releases/download/v2.0.1/predictor_ops-2.0.1-py3-none-any.whl",
        "sha256:77ca2eb3f1090226dfef23b84d7fb2f9a61bd858c970d433d28303e637a8903e",
    ),
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    # predictor-core/predictor-ops are consumed from their published GitHub
    # Release (see [tool.uv.sources] in pyproject.toml), not vendored locally,
    # so the portable source of truth is the lockfile itself.
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    packages = {pkg["name"]: pkg for pkg in lock["package"]}
    for name, (url, digest) in EXPECTED.items():
        wheel = packages[name]["wheels"][0]
        assert wheel["url"] == url
        assert wheel["hash"] == digest
    import predictor_core
    import predictor_ops

    assert importlib.metadata.version("predictor-core") == "2.1.0"
    assert importlib.metadata.version("predictor-ops") == "2.0.1"
    for module in (predictor_core, predictor_ops):
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
        assert entrypoint.load().health().status in {
            "SUCCEEDED",
            "DEGRADED",
            "WAITING",
            "SOURCE_UNAVAILABLE",
        }
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
