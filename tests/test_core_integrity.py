"""Installed-wheel contract for shared libraries."""

import importlib.metadata
import tomllib
from pathlib import Path

import predictor_core
import predictor_ops

ROOT = Path(__file__).resolve().parents[1]
# predictor-core/predictor-ops are consumed from their published GitHub
# Release (see [tool.uv.sources] in pyproject.toml), not from a wheel
# vendored under wheelhouse/ in this repo (that path is never committed - a
# fresh clone never had these files). The portable, git-visible source of
# truth is the lockfile itself.
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


def test_shared_versions_are_exactly_compatible():
    assert importlib.metadata.version("predictor-core") == "2.1.0"
    assert importlib.metadata.version("predictor-ops") == "2.0.1"


def test_shared_libraries_resolve_from_site_packages():
    for module in (predictor_core, predictor_ops):
        location = Path(module.__file__).resolve().as_posix().lower()
        assert "site-packages" in location
        assert "/vendor/" not in location and "/packages/" not in location


def test_wheelhouse_hashes_are_pinned():
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = {pkg["name"]: pkg for pkg in lock["package"]}
    for name, (url, digest) in EXPECTED.items():
        wheel = packages[name]["wheels"][0]
        assert wheel["url"] == url
        assert wheel["hash"] == digest


def test_no_shared_source_copy_exists():
    assert not (ROOT / "vendor").exists()
    assert not (ROOT / "packages").exists()
