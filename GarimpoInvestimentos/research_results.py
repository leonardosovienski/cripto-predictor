"""CRIPTO-owned authenticated ResearchResult outbox.

The outbox composes authority-preserving facts. It does not infer scientific
support from OPS success and only accepts results correlated to an admitted task.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from research_protocol import canonical, digest, loads, payload_hash, sign_result, validate_result


class ResultConflict(ValueError):
    pass


class ResultOutbox:
    def __init__(
        self,
        path,
        *,
        admission_store,
        publisher_identity: str,
        key_id: str | None = None,
        secret: bytes | None = None,
        key_store=None,
        scope: str = "crypto.research.result",
    ):
        self.path = Path(path)
        self.admission_store = admission_store
        self.publisher_identity = publisher_identity
        self.key_id = key_id
        self.secret = secret
        self.key_store = key_store
        self.scope = scope
        if key_store is None and (key_id is None or secret is None):
            raise ValueError("fixed key or operator key store required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS result_outbox(
                  result_id TEXT PRIMARY KEY,
                  task_id TEXT NOT NULL,
                  admission_id TEXT NOT NULL,
                  message_id TEXT NOT NULL UNIQUE,
                  payload_hash TEXT NOT NULL,
                  envelope BLOB NOT NULL,
                  status TEXT NOT NULL CHECK(status IN (
                    'PENDING','PUBLISHED','RETRYABLE','DEAD_LETTER')),
                  attempt_count INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL,
                  processed_at TEXT,
                  error TEXT
                )
                """
            )

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _authorize(self, result):
        context = self.admission_store.admitted_context(result["task_id"])
        task, receipt = context["task"], context["receipt"]
        expected = {
            "admission_id": receipt["admission_id"],
            "research_id": task["research_id"],
            "hypothesis_id": task["hypothesis_id"],
        }
        for field, value in expected.items():
            if result[field] != value:
                raise PermissionError(f"RESULT_NOT_AUTHORIZED: {field} does not match admission")
        provenance = result["provenance"]
        if provenance["task_payload_hash"] != context["task_payload_hash"]:
            raise PermissionError("RESULT_NOT_AUTHORIZED: task payload identity mismatch")
        if provenance["admission_policy_hash"] != receipt["policy_hash"]:
            raise PermissionError("RESULT_NOT_AUTHORIZED: admission policy identity mismatch")
        resolved_hash = digest(canonical(receipt["resolved_references"]))
        if provenance["resolved_references_hash"] != resolved_hash:
            raise PermissionError("RESULT_NOT_AUTHORIZED: admitted references identity mismatch")

    def produce(self, result):
        validate_result(result)
        self._authorize(result)
        key_id, secret = (
            self.key_store.signing_key(self.publisher_identity, self.scope)
            if self.key_store is not None
            else (self.key_id, self.secret)
        )
        envelope = sign_result(
            result,
            producer="CRIPTO",
            publisher_identity=self.publisher_identity,
            consumer="CAIN",
            scope=self.scope,
            key_id=key_id,
            secret=secret,
        )
        result_hash = payload_hash(result)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT payload_hash,envelope,status FROM result_outbox WHERE result_id=?",
                (result["result_id"],),
            ).fetchone()
            if previous:
                if previous["payload_hash"] != result_hash:
                    raise ResultConflict(
                        "CONFLICT: result_id already has a different canonical payload"
                    )
                return {
                    "status": "duplicate",
                    "outbox_status": previous["status"],
                    "envelope": loads(previous["envelope"]),
                }
            db.execute(
                "INSERT INTO result_outbox(result_id,task_id,admission_id,message_id,"
                "payload_hash,envelope,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    result["result_id"],
                    result["task_id"],
                    result["admission_id"],
                    envelope["message_id"],
                    result_hash,
                    canonical(envelope),
                    "PENDING",
                    result["produced_at"],
                ),
            )
        return {"status": "produced", "outbox_status": "PENDING", "envelope": envelope}

    def pending(self, limit: int = 100):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Invalid outbox limit")
        with self.connection() as db:
            rows = db.execute(
                "SELECT envelope FROM result_outbox WHERE status IN ('PENDING','RETRYABLE') "
                "ORDER BY created_at,result_id LIMIT ?",
                (limit,),
            ).fetchall()
        return [loads(row["envelope"]) for row in rows]

    def record_send(self, result_id, message_id):
        """Persist an at-least-once delivery attempt before invoking transport."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT envelope,message_id,status FROM result_outbox WHERE result_id=?",
                (result_id,),
            ).fetchone()
            if row is None or row["message_id"] != message_id:
                raise ValueError("ACK_CONFLICT: unknown result/message identity")
            if row["status"] == "PUBLISHED":
                return {"status": "already_published", "envelope": loads(row["envelope"])}
            if row["status"] == "DEAD_LETTER":
                raise ValueError("DELIVERY_BLOCKED: result is dead-lettered")
            db.execute(
                "UPDATE result_outbox SET attempt_count=attempt_count+1,error=NULL "
                "WHERE result_id=?",
                (result_id,),
            )
        return {"status": "send_recorded", "envelope": loads(row["envelope"])}

    def acknowledge(self, result_id, message_id, *, processed_at):
        parsed = datetime.fromisoformat(processed_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Invalid acknowledgement time")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT message_id,status,attempt_count FROM result_outbox WHERE result_id=?",
                (result_id,),
            ).fetchone()
            if row is None or row["message_id"] != message_id:
                raise ValueError("ACK_CONFLICT: unknown result/message identity")
            if row["attempt_count"] < 1:
                raise ValueError("ACK_CONFLICT: result has no recorded send")
            if row["status"] != "PUBLISHED":
                db.execute(
                    "UPDATE result_outbox SET status='PUBLISHED',processed_at=?,error=NULL "
                    "WHERE result_id=?",
                    (processed_at, result_id),
                )
        return self.state(result_id)

    def fail_delivery(self, result_id, message_id, error, *, max_attempts=3):
        if type(max_attempts) is not int or max_attempts < 1 or not error:
            raise ValueError("Invalid delivery failure")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT message_id,status,attempt_count FROM result_outbox WHERE result_id=?",
                (result_id,),
            ).fetchone()
            if row is None or row["message_id"] != message_id:
                raise ValueError("ACK_CONFLICT: unknown result/message identity")
            if row["status"] == "PUBLISHED":
                raise ValueError("ACK_CONFLICT: published result cannot fail delivery")
            status = "DEAD_LETTER" if row["attempt_count"] >= max_attempts else "RETRYABLE"
            db.execute(
                "UPDATE result_outbox SET status=?,error=? WHERE result_id=?",
                (status, error[:1000], result_id),
            )
        return self.state(result_id)

    def reconcile(self):
        with self.connection() as db:
            rows = db.execute(
                "SELECT status,count(*) AS count FROM result_outbox GROUP BY status"
            ).fetchall()
        counts = {row["status"]: row["count"] for row in rows}
        return {
            "pending": counts.get("PENDING", 0) + counts.get("RETRYABLE", 0),
            "published": counts.get("PUBLISHED", 0),
            "dead_letters": counts.get("DEAD_LETTER", 0),
        }

    def state(self, result_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT result_id,task_id,admission_id,message_id,payload_hash,status,"
                "attempt_count,created_at,processed_at,error FROM result_outbox WHERE result_id=?",
                (result_id,),
            ).fetchone()
        return dict(row) if row else None
