"""Installed-wheel contract for shared libraries."""

import importlib.metadata
import json
import tomllib
from pathlib import Path

import predictor_core
import predictor_ops

ROOT = Path(__file__).resolve().parents[1]
# predictor-core/predictor-ops are consumed from their published GitHub
# Release through STACK_WHEELS.json (repository, tag, asset, sha256) and the
# flat index .stack-wheels (never committed; `scripts/stack_wheels.py fetch`),
# not from a wheel vendored in this repo. The git-visible sources of truth are
# the registry and the lockfile, which pins by name + version to that index:
# no repository name or URL lives in the lock (R01, 2026-10-07).
EXPECTED = {
    "predictor-core": (
        "3.2.1",
        "predictor_core-3.2.1-py3-none-any.whl",
        "10ef42f34ace8bb2df5f83ff7de2ceec79b035a25ea0a690e8942bd60d2fb4e3",
    ),
    "predictor-ops": (
        "4.2.2rc1",
        "predictor_ops-4.2.2rc1-py3-none-any.whl",
        "0be70bfbb2437dfb080baceb9af41043a09d03b15a358903b8bd7007f5f169b3",
    ),
}


def test_shared_versions_are_exactly_compatible():
    assert importlib.metadata.version("predictor-core") == "3.2.1"
    assert importlib.metadata.version("predictor-ops") == "4.2.2rc1"


def test_shared_libraries_resolve_from_site_packages():
    for module in (predictor_core, predictor_ops):
        location = Path(module.__file__).resolve().as_posix().lower()
        assert "site-packages" in location
        assert "/vendor/" not in location and "/packages/" not in location


def test_registry_and_lock_pin_the_published_wheels():
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = {pkg["name"]: pkg for pkg in lock["package"]}
    registry = json.loads((ROOT / "STACK_WHEELS.json").read_text(encoding="utf-8"))
    registered = {entry["package"]: entry for entry in registry["wheels"]}
    assert set(registered) == set(EXPECTED)
    for name, (version, asset, digest) in EXPECTED.items():
        assert registered[name]["version"] == version
        assert registered[name]["asset"] == asset
        assert registered[name]["sha256"] == digest
        assert registered[name]["repository"] in {
            "leonardosovienski/core-predictor",
            "leonardosovienski/predictor-ops",
        }
        package = packages[name]
        assert package["version"] == version
        assert package["source"] == {"registry": ".stack-wheels"}
        assert [wheel["path"] for wheel in package["wheels"]] == [asset]
    assert "releases/download" not in (ROOT / "uv.lock").read_text(encoding="utf-8")


def test_no_shared_source_copy_exists():
    assert not (ROOT / "vendor").exists()
    assert {path.name for path in (ROOT / "packages").iterdir() if path.is_dir()} == {
        "research-export"
    }
    export = tomllib.loads((ROOT / "packages/research-export/pyproject.toml").read_text())
    assert export["project"]["name"] == "crypto-research-export"
    assert not list((ROOT / "packages").rglob("predictor_core"))
    assert not list((ROOT / "packages").rglob("predictor_ops"))
