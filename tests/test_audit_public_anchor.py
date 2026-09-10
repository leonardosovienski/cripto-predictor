"""Published anchors must survive invalid local ledgers and malformed state."""

import json

import pytest

from GarimpoInvestimentos import quality_snapshot
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.hash_chain import seal_chain, verify_chain


@pytest.mark.parametrize(
    "prior",
    [
        b"{broken",
        b"null",
        json.dumps({"schema": 1, "entries": 1, "head_archive_id": 7, "head": "a" * 64}).encode(),
    ],
)
def test_bad_public_anchor_is_preserved_and_blocks_status(tmp_path, monkeypatch, prior):
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(prior)
    h6 = tmp_path / "h6.json"

    async def snapshot():
        return {}

    monkeypatch.setattr(quality_snapshot, "build_snapshot", snapshot)
    monkeypatch.setattr(quality_snapshot, "render", lambda _: "")
    monkeypatch.setattr(quality_snapshot, "append_history", lambda _: None)
    monkeypatch.setattr(quality_snapshot, "H6_STATUS_PATH", h6)
    assert (
        quality_snapshot.main(chain_manifest_path=manifest, feature_store_db=tmp_path / "db.sqlite")
        == 3
    )
    assert manifest.read_bytes() == prior
    assert not h6.exists()


def test_retroactive_unsealed_row_is_rejected_without_extending_chain(tmp_path):
    with FeatureStore(tmp_path / "db.sqlite") as store:
        conn = store._conn
        # Simulate a privileged insertion into a gap in a previously sealed ledger.
        conn.execute(
            "INSERT INTO predictions_archive (archive_id, change_type, ativo, ts, score, sentimento, resumo, price_usd, juiz, divergencia, fonte) VALUES (2, 'INSERT', 'bitcoin', '2026-09-01 00:00:00', 50, 'neutro', 'test', 100, 'test', 0, 'direct')"
        )
        conn.commit()
        seal_chain(conn)
        conn.execute(
            "INSERT INTO predictions_archive (archive_id, change_type, ativo, ts, score, sentimento, resumo, price_usd, juiz, divergencia, fonte) VALUES (1, 'INSERT', 'bitcoin', '2026-08-31 00:00:00', 50, 'neutro', 'test', 100, 'test', 0, 'direct')"
        )
        conn.commit()
        assert not verify_chain(conn).ok
        with pytest.raises(RuntimeError, match="selo recusado"):
            seal_chain(conn)
        assert conn.execute("SELECT COUNT(*) FROM predictions_archive_chain").fetchone()[0] == 1
