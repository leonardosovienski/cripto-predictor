"""Bind pip download URLs to the lock and exercise rejection before install."""

import hashlib
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
    r'https://github\.com/leonardosovienski/(?:core-predictor|predictor-ops)/'
    r'releases/download/[^"\s\\]+'
)


@pytest.mark.parametrize("relative", ["Dockerfile", ".github/workflows/ci.yml"])
def test_install_paths_require_the_existing_locked_digests(relative):
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = {item["name"]: item for item in lock["package"]}
    expected = set()
    for name in ("predictor-core", "predictor-ops"):
        wheel = packages[name]["wheels"][0]
        algorithm, digest = wheel["hash"].split(":", 1)
        assert algorithm == "sha256" and re.fullmatch(r"[0-9a-f]{64}", digest)
        expected.add(wheel["url"] + "#sha256=" + digest)
    urls = SHARED_URL.findall((ROOT / relative).read_text(encoding="utf-8"))
    assert len(urls) == 2
    assert set(urls) == expected


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
