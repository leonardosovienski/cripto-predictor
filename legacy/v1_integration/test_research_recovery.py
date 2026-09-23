import hashlib

import pytest

from GarimpoInvestimentos.research_recovery import (
    create_recovery_bundle,
    restore_recovery_bundle,
    verify_recovery_bundle,
)
from legacy.v1_integration.test_research_execution import setup_stack


def tree_hash(root):
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_backup_restore_preserves_scientific_history_and_never_overwrites(tmp_path):
    executor, admission, outbox, _ = setup_stack(tmp_path / "live")
    completed = executor.execute("TASK-E2E-001")
    live = tmp_path / "live"
    before = tree_hash(live)
    bundle = tmp_path / "recovery-bundle"
    manifest = create_recovery_bundle(
        bundle,
        sqlite_databases={
            "admission": admission.path,
            "result-outbox": outbox.path,
            "experiment-journal": executor.journal.path,
        },
        artifact_roots={"execution": executor.root / "experiments"},
    )
    assert manifest["source_mutated"] is False
    assert tree_hash(live) == before

    restored = tmp_path / "restored"
    assert restore_recovery_bundle(bundle, restored)["status"] == "RESTORED_TO_NEW_ROOT"
    assert verify_recovery_bundle(restored)["files"] == manifest["files"]
    assert completed["result"]["result_id"] in "".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in restored.rglob("*")
        if path.is_file()
    )

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "history.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError, match="empty"):
        restore_recovery_bundle(bundle, occupied)
    assert (occupied / "history.txt").read_text(encoding="utf-8") == "preserve"


def test_corrupt_recovery_bundle_fails_closed(tmp_path):
    executor, admission, outbox, _ = setup_stack(tmp_path / "live")
    executor.execute("TASK-E2E-001")
    bundle = tmp_path / "bundle"
    create_recovery_bundle(
        bundle,
        sqlite_databases={"admission": admission.path, "result": outbox.path},
        artifact_roots={"execution": executor.root / "experiments"},
    )
    target = next(path for path in (bundle / "artifacts").rglob("*") if path.is_file())
    target.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_recovery_bundle(bundle)
