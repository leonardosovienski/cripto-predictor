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
        "https://github.com/leonardosovienski/core-predictor/releases/download/v2.3.0/predictor_core-2.3.0-py3-none-any.whl",
        "sha256:e0d29eac348e2be4092dde1b629c101d54973b54b5d43014cdaee69e4e17b3b9",
    ),
    "predictor-ops": (
        "https://github.com/leonardosovienski/predictor-ops/releases/download/v3.1.0/predictor_ops-3.1.0-py3-none-any.whl",
        "sha256:490ece696f9173bbaa56c2c53a1ff6e5ffab1a7625fb00ac0a5f896c37081b37",
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

    assert importlib.metadata.version("predictor-core") == "2.3.0"
    assert importlib.metadata.version("predictor-ops") == "3.1.0"
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
