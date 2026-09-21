"""CRIPTO-owned durable admission for authenticated ResearchTaskV1 proposals.

This module does not execute tasks. It maps one allowlisted request type to a
local handler identity and freezes registry references for a later scheduler.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from research_protocol import canonical, digest, verify_task

POLICY_VERSION = "CryptoResearchAdmissionPolicyV1"
DECISIONS = {
    "ACCEPTED",
    "REJECTED",
    "EXPIRED",
    "CONFLICT",
    "UNAUTHORIZED",
    "REQUIRES_READMISSION",
}
KNOWN_HANDLERS = {
    "BACKTEST_EXISTING_HYPOTHESIS": "crypto.handlers.backtest_existing_hypothesis.v1"
}


def _keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f"POLICY_INVALID: unexpected or missing {label} fields")


def _timestamp(value):
    if type(value) is not str:
        raise ValueError("Invalid time")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Time requires timezone")
    return parsed.astimezone(timezone.utc)


def _now(value=None):
    if value is None:
        return datetime.now(timezone.utc)
    return _timestamp(value) if type(value) is str else value.astimezone(timezone.utc)


class AdmissionStore:
    def __init__(self, path, policy_path, *, keys, available_handlers=None):
        self.path = Path(path)
        self.policy_path = Path(policy_path)
        self.keys = dict(keys) if not hasattr(keys, "resolve") else None
        self.key_store = keys if hasattr(keys, "resolve") else None
        self.available_handlers = frozenset(
            KNOWN_HANDLERS.values() if available_handlers is None else available_handlers
        )
        if not self.available_handlers <= set(KNOWN_HANDLERS.values()):
            raise ValueError("Unknown local handler registration")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.policy()
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS task_inbox(
                  task_id TEXT PRIMARY KEY,
                  message_id TEXT NOT NULL UNIQUE,
                  payload_hash TEXT NOT NULL,
                  envelope BLOB NOT NULL,
                  received_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS admissions(
                  admission_id TEXT PRIMARY KEY,
                  task_id TEXT NOT NULL,
                  payload_hash TEXT NOT NULL,
                  decision TEXT NOT NULL,
                  reason_code TEXT NOT NULL,
                  policy_id TEXT NOT NULL,
                  policy_version INTEGER NOT NULL,
                  policy_hash TEXT NOT NULL,
                  decided_at TEXT NOT NULL,
                  publisher_identity TEXT NOT NULL,
                  scope TEXT NOT NULL,
                  resolved_references BLOB NOT NULL,
                  admitted_handler TEXT,
                  resource_budget BLOB NOT NULL,
                  normalized_priority TEXT,
                  provenance BLOB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS admissions_task ON admissions(task_id,decided_at);
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

    def policy(self):
        policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        _keys(
            policy,
            {
                "schema_version",
                "policy_id",
                "policy_version",
                "owner",
                "publishers",
                "handlers",
                "registry",
                "limits",
                "allowed_symbols",
            },
            "policy",
        )
        if policy["schema_version"] != POLICY_VERSION or policy["owner"] != "CRIPTO_OPERATOR":
            raise ValueError("POLICY_INVALID: CRIPTO/operator ownership required")
        if type(policy["policy_id"]) is not str or type(policy["policy_version"]) is not int:
            raise ValueError("POLICY_INVALID: identity")
        if type(policy["publishers"]) is not list or len(policy["publishers"]) > 100:
            raise ValueError("POLICY_INVALID: publishers")
        publisher_keys = set()
        for publisher in policy["publishers"]:
            _keys(publisher, {"publisher_identity", "key_id", "scopes", "revoked"}, "publisher")
            identity = (publisher["publisher_identity"], publisher["key_id"])
            if identity in publisher_keys or type(publisher["revoked"]) is not bool:
                raise ValueError("POLICY_INVALID: publisher identity")
            if type(publisher["scopes"]) is not list or not publisher["scopes"]:
                raise ValueError("POLICY_INVALID: publisher scopes")
            publisher_keys.add(identity)
        if policy["handlers"] != KNOWN_HANDLERS:
            raise ValueError("POLICY_INVALID: handlers must equal the compiled allowlist")
        if type(policy["registry"]) is not list or not policy["registry"]:
            raise ValueError("POLICY_INVALID: registry")
        registry_keys = set()
        for entry in policy["registry"]:
            _keys(
                entry,
                {"kind", "name", "version", "revision_id", "content_hash", "scopes"},
                "registry entry",
            )
            identity = (entry["kind"], entry["name"], entry["version"])
            if identity in registry_keys:
                raise ValueError("POLICY_INVALID: duplicate registry entry")
            if (
                type(entry["revision_id"]) is not str
                or type(entry["content_hash"]) is not str
                or len(entry["content_hash"]) != 64
                or type(entry["scopes"]) is not list
            ):
                raise ValueError("POLICY_INVALID: registry identity")
            registry_keys.add(identity)
        _keys(
            policy["limits"],
            {
                "max_pending_tasks",
                "max_task_bytes",
                "max_refs",
                "max_parameter_bytes",
                "rate_limit_per_minute",
                "max_concurrency",
                "cpu_seconds",
                "memory_mb",
                "disk_mb",
                "timeout_seconds",
                "max_retries",
                "dead_letter_threshold",
                "max_age_seconds",
                "per_publisher_pending",
                "max_priority",
            },
            "limits",
        )
        numeric = {key: value for key, value in policy["limits"].items() if key != "max_priority"}
        if any(type(value) is not int or value < 0 for value in numeric.values()):
            raise ValueError("POLICY_INVALID: numeric limits")
        if policy["limits"]["max_priority"] not in {"LOW", "NORMAL", "HIGH"}:
            raise ValueError("POLICY_INVALID: max_priority")
        if (
            type(policy["allowed_symbols"]) is not list
            or not policy["allowed_symbols"]
            or not all(type(item) is str for item in policy["allowed_symbols"])
        ):
            raise ValueError("POLICY_INVALID: symbols")
        return policy

    @staticmethod
    def policy_hash(policy):
        return digest(canonical(policy))

    @staticmethod
    def _publisher(policy, identity, key_id):
        for publisher in policy["publishers"]:
            if (publisher["publisher_identity"], publisher["key_id"]) == (identity, key_id):
                return publisher
        return None

    @staticmethod
    def _resolve(policy, task, scope):
        references = [
            task["protocol_ref"],
            task["dataset_constraint_ref"],
            *task["baseline_refs"],
            task["cost_model_ref"],
            *task["evidence_refs"],
        ]
        resolved = []
        for reference in references:
            match = next(
                (
                    entry
                    for entry in policy["registry"]
                    if all(entry[key] == reference[key] for key in ("kind", "name", "version"))
                    and scope in entry["scopes"]
                ),
                None,
            )
            if match is None:
                raise PermissionError("REFERENCE_UNAUTHORIZED_OR_UNKNOWN")
            resolved.append(
                {
                    "kind": match["kind"],
                    "name": match["name"],
                    "version": match["version"],
                    "revision_id": match["revision_id"],
                    "content_hash": match["content_hash"],
                }
            )
        return resolved

    @staticmethod
    def _priority(requested, maximum):
        levels = ["LOW", "NORMAL", "HIGH"]
        return levels[min(levels.index(requested), levels.index(maximum))]

    def _evaluate(self, envelope, policy, now):
        publisher = self._publisher(
            policy, envelope["publisher_identity"], envelope["key_id"]
        )
        if (
            envelope["producer"] != "CAIN"
            or envelope["consumer"] != "CRIPTO"
            or publisher is None
            or publisher["revoked"]
            or envelope["scope"] not in publisher["scopes"]
        ):
            return "UNAUTHORIZED", "PUBLISHER_OR_SCOPE_DENIED", [], None
        try:
            verify_task(envelope, lambda identity, key_id: self._resolve_key(
                identity, key_id, envelope["scope"]
            ))
        except PermissionError:
            return "UNAUTHORIZED", "AUTHENTICATION_FAILED", [], None
        task = envelope["payload"]
        if now >= _timestamp(task["expires_at"]):
            return "EXPIRED", "TASK_EXPIRED", [], None
        age = (now - _timestamp(task["created_at"])).total_seconds()
        if age < 0 or age > policy["limits"]["max_age_seconds"]:
            return "REJECTED", "TASK_AGE_OUT_OF_POLICY", [], None
        if len(canonical(task)) > policy["limits"]["max_task_bytes"]:
            return "REJECTED", "TASK_SIZE_LIMIT", [], None
        refs = 3 + len(task["baseline_refs"]) + len(task["evidence_refs"])
        if refs > policy["limits"]["max_refs"]:
            return "REJECTED", "REFERENCE_LIMIT", [], None
        if len(canonical(task["bounded_parameters"])) > policy["limits"]["max_parameter_bytes"]:
            return "REJECTED", "PARAMETER_SIZE_LIMIT", [], None
        if task["bounded_parameters"]["symbol"] not in policy["allowed_symbols"]:
            return "REJECTED", "SYMBOL_NOT_ALLOWED", [], None
        handler = policy["handlers"].get(task["request_type"])
        if handler not in KNOWN_HANDLERS.values():
            return "REJECTED", "HANDLER_NOT_ALLOWED", [], None
        if handler not in self.available_handlers:
            return "REJECTED", "HANDLER_UNAVAILABLE", [], None
        try:
            resolved = self._resolve(policy, task, envelope["scope"])
        except PermissionError:
            return "REJECTED", "REFERENCE_UNAUTHORIZED_OR_UNKNOWN", [], None
        return "ACCEPTED", "ADMITTED", resolved, handler

    def _receipt(self, envelope, policy, now, decision, reason, resolved, handler):
        policy_hash = self.policy_hash(policy)
        task = envelope["payload"]
        budget = {
            key: policy["limits"][key]
            for key in (
                "max_concurrency",
                "cpu_seconds",
                "memory_mb",
                "disk_mb",
                "timeout_seconds",
                "max_retries",
                "dead_letter_threshold",
            )
        }
        admission_id = digest(
            canonical([task["task_id"], envelope["payload_hash"], policy_hash, decision, reason])
        )
        return {
            "admission_id": admission_id,
            "task_id": task["task_id"],
            "payload_hash": envelope["payload_hash"],
            "decision": decision,
            "reason_code": reason,
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "policy_hash": policy_hash,
            "decided_at": now.isoformat(),
            "publisher_identity": envelope["publisher_identity"],
            "scope": envelope["scope"],
            "resolved_references": resolved,
            "admitted_handler": handler,
            "resource_budget": budget,
            "normalized_priority": self._priority(
                task["priority_hint"], policy["limits"]["max_priority"]
            )
            if decision == "ACCEPTED"
            else None,
            "provenance": {
                "message_id": envelope["message_id"],
                "authentication_method": envelope["authentication_method"],
                "key_id": envelope["key_id"],
                "authorization_result": "AUTHORIZED" if decision == "ACCEPTED" else "DENIED",
            },
        }

    def _persist_receipt(self, db, receipt):
        db.execute(
            "INSERT OR IGNORE INTO admissions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                receipt["admission_id"],
                receipt["task_id"],
                receipt["payload_hash"],
                receipt["decision"],
                receipt["reason_code"],
                receipt["policy_id"],
                receipt["policy_version"],
                receipt["policy_hash"],
                receipt["decided_at"],
                receipt["publisher_identity"],
                receipt["scope"],
                canonical(receipt["resolved_references"]),
                receipt["admitted_handler"],
                canonical(receipt["resource_budget"]),
                receipt["normalized_priority"],
                canonical(receipt["provenance"]),
            ),
        )

    def submit(self, envelope, *, now=None):
        now = _now(now)
        policy = self.policy()
        # Contract validation occurs inside _evaluate/verify_task before acceptance.
        decision, reason, resolved, handler = self._evaluate(envelope, policy, now)
        task = envelope["payload"]
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT payload_hash FROM task_inbox WHERE task_id=?", (task["task_id"],)
            ).fetchone()
            if existing and existing["payload_hash"] != envelope["payload_hash"]:
                receipt = self._receipt(
                    envelope, policy, now, "CONFLICT", "TASK_ID_PAYLOAD_CONFLICT", [], None
                )
                self._persist_receipt(db, receipt)
                return receipt
            if existing:
                row = db.execute(
                    "SELECT * FROM admissions WHERE task_id=? AND payload_hash=? "
                    "ORDER BY decided_at LIMIT 1",
                    (task["task_id"], envelope["payload_hash"]),
                ).fetchone()
                decoded = self._decode_receipt(row)
                if decoded is None:
                    raise ValueError("ADMISSION_RECEIPT_NOT_FOUND")
                return decoded | {"duplicate": True}
            pending = db.execute(
                "SELECT count(*) FROM admissions WHERE decision='ACCEPTED'"
            ).fetchone()[0]
            publisher_pending = db.execute(
                "SELECT count(*) FROM admissions WHERE decision='ACCEPTED' AND publisher_identity=?",
                (envelope["publisher_identity"],),
            ).fetchone()[0]
            minute = now.timestamp() - 60
            recent = sum(
                _timestamp(row[0]).timestamp() >= minute
                for row in db.execute(
                    "SELECT decided_at FROM admissions WHERE publisher_identity=?",
                    (envelope["publisher_identity"],),
                )
            )
            if decision == "ACCEPTED" and pending >= policy["limits"]["max_pending_tasks"]:
                decision, reason, resolved, handler = "REJECTED", "GLOBAL_PENDING_QUOTA", [], None
            elif decision == "ACCEPTED" and publisher_pending >= policy["limits"]["per_publisher_pending"]:
                decision, reason, resolved, handler = "REJECTED", "PUBLISHER_PENDING_QUOTA", [], None
            elif decision == "ACCEPTED" and recent >= policy["limits"]["rate_limit_per_minute"]:
                decision, reason, resolved, handler = "REJECTED", "RATE_LIMIT", [], None
            receipt = self._receipt(envelope, policy, now, decision, reason, resolved, handler)
            db.execute(
                "INSERT INTO task_inbox VALUES(?,?,?,?,?)",
                (
                    task["task_id"],
                    envelope["message_id"],
                    envelope["payload_hash"],
                    canonical(envelope),
                    now.isoformat(),
                ),
            )
            self._persist_receipt(db, receipt)
        return receipt

    @staticmethod
    def _decode_receipt(row) -> dict | None:
        if row is None:
            return None
        value = dict(row)
        for key in ("resolved_references", "resource_budget", "provenance"):
            value[key] = json.loads(value[key])
        return value

    def receipt(self, task_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM admissions WHERE task_id=? ORDER BY decided_at DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        return self._decode_receipt(row)

    def _resolve_key(self, identity, key_id, scope):
        if self.key_store is not None:
            return self.key_store.resolve(identity, key_id, scope)
        if self.keys is None:
            return None
        return self.keys.get((identity, key_id))

    def admitted_context(self, task_id):
        """Return the immutable task and latest receipt only when admission is accepted."""
        with self.connection() as db:
            inbox = db.execute(
                "SELECT envelope,payload_hash FROM task_inbox WHERE task_id=?", (task_id,)
            ).fetchone()
        receipt = self.receipt(task_id)
        if inbox is None or receipt is None or receipt["decision"] != "ACCEPTED":
            raise PermissionError("RESULT_NOT_AUTHORIZED: task has no accepted admission")
        envelope = json.loads(inbox["envelope"])
        return {
            "task": envelope["payload"],
            "task_payload_hash": inbox["payload_hash"],
            "receipt": receipt,
        }

    def revalidate(self, task_id, *, now=None):
        now = _now(now)
        current = self.policy()
        with self.connection() as db:
            inbox = db.execute("SELECT envelope FROM task_inbox WHERE task_id=?", (task_id,)).fetchone()
        if inbox is None:
            raise ValueError("TASK_NOT_FOUND")
        envelope = json.loads(inbox["envelope"])
        previous = self.receipt(task_id)
        if previous is None:
            raise ValueError("ADMISSION_RECEIPT_NOT_FOUND")
        if previous["decision"] != "ACCEPTED":
            return {"decision": previous["decision"], "reason_code": "NOT_PREVIOUSLY_ACCEPTED"}
        if previous["policy_hash"] != self.policy_hash(current):
            return {"decision": "REQUIRES_READMISSION", "reason_code": "POLICY_CHANGED"}
        decision, reason, resolved, handler = self._evaluate(envelope, current, now)
        if decision != "ACCEPTED":
            return {"decision": decision, "reason_code": reason}
        if resolved != previous["resolved_references"] or handler != previous["admitted_handler"]:
            return {"decision": "REQUIRES_READMISSION", "reason_code": "RESOLUTION_CHANGED"}
        return {
            "decision": "ACCEPTED",
            "reason_code": "REVALIDATED",
            "admission_id": previous["admission_id"],
            "admitted_handler": handler,
            "resolved_references": resolved,
        }
