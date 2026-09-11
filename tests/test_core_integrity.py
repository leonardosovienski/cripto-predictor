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
        "https://github.com/leonardosovienski/core-predictor/releases/download/v3.2.1/predictor_core-3.2.1-py3-none-any.whl",
        "sha256:10ef42f34ace8bb2df5f83ff7de2ceec79b035a25ea0a690e8942bd60d2fb4e3",
    ),
    "predictor-ops": (
        "https://github.com/leonardosovienski/predictor-ops/releases/download/v4.2.0/predictor_ops-4.2.0-py3-none-any.whl",
        "sha256:a6108ee1c6fe9c14752766a435109f9b6bcf98102ee178330512efbcac984000",
    ),
}


def test_shared_versions_are_exactly_compatible():
    assert importlib.metadata.version("predictor-core") == "3.2.1"
    assert importlib.metadata.version("predictor-ops") == "4.2.0"


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
    assert {path.name for path in (ROOT / "packages").iterdir() if path.is_dir()} == {"research-export"}
    export = tomllib.loads((ROOT / "packages/research-export/pyproject.toml").read_text())
    assert export["project"]["name"] == "crypto-research-export"
    assert not list((ROOT / "packages").rglob("predictor_core"))
    assert not list((ROOT / "packages").rglob("predictor_ops"))
