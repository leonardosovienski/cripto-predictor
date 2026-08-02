from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_payload_is_present_and_not_runtime_ignored():
    payload = list((ROOT / "GarimpoInvestimentos").rglob("*.py"))
    assert payload
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "GarimpoInvestimentos" not in ignore


def test_no_legacy_shared_source_directories():
    assert not (ROOT / "vendor").exists()
    assert not (ROOT / "packages").exists()
