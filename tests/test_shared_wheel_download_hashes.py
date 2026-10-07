"""Bind the stack wheels to the registry and the lock, and exercise pip's digest rejection."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHARED_URL = re.compile(
    r"https://github\.com/leonardosovienski/"
    r"(?:core-predictor|predictor-ops|ecosystem-predictor(?:-cain)?)/"
    r'releases/download/[^"\s\\]+'
)


def test_lock_pins_stack_wheels_to_the_registry_index_by_sha256():
    # Since R01 (2026-10-07) the producers are private and one of them was renamed: the
    # lock carries no release URL; STACK_WHEELS.json carries repository, tag, asset and
    # sha256, and scripts/stack_wheels.py verifies the bytes before uv sees them.
    lock_text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert SHARED_URL.findall(lock_text) == []
    assert SHARED_URL.findall((ROOT / "pyproject.toml").read_text(encoding="utf-8")) == []
    lock = tomllib.loads(lock_text)
    packages = {item["name"]: item for item in lock["package"]}
    registry = json.loads((ROOT / "STACK_WHEELS.json").read_text(encoding="utf-8"))
    registered = {entry["package"]: entry for entry in registry["wheels"]}
    for name in ("predictor-core", "predictor-ops"):
        assert re.fullmatch(r"[0-9a-f]{64}", registered[name]["sha256"])
        assert packages[name]["version"] == registered[name]["version"]
        assert packages[name]["source"] == {"registry": ".stack-wheels"}
        (wheel,) = packages[name]["wheels"]
        assert wheel["path"] == registered[name]["asset"]
    # Stage A: the domain has no envelope dependency (prompt §8, D-13).
    assert "predictor-research-protocol" not in packages
    assert "cain-research" not in packages


@pytest.mark.parametrize("relative", ["Dockerfile", ".github/workflows/ci.yml"])
def test_install_paths_require_the_existing_locked_digests(relative):
    # Pip installs only requirements exported from uv.lock, with every digest
    # enforced; no stack wheel URL may be installed around the lock.
    text = (ROOT / relative).read_text(encoding="utf-8")
    assert "uv export --locked" in text
    assert "--require-hashes -r" in text
    assert SHARED_URL.findall(text) == []


@pytest.fixture(scope="module")
def pip_python(tmp_path_factory):
    env = tmp_path_factory.mktemp("offline-pip") / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(env)], check=True, timeout=60)
    return env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def write_inert_wheel(path, value):
    info = "digest_probe-0.0.0.dist-info"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("digest_probe/__init__.py", f"VALUE = {value!r}\n")
        archive.writestr(
            info + "/METADATA", "Metadata-Version: 2.1\nName: digest-probe\nVersion: 0.0.0\n"
        )
        archive.writestr(
            info + "/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr(info + "/RECORD", "")


def download(python, wheel, digest, destination):
    return subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "--isolated",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "download",
            "--no-index",
            "--no-deps",
            "--dest",
            str(destination),
            wheel.as_uri() + "#sha256=" + digest,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_pip_accepts_exact_bytes_and_rejects_same_version_replaced_bytes(tmp_path, pip_python):
    wheel = tmp_path / "digest_probe-0.0.0-py3-none-any.whl"
    write_inert_wheel(wheel, "original")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    accepted = tmp_path / "accepted"
    result = download(pip_python, wheel, digest, accepted)
    assert result.returncode == 0, result.stdout + result.stderr
    assert hashlib.sha256((accepted / wheel.name).read_bytes()).hexdigest() == digest
    write_inert_wheel(wheel, "replacement")
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() != digest
    rejected = tmp_path / "rejected"
    result = download(pip_python, wheel, digest, rejected)
    assert result.returncode != 0
    assert "hash" in (result.stdout + result.stderr).lower()
    assert not (rejected / wheel.name).exists()
