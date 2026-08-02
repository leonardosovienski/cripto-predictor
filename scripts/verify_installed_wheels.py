from __future__ import annotations

import hashlib
import importlib.metadata
import os
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED = {
    "predictor_core-2.1.0-py3-none-any.whl": "83de1d4415700dedaf387bc46dd9685e046de1fa47f37367bf2167462b09761b",
    "predictor_ops-2.0.0-py3-none-any.whl": "8f7cf5373fa944c99ab355fbaaa3ba05e8d127efaafc723be95836dc79ec0d23",
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    for name, expected in EXPECTED.items():
        assert hashlib.sha256((root / "wheelhouse" / name).read_bytes()).hexdigest() == expected
    import predictor_core
    import predictor_ops

    assert importlib.metadata.version("predictor-core") == "2.1.0"
    assert importlib.metadata.version("predictor-ops") == "2.0.0"
    for module in (predictor_core, predictor_ops):
        assert "site-packages" in Path(module.__file__).resolve().as_posix().lower()
    entrypoint = next(
        item
        for item in importlib.metadata.entry_points(group="ecosystem_predictor.plugins")
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
