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
        "https://github.com/leonardosovienski/core-predictor/releases/download/v3.2.1/predictor_core-3.2.1-py3-none-any.whl",
        "sha256:10ef42f34ace8bb2df5f83ff7de2ceec79b035a25ea0a690e8942bd60d2fb4e3",
    ),
    "predictor-ops": (
        "https://github.com/leonardosovienski/predictor-ops/releases/download/v4.2.0/predictor_ops-4.2.0-py3-none-any.whl",
        "sha256:a6108ee1c6fe9c14752766a435109f9b6bcf98102ee178330512efbcac984000",
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

    assert importlib.metadata.version("predictor-core") == "3.2.1"
    assert importlib.metadata.version("predictor-ops") == "4.2.0"
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
