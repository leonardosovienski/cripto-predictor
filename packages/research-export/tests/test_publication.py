import os

import pytest

from crypto_research_export import export
from test_export import fixture  # noqa: F401


def test_retry_recovers_the_same_receipt(fixture):
    root, admission, destination = fixture
    first = export(root, admission, destination, "2026-09-11T00:00:00Z")
    second = export(root, admission, destination, "2026-09-11T00:00:00Z")
    assert first == second
    assert not list(destination.parent.glob(".snapshot-*"))


def test_interrupted_publication_exposes_no_partial_file(fixture, monkeypatch):
    root, admission, destination = fixture

    def interrupted(*args):
        assert not destination.exists()
        raise OSError("synthetic interruption before commit")

    monkeypatch.setattr(os, "link", interrupted)
    with pytest.raises(OSError):
        export(root, admission, destination, "2026-09-11T00:00:00Z")
    assert not destination.exists()
    assert not list(destination.parent.glob(".snapshot-*"))
