"""Installed-wheel contract for shared libraries."""

import hashlib
import importlib.metadata
from pathlib import Path

import predictor_core
import predictor_ops

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "predictor_core-2.1.0-py3-none-any.whl": "83de1d4415700dedaf387bc46dd9685e046de1fa47f37367bf2167462b09761b",
    "predictor_ops-2.0.0-py3-none-any.whl": "8f7cf5373fa944c99ab355fbaaa3ba05e8d127efaafc723be95836dc79ec0d23",
}


def test_shared_versions_are_exactly_compatible():
    assert importlib.metadata.version("predictor-core") == "2.1.0"
    assert importlib.metadata.version("predictor-ops") == "2.0.0"


def test_shared_libraries_resolve_from_site_packages():
    for module in (predictor_core, predictor_ops):
        location = Path(module.__file__).resolve().as_posix().lower()
        assert "site-packages" in location
        assert "/vendor/" not in location and "/packages/" not in location


def test_wheelhouse_hashes_are_pinned():
    for name, expected in EXPECTED.items():
        payload = (ROOT / "wheelhouse" / name).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == expected


def test_no_shared_source_copy_exists():
    assert not (ROOT / "vendor").exists()
    assert not (ROOT / "packages").exists()
