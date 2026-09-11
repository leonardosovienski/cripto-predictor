import pytest
from research_snapshot import canonical, digest


@pytest.fixture
def fixture(tmp_path):
    root = tmp_path / "source"
    (root / "charters").mkdir(parents=True)
    content = canonical(
        {
            "schema_version": "crypto-scientific-state/1",
            "hypotheses": {"H6": "CLOSED_INSUFFICIENT_SAMPLE", "H7": "REGISTERED_NOT_ACTIVATED"},
        }
    )
    (root / "charters/scientific_state.json").write_bytes(content)
    admission = {
        "policy": "crypto-frozen-reports-local/1",
        "read": True,
        "sources": {"charters/scientific_state.json": digest(content)},
        "code_revision": "fixture-only",
        "exporter_revision": "fixture-only",
    }
    return root, admission, tmp_path / "publication.json"
