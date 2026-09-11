"""Exporter-only tests: synthetic sources, no predictor test collection/imports."""

import json
import socket
import sys
from pathlib import Path

import pytest
from crypto_research_export import export
from research_snapshot import digest, loads, validate


def test_export_is_deterministic_and_side_effect_free(fixture, monkeypatch):
    root, admission, destination = fixture
    before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("Network forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    result = export(root, admission, destination, "2026-09-11T00:00:00Z")
    assert result["records"] == 2
    package = validate(loads(destination.read_bytes()))
    assert package["records"][0]["source_status"] == "CLOSED_INSUFFICIENT_SAMPLE"
    assert package["records"][0]["mapping"] is None
    assert before == {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    second = destination.with_name("second.json")
    export(root, admission, second, "2026-09-11T00:00:00Z")
    assert destination.read_bytes() == second.read_bytes()
    assert not any(
        name.startswith(("GarimpoInvestimentos", "predictor_core", "predictor_ops"))
        for name in sys.modules
    )


def test_changed_source_refused(fixture):
    root, admission, destination = fixture
    (root / "charters/scientific_state.json").write_text("{}")
    with pytest.raises(ValueError):
        export(root, admission, destination, "2026-09-11T00:00:00Z")
    assert not destination.exists()


@pytest.mark.parametrize(
    "name", ["../secret", "holdout.csv", "feature_store.db", "C:/private", "docs/HYPOTHESES.md"]
)
def test_unadmitted_source_never_read(fixture, monkeypatch, name):
    root, admission, destination = fixture
    admission["sources"] = {name: "0" * 64}

    def denied(*args, **kwargs):
        raise AssertionError("Forbidden source read")

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(ValueError):
        export(root, admission, destination, "2026-09-11T00:00:00Z")


def test_same_destination_never_overwritten(fixture):
    root, admission, destination = fixture
    destination.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        export(root, admission, destination, "2026-09-11T00:00:00Z")
    assert destination.read_bytes() == b"preserve"
    with pytest.raises(ValueError):
        export(root, admission, root / "new.json", "2026-09-11T00:00:00Z")


def test_exact_unicode_offsets_for_claims(fixture):
    root, admission, destination = fixture
    text = (
        "# Relatório\n\n## CLAIM-CR-TEST\n- **state:** INCONCLUSIVE\nLimitação: amostra pequena.\n"
    )
    (root / "docs").mkdir()
    (root / "docs/EVIDENCE_REGISTRY.md").write_bytes(text.encode())
    admission["sources"] = {"docs/EVIDENCE_REGISTRY.md": digest(text.encode())}
    export(root, admission, destination, "2026-09-11T00:00:00Z")
    evidence = json.loads(destination.read_bytes())["evidence"][0]
    assert text[evidence["start"] : evidence["end"]] == evidence["text"]


def test_source_changes_during_export_refused(fixture, monkeypatch):
    root, admission, destination = fixture
    original = Path.open
    calls = 0

    def changed(path, *args, **kwargs):
        nonlocal calls
        if path.name == "scientific_state.json":
            calls += 1
            if calls == 2:
                with original(path, "wb") as handle:
                    handle.write(b"{}")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", changed)
    with pytest.raises(ValueError, match="changed"):
        export(root, admission, destination, "2026-09-11T00:00:00Z")
    assert not destination.exists()
