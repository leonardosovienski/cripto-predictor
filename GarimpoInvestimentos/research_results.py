"""CRIPTO-owned authoritative result store (no envelope, no signing, no transport).

Each terminal result is stored once per request, keyed by result_id, together with its
canonical content hash and the path of the immutable result file. After a restart the
result is re-read from here and both copies are checked; any divergence fails closed
(RECONCILIATION_REQUIRED), never repaired silently.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from GarimpoInvestimentos.research_contract import canonical, content_hash, validate_result


class ResultConflict(ValueError):
    """A different payload already exists for the same result/request/experiment."""


class ResultIntegrityError(ValueError):
    """The authoritative copy and the result file disagree or were altered."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class ResultStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS results(
                  result_id TEXT PRIMARY KEY,
                  request_id TEXT NOT NULL UNIQUE,
                  experiment_id TEXT NOT NULL UNIQUE,
                  content_hash TEXT NOT NULL,
                  result BLOB NOT NULL,
                  result_path TEXT NOT NULL,
                  stored_at TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def store(self, result: dict, result_path: Path) -> dict:
        validate_result(result)
        raw = canonical(result)
        chash = content_hash(result)
        if Path(result_path).read_bytes() != raw:
            raise ResultIntegrityError("result file bytes differ from the result being stored")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT result_id,request_id,experiment_id,content_hash FROM results "
                "WHERE result_id=? OR request_id=? OR experiment_id=?",
                (result["result_id"], result["request_id"], result["experiment_id"]),
            ).fetchall()
            for row in rows:
                if (
                    row["result_id"],
                    row["request_id"],
                    row["experiment_id"],
                    row["content_hash"],
                ) != (result["result_id"], result["request_id"], result["experiment_id"], chash):
                    raise ResultConflict(
                        "CONFLICT: a different result already exists for this identity"
                    )
            if rows:
                return {"status": "duplicate", "content_hash": chash}
            db.execute(
                "INSERT INTO results(result_id,request_id,experiment_id,content_hash,result,result_path,stored_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    result["result_id"],
                    result["request_id"],
                    result["experiment_id"],
                    chash,
                    raw,
                    str(result_path),
                    _now(),
                ),
            )
        return {"status": "stored", "content_hash": chash}

    def _verified(self, row) -> dict:
        raw = bytes(row["result"])
        if hashlib.sha256(raw).hexdigest() != row["content_hash"]:
            raise ResultIntegrityError("stored result blob does not match its content hash")
        result = json.loads(raw)
        validate_result(result)
        path = Path(row["result_path"])
        if not path.exists():
            raise ResultIntegrityError("result file missing (database says it exists)")
        if path.read_bytes() != raw:
            raise ResultIntegrityError("result file altered after storage")
        if result["request_id"] != row["request_id"] or result["result_id"] != row["result_id"]:
            raise ResultIntegrityError("result metadata inconsistent with its index")
        return result

    def read_by_request(self, request_id: str) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM results WHERE request_id=?", (request_id,)).fetchone()
        return None if row is None else self._verified(row)

    def read(self, result_id: str) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM results WHERE result_id=?", (result_id,)).fetchone()
        return None if row is None else self._verified(row)

    def count(self) -> int:
        with self.connection() as db:
            return db.execute("SELECT count(*) FROM results").fetchone()[0]

    def reconcile(self) -> list[dict]:
        findings = []
        with self.connection() as db:
            rows = db.execute("SELECT * FROM results").fetchall()
        for row in rows:
            try:
                self._verified(row)
            except (ResultIntegrityError, ValueError) as exc:
                findings.append(
                    {
                        "result_id": row["result_id"],
                        "finding": "RESULT_STORE_INTEGRITY",
                        "error": str(exc),
                    }
                )
        return findings


__all__ = ["ResultConflict", "ResultIntegrityError", "ResultStore"]
