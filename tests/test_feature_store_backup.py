import json
import hashlib
from pathlib import Path
import sqlite3

import pytest

from scripts.feature_store_backup import (
    BackupError,
    SCHEMA_VERSION,
    create_backup,
    restore_backup,
    verify_backup,
)


def _database(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE candles (id INTEGER PRIMARY KEY, close REAL)")
    connection.execute("INSERT INTO candles VALUES (1, 101.5)")
    connection.commit()
    connection.close()
    return path


def test_backup_verify_restore_roundtrip(tmp_path):
    source = _database(tmp_path / "live" / "feature_store.db")
    backup = create_backup(tmp_path / "backup", database=source)
    manifest = verify_backup(backup)
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert not list(backup.glob("feature_store.db-*"))

    restored = restore_backup(backup, tmp_path / "restored")
    connection = sqlite3.connect(restored / "output" / "feature_store.db")
    try:
        assert connection.execute("SELECT * FROM candles").fetchall() == [(1, 101.5)]
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        connection.close()


def test_backup_rejeita_tamper_e_destinos_existentes(tmp_path):
    source = _database(tmp_path / "live.db")
    backup = create_backup(tmp_path / "backup", database=source)
    with (backup / "feature_store.db").open("ab") as handle:
        handle.write(b"truncated-or-tampered")
    with pytest.raises(BackupError, match="diverge"):
        verify_backup(backup)

    clean = create_backup(tmp_path / "clean", database=source)
    with pytest.raises(BackupError, match="ja existe"):
        create_backup(clean, database=source)
    with pytest.raises(BackupError, match="ja existe"):
        restore_backup(clean, tmp_path)


def test_backup_rejeita_banco_ausente_e_manifesto_invalido(tmp_path):
    with pytest.raises(BackupError, match="ausente"):
        create_backup(tmp_path / "backup", database=tmp_path / "missing.db")
    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "BACKUP_MANIFEST.json").write_text(json.dumps({"schema_version": "x"}))
    with pytest.raises(BackupError, match="invalido"):
        verify_backup(invalid)


def test_backup_detecta_sqlite_truncado_mesmo_com_manifesto_recalculado(tmp_path):
    source = _database(tmp_path / "live.db")
    backup = create_backup(tmp_path / "backup", database=source)
    database = backup / "feature_store.db"
    database.write_bytes(database.read_bytes()[:100])
    manifest_path = backup / "BACKUP_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["size_bytes"] = database.stat().st_size
    manifest["sha256"] = hashlib.sha256(database.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BackupError, match="verificar|integrity_check"):
        verify_backup(backup)


def test_backup_inclui_commit_em_wal_com_escritor_aberto(tmp_path):
    source = _database(tmp_path / "live.db")
    writer = sqlite3.connect(source)
    try:
        writer.execute("INSERT INTO candles VALUES (2, 102.5)")
        writer.commit()
        backup = create_backup(tmp_path / "backup", database=source)
    finally:
        writer.close()
    connection = sqlite3.connect(backup / "feature_store.db")
    try:
        assert connection.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 2
    finally:
        connection.close()
