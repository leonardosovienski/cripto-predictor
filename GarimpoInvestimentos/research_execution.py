"""Recoverable CRIPTO-owned execution of admitted research requests (no envelope).

Every admitted request becomes one logical experiment. The domain effect is produced by
the closed worker running as a real predictor_ops job (lock, heartbeat, timeout,
attempt, economic idempotency and terminal events are produced by predictor_ops). The
scientific state is read back from the predictor_core trial registry. The authoritative
result is persisted in the ResultStore and re-read after restart, never recomputed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from predictor_core.contracts.trial_v2 import TrialRegistryV2
from predictor_ops import JobConfig, JobType, RunStatus, run_job
from predictor_ops.models import EconomicJobKey, RuntimeConfig

from GarimpoInvestimentos.durable_io import atomic_write, strict_json_loads
from GarimpoInvestimentos.research_contract import (
    RESULT_SCHEMA,
    canonical,
    content_hash,
    digest,
    utc,
    validate_result,
)
from GarimpoInvestimentos.research_faults import (
    FAULT_ENV,
    FAULT_EXIT,
    FAULT_POINTS,
    fault,
    worker_flag,
)

HANDLER = "crypto.handlers.backtest_existing_hypothesis.v1"
# On-disk layout kept short on purpose: the deepest predictor_ops file under OPS_DIR is
# idempotency/.economic-<sha256>.json.<uuid>.tmp (~129 chars), so a Windows state root
# must stay within MAX_STATE_ROOT_CHARS to remain under MAX_PATH (260).
EXEC_DIR = "x"
EXPERIMENTS_DIR = "e"
OPS_DIR = "o"
MAX_STATE_ROOT_CHARS = 120
STATES = (
    "PLANNED",
    "MATERIALIZED",
    "SCHEDULED",
    "RUNNING",
    "DOMAIN_EFFECT_COMMITTED",
    "MEASURED",
    "RESULT_CREATED",
    "RESULT_STORED",
    "COMPLETED",
    "FAILED_ATTEMPT",
    "REFUSED",
    "RECONCILIATION_REQUIRED",
)
_HASH = re.compile(r"[0-9a-f]{64}")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _json(path: Path) -> dict:
    value = strict_json_loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def _dist_identity(name: str) -> dict:
    """Installed distribution identity: version and sha256 of its RECORD."""
    from importlib.metadata import PackageNotFoundError, distribution

    try:
        dist = distribution(name)
    except PackageNotFoundError:
        return {"package": name, "version": None, "record_sha256": None}
    record = next((item for item in (dist.files or []) if item.name == "RECORD"), None)
    record_sha = _sha(Path(str(dist.locate_file(record)))) if record is not None else None
    return {"package": name, "version": dist.version, "record_sha256": record_sha}


class ExecutionError(RuntimeError):
    """Raised with an outcome status the entrypoint maps to an exit code."""

    def __init__(self, status: str, reason: str, detail: dict | None = None):
        super().__init__(f"{status}: {reason}")
        self.status = status
        self.reason = reason
        self.detail = detail or {}


class ReferenceStore:
    """Operator-owned immutable objects; requests only select registry hashes."""

    def __init__(self, root: str | Path, *, max_bytes: int = 32 * 1024 * 1024):
        self.root = Path(root).resolve()
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def object_path(self, object_hash: str) -> Path:
        if not _HASH.fullmatch(object_hash):
            raise ValueError("invalid content hash")
        return self.root / object_hash[:2] / object_hash

    def put_operator_bytes(self, raw: bytes) -> str:
        """Administrative provisioning boundary; never called with request data."""
        if not raw or len(raw) > self.max_bytes:
            raise ValueError("operator object size denied")
        strict_json_loads(raw.decode("utf-8"))
        object_hash = hashlib.sha256(raw).hexdigest()
        target = self.object_path(object_hash)
        if target.exists():
            if _sha(target) != object_hash:
                raise ValueError("operator object corruption")
            return object_hash
        atomic_write(target, raw)
        target.chmod(stat.S_IREAD)
        return object_hash

    def materialize(self, references: list[dict], destination: str | Path) -> list[dict]:
        destination = Path(destination).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        materialized = []
        kinds = set()
        for reference in references:
            if set(reference) != {"kind", "name", "version", "revision_id", "content_hash"}:
                raise ValueError("resolved reference shape changed")
            kind, expected = reference["kind"], reference["content_hash"]
            if kind in kinds or not re.fullmatch(r"[a-z_]{1,32}", kind):
                raise ValueError("reference kinds must be unique and bounded")
            kinds.add(kind)
            source = self.object_path(expected)
            if (
                not source.exists()
                or source.is_symlink()
                or getattr(source, "is_junction", lambda: False)()
            ):
                raise FileNotFoundError(f"admitted reference object unavailable: {kind}")
            resolved = source.resolve(strict=True)
            if not resolved.is_relative_to(self.root) or not resolved.is_file():
                raise PermissionError("reference object escapes operator store")
            size = resolved.stat().st_size
            if size <= 0 or size > self.max_bytes or _sha(resolved) != expected:
                raise ValueError(f"reference size/hash verification failed: {kind}")
            target = destination / f"{kind}.json"
            if target.exists() and _sha(target) != expected:
                raise ValueError(f"materialized reference changed after materialization: {kind}")
            if not target.exists():
                shutil.copyfile(resolved, target)
                target.chmod(stat.S_IREAD)
                fault("during_materialization")
            observed = _sha(target)
            if observed != expected:
                raise ValueError(f"materialized reference changed: {kind}")
            materialized.append(
                {
                    **reference,
                    "expected_hash": expected,
                    "observed_hash": observed,
                    "resolver_id": "crypto-operator-cas",
                    "resolver_version": "2",
                    "path": str(target),
                    "size": size,
                    "verification": "PASS",
                }
            )
        return materialized


class ExperimentJournal:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS experiments(
                  experiment_id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                  logical_hash TEXT NOT NULL, state TEXT NOT NULL,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                  effect_hash TEXT, result_hash TEXT, ops_run_id TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS transitions(
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id TEXT NOT NULL,
                  state TEXT NOT NULL, recorded_at TEXT NOT NULL, detail TEXT
                );
                CREATE TABLE IF NOT EXISTS attempts(
                  attempt_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, number INTEGER NOT NULL,
                  ops_run_id TEXT, ops_status TEXT, ops_exit_code INTEGER, state TEXT NOT NULL,
                  started_at TEXT NOT NULL, finished_at TEXT, ops_record_hash TEXT, error TEXT
                );
                CREATE INDEX IF NOT EXISTS attempts_experiment ON attempts(experiment_id,number);
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

    def ensure(self, experiment_id: str, request_id: str, logical_hash: str) -> dict:
        now = _now()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM experiments WHERE request_id=?", (request_id,)
            ).fetchone()
            if row:
                if row["experiment_id"] != experiment_id or row["logical_hash"] != logical_hash:
                    raise ExecutionError("RECONCILIATION_REQUIRED", "EXPERIMENT_IDENTITY_CONFLICT")
                return dict(row)
            db.execute(
                "INSERT INTO experiments(experiment_id,request_id,logical_hash,state,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?)",
                (experiment_id, request_id, logical_hash, "PLANNED", now, now),
            )
            db.execute(
                "INSERT INTO transitions(experiment_id,state,recorded_at,detail) VALUES(?,?,?,?)",
                (experiment_id, "PLANNED", now, "admitted logical identity"),
            )
        return self.get(experiment_id)

    def transition(self, experiment_id: str, state: str, *, detail: str = "", **fields) -> dict:
        if state not in STATES or set(fields) - {
            "effect_hash",
            "result_hash",
            "ops_run_id",
            "error",
        }:
            raise ValueError("invalid journal transition")
        now = _now()
        assignments = ["state=?", "updated_at=?"] + [f"{key}=?" for key in fields]
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if (
                db.execute(
                    "SELECT 1 FROM experiments WHERE experiment_id=?", (experiment_id,)
                ).fetchone()
                is None
            ):
                raise ValueError("unknown experiment")
            db.execute(
                f"UPDATE experiments SET {','.join(assignments)} WHERE experiment_id=?",
                [state, now, *fields.values(), experiment_id],
            )
            db.execute(
                "INSERT INTO transitions(experiment_id,state,recorded_at,detail) VALUES(?,?,?,?)",
                (experiment_id, state, now, detail[:1000]),
            )
        return self.get(experiment_id)

    def get(self, experiment_id: str) -> dict:
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)
            ).fetchone()
        if row is None:
            raise ValueError("unknown experiment")
        return dict(row)

    def first_transition_at(self, experiment_id: str, state: str) -> str | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT recorded_at FROM transitions WHERE experiment_id=? AND state=? ORDER BY sequence LIMIT 1",
                (experiment_id, state),
            ).fetchone()
        return row["recorded_at"] if row else None

    def start_attempt(self, experiment_id: str) -> tuple[str, int]:
        attempt_id = "crypto:ATTEMPT-" + uuid4().hex
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            number = (
                db.execute(
                    "SELECT count(*) FROM attempts WHERE experiment_id=?", (experiment_id,)
                ).fetchone()[0]
                + 1
            )
            db.execute(
                "INSERT INTO attempts(attempt_id,experiment_id,number,state,started_at) VALUES(?,?,?,?,?)",
                (attempt_id, experiment_id, number, "RUNNING", _now()),
            )
        return attempt_id, number

    def finish_attempt(
        self, attempt_id: str, *, state: str, run=None, error: str | None = None
    ) -> None:
        if state not in {"SUCCEEDED", "FAILED", "SKIPPED_ALREADY_SUCCEEDED", "REFUSED"}:
            raise ValueError("invalid attempt state")
        with self.connection() as db:
            db.execute(
                "UPDATE attempts SET state=?,ops_run_id=?,ops_status=?,ops_exit_code=?,finished_at=?,"
                "ops_record_hash=?,error=? WHERE attempt_id=?",
                (
                    state,
                    getattr(run, "run_id", None),
                    getattr(getattr(run, "run_status", None), "value", None),
                    getattr(run, "exit_code", None),
                    _now(),
                    content_hash(run.record) if run is not None else None,
                    (error or "")[:2000] or None,
                    attempt_id,
                ),
            )

    def attempts(self, experiment_id: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM attempts WHERE experiment_id=? ORDER BY number", (experiment_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def close_interrupted_attempts(self, experiment_id: str) -> int:
        """Attempts left RUNNING by a crashed process are closed as FAILED (never re-counted as success)."""
        with self.connection() as db:
            cursor = db.execute(
                "UPDATE attempts SET state='FAILED',finished_at=?,error='INTERRUPTED: process ended during attempt' "
                "WHERE experiment_id=? AND state='RUNNING'",
                (_now(), experiment_id),
            )
        return cursor.rowcount


def experiment_dir(execution_root: Path, logical_hash: str) -> Path:
    return Path(execution_root) / EXPERIMENTS_DIR / logical_hash[:16]


def ops_terminal_records(ops_root: Path, job_id: str) -> list[dict]:
    """Terminal run records written by predictor_ops (events.jsonl), oldest first."""
    events = ops_root / job_id / "events.jsonl"
    if not events.exists():
        return []
    records = []
    for line in events.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = strict_json_loads(line)
        if isinstance(record, dict) and record.get("finished_at"):
            records.append(record)
    return records


class ResearchExecutor:
    def __init__(
        self,
        root: str | Path,
        *,
        admission_store,
        result_store,
        reference_store: ReferenceStore,
        python_executable: str | None = None,
    ):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.admission_store = admission_store
        self.result_store = result_store
        self.references = reference_store
        self.python = python_executable or sys.executable
        self.journal = ExperimentJournal(self.root / "journal.sqlite")
        self.ops_root = self.root / OPS_DIR
        self.identities = {
            "core": _dist_identity("predictor-core"),
            "ops": _dist_identity("predictor-ops"),
            "crypto": _dist_identity("cripto-predictor"),
        }

    @staticmethod
    def logical_identity(context: dict) -> tuple[str, str]:
        receipt, request = context["receipt"], context["request"]
        logical_hash = content_hash(
            {
                "request_id": request["request_id"],
                "request_content_hash": context["request_content_hash"],
                "admission_id": receipt["admission_id"],
                "handler": receipt["admitted_handler"],
                "references": receipt["resolved_references"],
            }
        )
        return "crypto:EXP-" + logical_hash[:32], logical_hash

    def _work(self, logical_hash: str) -> Path:
        return experiment_dir(self.root, logical_hash)

    def _job_config(
        self,
        context,
        experiment_id,
        logical_hash,
        work,
        request_path,
        effect_path,
        trial_path,
        number,
    ):
        request = context["request"]
        budget = context["receipt"]["resource_budget"]
        command = [
            self.python,
            "-m",
            "GarimpoInvestimentos.research_worker",
            "--request",
            str(request_path),
            "--effect",
            str(effect_path),
            "--trial-registry",
            str(trial_path),
        ]
        command += worker_flag()
        environment = {FAULT_ENV: ""}
        return JobConfig(
            id="crypto-research-" + logical_hash[:24],
            command=command,
            cwd=work,
            environment=environment,
            timeout_seconds=budget["timeout_seconds"],
            heartbeat_interval_seconds=1,
            expected_artifact=effect_path,
            provenance={
                "domain": "crypto",
                "request_id": request["request_id"],
                "admission_id": context["receipt"]["admission_id"],
                "logical_hash": logical_hash,
            },
            input_reference=_sha(request_path),
            output_reference=str(effect_path),
            retry_count=number - 1,
            scientific_state="RESEARCH_BACKTEST",
            job_type=JobType.SHADOW_DECISION,
            economic_key=EconomicJobKey(
                domain="crypto",
                event_id=experiment_id,
                market=request["parameters"]["symbol"],
                decision_stage="research_backtest",
                logical_time=utc(request["data_cutoff"], "data_cutoff"),
            ),
            capital_permission=False,
            exit_statuses={0: RunStatus.SUCCEEDED},
            runtime=RuntimeConfig(root=self.ops_root),
        )

    def execute(self, request_id: str) -> dict:
        context = self.admission_store.admitted_context(request_id)
        receipt, request = context["receipt"], context["request"]
        if receipt["admitted_handler"] != HANDLER:
            raise ExecutionError("REJECTED", "HANDLER_NOT_COMPILED")
        experiment_id, logical_hash = self.logical_identity(context)
        row = self.journal.ensure(experiment_id, request_id, logical_hash)
        work = self._work(logical_hash)
        effect_path, result_path = work / "domain-effect.json", work / "research-result.json"
        existing = self.result_store.read_by_request(request_id)
        if existing is None and self.journal.first_transition_at(experiment_id, "RESULT_STORED"):
            self.journal.transition(
                experiment_id,
                "RECONCILIATION_REQUIRED",
                error="journal says the result was stored but the result store has none",
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "STORED_RESULT_MISSING_FROM_INDEX")
        if existing is not None:
            self._check_integrity(experiment_id, row, effect_path, result_path)
            # Authoritative result already stored: finish any step a crash interrupted.
            self.admission_store.mark_terminal(request_id, existing["result_id"])
            if row["state"] != "COMPLETED":
                self.journal.transition(
                    experiment_id, "COMPLETED", detail="reconciled from stored result"
                )
            return {"status": "DUPLICATE", "result": existing, "experiment_id": experiment_id}
        # No authoritative result yet: the current policy must still admit the request
        # (a stored result is an immutable fact and is returned above whatever the policy).
        revalidated = self.admission_store.revalidate(request_id)
        if revalidated["decision"] != "ACCEPTED":
            raise ExecutionError("REJECTED", revalidated["reason_code"])
        if row["state"] in {"REFUSED", "RECONCILIATION_REQUIRED"}:
            raise ExecutionError(
                "TEMPORAL_INTEGRITY_VIOLATION"
                if (row["error"] or "").startswith("TEMPORAL")
                else "RECONCILIATION_REQUIRED"
                if row["state"] == "RECONCILIATION_REQUIRED"
                else "REJECTED",
                row["error"] or row["state"],
            )
        self.journal.close_interrupted_attempts(experiment_id)
        refs_dir = work / "references"
        trial_path = work / "trials-v2.json"
        refusal_path = work / "worker-refusal.json"

        # Materialize (verified every time; changed bytes fail closed).
        receipt_path = work / "reference-materialization.json"
        try:
            materialized = self.references.materialize(receipt["resolved_references"], refs_dir)
        except FileNotFoundError as exc:
            raise ExecutionError("NOT_READY", str(exc)) from exc
        except (ValueError, PermissionError) as exc:
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error=f"REFERENCE: {exc}"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", f"REFERENCE: {exc}") from exc
        materialization = {
            "schema": "crypto-reference-materialization/2",
            "request_id": request_id,
            "experiment_id": experiment_id,
            "references": materialized,
        }
        if receipt_path.exists():
            recorded = _json(receipt_path)
            if (recorded.get("request_id"), recorded.get("experiment_id")) != (
                request_id,
                experiment_id,
            ):
                self.journal.transition(
                    experiment_id,
                    "RECONCILIATION_REQUIRED",
                    error="REFERENCE: materialization belongs to another request",
                )
                raise ExecutionError("RECONCILIATION_REQUIRED", "REFERENCE_FROM_ANOTHER_REQUEST")
            if recorded != materialization:
                self.journal.transition(
                    experiment_id,
                    "RECONCILIATION_REQUIRED",
                    error="REFERENCE: materialization receipt conflict",
                )
                raise ExecutionError("RECONCILIATION_REQUIRED", "MATERIALIZATION_RECEIPT_CONFLICT")
        else:
            atomic_write(receipt_path, canonical(materialization))
        materialization_hash = _sha(receipt_path)
        if row["state"] == "PLANNED":
            self.journal.transition(
                experiment_id, "MATERIALIZED", detail="all admitted hashes verified"
            )

        worker_request = {
            "schema": "crypto-admitted-backtest/2",
            "experiment_id": experiment_id,
            "trial_id": "crypto:TRIAL-" + logical_hash[:32],
            "request": {key: value for key, value in request.items() if key != "client_ref"},
            "references": [{"kind": item["kind"], "path": item["path"]} for item in materialized],
            "identities": {item["kind"]: item["content_hash"] for item in materialized},
            "registered_at": self.journal.get(experiment_id)["created_at"],
            "code_version": "cripto-predictor=={version}+record.{record}".format(
                version=self.identities["crypto"]["version"],
                record=(self.identities["crypto"]["record_sha256"] or "none")[:16],
            ),
        }
        request_path = work / "worker-request.json"
        raw_request = canonical(worker_request)
        if request_path.exists() and request_path.read_bytes() != raw_request:
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="worker request conflict"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "WORKER_REQUEST_CONFLICT")
        if not request_path.exists():
            atomic_write(request_path, raw_request)

        recorded = self.journal.get(experiment_id)
        self._check_integrity(experiment_id, recorded, effect_path, result_path)
        fault("before_ops")

        run = None
        attempt_id = None
        if not effect_path.exists():
            attempts = self.journal.attempts(experiment_id)
            failed = sum(1 for item in attempts if item["state"] == "FAILED")
            if failed > receipt["resource_budget"]["max_retries"]:
                return self._terminal_failure(
                    context, experiment_id, logical_hash, attempts, materialization_hash
                )
            attempt_id, number = self.journal.start_attempt(experiment_id)
            config = self._job_config(
                context,
                experiment_id,
                logical_hash,
                work,
                request_path,
                effect_path,
                trial_path,
                number,
            )
            self.journal.transition(
                experiment_id, "SCHEDULED", detail="static worker selected by handler identity"
            )
            self.journal.transition(
                experiment_id, "RUNNING", detail=f"delegated to predictor_ops attempt {number}"
            )
            try:
                run = run_job(config)
            except Exception as exc:  # noqa: BLE001 - Ops failure is recorded, never a result
                self.journal.finish_attempt(
                    attempt_id, state="FAILED", error=f"OPS_EXCEPTION {type(exc).__name__}: {exc}"
                )
                self.journal.transition(
                    experiment_id, "FAILED_ATTEMPT", error=f"OPS_EXCEPTION {type(exc).__name__}"
                )
                raise ExecutionError(
                    "OPS_FAILED_RETRYABLE",
                    f"OPS_EXCEPTION {type(exc).__name__}",
                    {"operational_state": "FAILED"},
                ) from exc
            fault("after_ops")
            if (
                run.run_status is RunStatus.SKIPPED
                and run.record.get("reason") == "economic_operation_already_claimed"
            ):
                # Ops already holds a SUCCEEDED run for this experiment: reconcile, never re-run.
                self.journal.finish_attempt(attempt_id, state="SKIPPED_ALREADY_SUCCEEDED", run=run)
                if not effect_path.exists():
                    self.journal.transition(
                        experiment_id,
                        "RECONCILIATION_REQUIRED",
                        error="Ops reports SUCCEEDED but effect bytes are missing",
                    )
                    raise ExecutionError(
                        "RECONCILIATION_REQUIRED", "EFFECT_MISSING_AFTER_OPS_SUCCESS"
                    )
            elif run.run_status is RunStatus.SKIPPED:
                self.journal.finish_attempt(
                    attempt_id, state="FAILED", run=run, error=str(run.record.get("reason"))
                )
                self.journal.transition(
                    experiment_id, "FAILED_ATTEMPT", error=f"OPS_SKIPPED {run.record.get('reason')}"
                )
                raise ExecutionError(
                    "OPS_FAILED_RETRYABLE",
                    f"OPS_SKIPPED {run.record.get('reason')}",
                    {"operational_state": "FAILED", "ops_run_id": run.run_id},
                )
            elif run.run_status is not RunStatus.SUCCEEDED:
                timed_out = (run.record.get("termination") or {}).get("reason") == "timeout"
                if refusal_path.exists():
                    refusal = _json(refusal_path)
                    self.journal.finish_attempt(
                        attempt_id, state="REFUSED", run=run, error=refusal.get("reason")
                    )
                    if refusal.get("exit_code") == 6:
                        refusal_path.replace(
                            refusal_path.with_name(
                                f"worker-refusal.{attempt_id.split('-')[-1]}.json"
                            )
                        )
                        self.journal.transition(
                            experiment_id,
                            "RECONCILIATION_REQUIRED",
                            error=f"REFERENCE: {refusal.get('reason')}",
                        )
                        raise ExecutionError(
                            "RECONCILIATION_REQUIRED",
                            f"REFERENCE: {refusal.get('reason')}",
                            {"operational_state": run.run_status.value, "ops_run_id": run.run_id},
                        )
                    temporal = refusal.get("exit_code") == 4
                    error = ("TEMPORAL: " if temporal else "REFUSED: ") + str(refusal.get("reason"))
                    self.journal.transition(experiment_id, "REFUSED", error=error)
                    terminal = "crypto:REFUSED-" + logical_hash[:32]
                    self.admission_store.mark_terminal(request_id, terminal)
                    raise ExecutionError(
                        "TEMPORAL_INTEGRITY_VIOLATION" if temporal else "REJECTED",
                        error,
                        {"operational_state": run.run_status.value, "ops_run_id": run.run_id},
                    )
                self.journal.finish_attempt(
                    attempt_id,
                    state="FAILED",
                    run=run,
                    error=json.dumps(
                        {
                            "run_status": run.run_status.value,
                            "exit_code": run.exit_code,
                            "termination": run.record.get("termination"),
                        },
                        sort_keys=True,
                    ),
                )
                self.journal.transition(
                    experiment_id,
                    "FAILED_ATTEMPT",
                    error=f"OPS_{'TIMEOUT' if timed_out else run.run_status.value}",
                )
                raise ExecutionError(
                    "OPS_FAILED_RETRYABLE",
                    f"OPS_{'TIMEOUT' if timed_out else run.run_status.value}",
                    {
                        "operational_state": "TIMEOUT" if timed_out else "FAILED",
                        "ops_run_id": run.run_id,
                        "exit_code": run.exit_code,
                        "attempt_id": attempt_id,
                    },
                )
            else:
                self.journal.finish_attempt(attempt_id, state="SUCCEEDED", run=run)
            fault("after_domain_effect")

        effect_hash = _sha(effect_path)
        recorded = self.journal.get(experiment_id)
        if recorded["effect_hash"] and recorded["effect_hash"] != effect_hash:
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="effect hash mismatch"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_HASH_MISMATCH")
        ops_record = self._ops_success_record(logical_hash)
        self.journal.transition(
            experiment_id,
            "DOMAIN_EFFECT_COMMITTED",
            detail="immutable effect verified",
            effect_hash=effect_hash,
            ops_run_id=ops_record["run_id"],
        )
        effect = _json(effect_path)
        if effect.get("experiment_id") != experiment_id:
            self.journal.transition(
                experiment_id,
                "RECONCILIATION_REQUIRED",
                error="effect belongs to another experiment",
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_EXPERIMENT_MISMATCH")
        core_trial = self._core_trial(effect, trial_path, experiment_id)
        self.journal.transition(
            experiment_id, "MEASURED", detail="causal domain output and Core trial loaded"
        )

        # The result is a deterministic function of the committed inputs; its hash is
        # journaled BEFORE the bytes are written (intent), so a crash at any point either
        # finds matching bytes, regenerates the same bytes, or fails closed.
        attempts = self.journal.attempts(experiment_id)
        produced_at = self.journal.first_transition_at(experiment_id, "DOMAIN_EFFECT_COMMITTED")
        result = self._result(
            context,
            experiment_id,
            logical_hash,
            effect,
            effect_hash,
            core_trial,
            ops_record,
            attempts,
            materialization_hash,
            produced_at,
        )
        raw = canonical(result)
        result_hash = digest(raw)
        recorded = self.journal.get(experiment_id)
        if recorded["result_hash"] is None:
            self.journal.transition(
                experiment_id,
                "RESULT_CREATED",
                detail="crypto-research-result/1 validated",
                result_hash=result_hash,
            )
        elif recorded["result_hash"] != result_hash:
            self.journal.transition(
                experiment_id,
                "RECONCILIATION_REQUIRED",
                error="regenerated result differs from the journaled result",
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "RESULT_NOT_REPRODUCIBLE")
        if result_path.exists():
            if _sha(result_path) != result_hash:
                self.journal.transition(
                    experiment_id, "RECONCILIATION_REQUIRED", error="result file hash mismatch"
                )
                raise ExecutionError("RECONCILIATION_REQUIRED", "RESULT_HASH_MISMATCH")
        else:
            if os.environ.get(FAULT_ENV) == "during_result_write":
                partial = result_path.with_name(f".{result_path.name}.{uuid4().hex}.tmp")
                partial.write_bytes(raw[: len(raw) // 2])
                fault("during_result_write")
            atomic_write(result_path, raw)
        fault("after_result_write")
        stored = self.result_store.store(result, result_path)
        fault("after_result_store")
        self.journal.transition(experiment_id, "RESULT_STORED", detail=stored["status"])
        self.admission_store.mark_terminal(request_id, result["result_id"])
        self.journal.transition(experiment_id, "COMPLETED", detail="logical execution completed")
        return {
            "status": "RESULT" if stored["status"] == "stored" else "DUPLICATE",
            "result": self.result_store.read_by_request(request_id),
            "experiment_id": experiment_id,
        }

    def _check_integrity(self, experiment_id, recorded, effect_path, result_path):
        if recorded["effect_hash"] and not effect_path.exists():
            self.journal.transition(
                experiment_id,
                "RECONCILIATION_REQUIRED",
                error="effect metadata exists without immutable bytes",
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_BYTES_MISSING")
        if (
            recorded["effect_hash"]
            and effect_path.exists()
            and _sha(effect_path) != recorded["effect_hash"]
        ):
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="effect hash mismatch"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "EFFECT_HASH_MISMATCH")
        # A journaled result hash without bytes is the intent-before-write crash window:
        # the deterministic result is regenerated and must match that hash (see execute).
        if (
            recorded["result_hash"]
            and result_path.exists()
            and _sha(result_path) != recorded["result_hash"]
        ):
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="result hash mismatch"
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "RESULT_HASH_MISMATCH")

    def _ops_success_record(self, logical_hash: str) -> dict:
        records = [
            r
            for r in ops_terminal_records(self.ops_root, "crypto-research-" + logical_hash[:24])
            if r.get("run_status") == "SUCCEEDED"
        ]
        if not records:
            raise ExecutionError("RECONCILIATION_REQUIRED", "OPS_SUCCESS_RECEIPT_MISSING")
        if len(records) > 1:
            raise ExecutionError("RECONCILIATION_REQUIRED", "OPS_REPORTS_MORE_THAN_ONE_SUCCESS")
        return records[0]

    def _core_trial(self, effect: dict, trial_path: Path, experiment_id: str) -> dict | None:
        if effect.get("trial") is None:
            if trial_path.exists():
                raise ExecutionError(
                    "RECONCILIATION_REQUIRED", "TRIAL_REGISTERED_WITHOUT_EFFECT_TRIAL"
                )
            return None
        rows = [
            row
            for row in TrialRegistryV2(trial_path).load()
            if row["trial_id"] == effect["trial"]["trial_id"]
        ]
        if (
            len(rows) != 1
            or rows[0] != effect["trial"]
            or rows[0]["experiment_id"] != experiment_id
        ):
            self.journal.transition(
                experiment_id,
                "RECONCILIATION_REQUIRED",
                error="Core trial registry disagrees with effect",
            )
            raise ExecutionError("RECONCILIATION_REQUIRED", "CORE_TRIAL_MISMATCH")
        return rows[0]

    def _result(
        self,
        context,
        experiment_id,
        logical_hash,
        effect,
        effect_hash,
        core_trial,
        ops_record,
        attempts,
        materialization_hash,
        produced_at,
    ) -> dict:
        request, receipt = context["request"], context["receipt"]
        scientific = core_trial["status"] if core_trial is not None else effect["scientific_state"]
        if core_trial is not None and scientific != effect["scientific_state"]:
            raise ExecutionError("RECONCILIATION_REQUIRED", "CORE_STATE_DISAGREES_WITH_EFFECT")
        attempt_ids = [item["attempt_id"] for item in attempts]
        ops_run_ids = [item["ops_run_id"] for item in attempts if item["ops_run_id"]]
        result = {
            "schema_version": RESULT_SCHEMA,
            "result_id": "crypto:RESULT-" + logical_hash[:32],
            "request_id": request["request_id"],
            "admission_id": receipt["admission_id"],
            "experiment_id": experiment_id,
            "research_id": request["research_id"],
            "hypothesis_id": request["hypothesis_id"],
            "result_state": effect["result_state"],
            "operational_state": "SUCCEEDED",
            "scientific_state": scientific,
            "economic_state": effect["economic_state"],
            "capital_permission": False,
            "produced_at": produced_at,
            "core_facts": {
                "identity": self.identities["core"],
                "trial_ids": [core_trial["trial_id"]] if core_trial else [],
                "trial_registry": "predictor_core.contracts.trial_v2.TrialRegistryV2",
                "scientific_state_source": "core_trial_registry"
                if core_trial
                else "not_evaluated_by_core",
                "trial_row_hash": content_hash(core_trial) if core_trial else None,
                "dataset_fingerprint": core_trial["dataset_hash"] if core_trial else None,
                "temporal_validation": effect["temporal_validation"],
                "statistics": (core_trial or {}).get("result"),
            },
            "ops_facts": {
                "identity": self.identities["ops"],
                "job_id": ops_record["job_id"],
                "economic_lock_id": ops_record.get("economic_lock_id"),
                "ops_run_id": ops_record["run_id"],
                "ops_run_ids": ops_run_ids,
                "attempt_ids": attempt_ids,
                "attempts": len(attempts),
                "retry_count": ops_record.get("retry_count"),
                "operational_state": ops_record["run_status"],
                "started_at": ops_record["started_at"],
                "finished_at": ops_record["finished_at"],
                "exit_code": ops_record["exit_code"],
                "heartbeat_at": ops_record.get("heartbeat_at"),
                "ops_record_hash": content_hash(ops_record),
            },
            "domain_facts": {
                "identity": self.identities["crypto"],
                "handler": receipt["admitted_handler"],
                "dataset_identity": self._content(receipt, "dataset"),
                "model_identity": self._content(receipt, "protocol"),
                "cost_model_identity": self._content(receipt, "cost_model"),
                "baseline_identity": self._content(receipt, "baseline"),
                "evidence_identity": self._content(receipt, "evidence"),
                "data_cutoff": effect["data_cutoff"],
                "data_quality": effect["data_quality"],
                "metrics": effect["metrics"],
                "costs": effect["costs"],
                "baseline_comparison": effect["baseline_comparison"],
                "placebo_seed": effect["placebo_seed"],
                "effect_sha256": effect_hash,
            },
            "provenance": {
                "request_content_hash": context["request_content_hash"],
                "admission_policy_id": receipt["policy_id"],
                "admission_policy_version": receipt["policy_version"],
                "admission_policy_hash": receipt["policy_hash"],
                "resolved_references_hash": content_hash(receipt["resolved_references"]),
                "handler_identity": receipt["admitted_handler"],
                "logical_experiment_hash": logical_hash,
                "reference_materialization_receipt_hash": materialization_hash,
                "journal_identity": content_hash(
                    {"experiment_id": experiment_id, "attempt_ids": attempt_ids}
                ),
            },
        }
        return validate_result(result)

    def _terminal_failure(
        self, context, experiment_id, logical_hash, attempts, materialization_hash
    ) -> dict:
        request, receipt = context["request"], context["receipt"]
        result = {
            "schema_version": RESULT_SCHEMA,
            "result_id": "crypto:RESULT-" + logical_hash[:32],
            "request_id": request["request_id"],
            "admission_id": receipt["admission_id"],
            "experiment_id": experiment_id,
            "research_id": request["research_id"],
            "hypothesis_id": request["hypothesis_id"],
            "result_state": "FAILED_OPERATIONAL",
            "operational_state": "FAILED",
            "scientific_state": "NOT_EVALUATED",
            "economic_state": "NOT_EVALUATED",
            "capital_permission": False,
            "produced_at": _now(),
            "core_facts": {"identity": self.identities["core"], "trial_ids": []},
            "ops_facts": {
                "identity": self.identities["ops"],
                "ops_run_ids": [item["ops_run_id"] for item in attempts if item["ops_run_id"]],
                "attempt_ids": [item["attempt_id"] for item in attempts],
                "attempts": len(attempts),
                "attempt_errors": [item["error"] for item in attempts],
                "retry_budget": receipt["resource_budget"]["max_retries"],
            },
            "domain_facts": {
                "identity": self.identities["crypto"],
                "handler": receipt["admitted_handler"],
            },
            "provenance": {
                "request_content_hash": context["request_content_hash"],
                "admission_policy_hash": receipt["policy_hash"],
                "resolved_references_hash": content_hash(receipt["resolved_references"]),
                "logical_experiment_hash": logical_hash,
                "reference_materialization_receipt_hash": materialization_hash,
            },
        }
        validate_result(result)
        work = self._work(logical_hash)
        result_path = work / "research-result.json"
        if not result_path.exists():
            atomic_write(result_path, canonical(result))
        else:
            result = _json(result_path)
        self.journal.transition(
            experiment_id,
            "RESULT_CREATED",
            detail="retry budget exhausted",
            result_hash=_sha(result_path),
        )
        stored = self.result_store.store(result, result_path)
        self.journal.transition(experiment_id, "RESULT_STORED", detail=stored["status"])
        self.admission_store.mark_terminal(request["request_id"], result["result_id"])
        self.journal.transition(experiment_id, "COMPLETED", detail="terminal operational failure")
        return {
            "status": "RESULT",
            "result": self.result_store.read_by_request(request["request_id"]),
            "experiment_id": experiment_id,
        }

    @staticmethod
    def _content(receipt: dict, kind: str) -> dict:
        ref = next(item for item in receipt["resolved_references"] if item["kind"] == kind)
        return {
            "name": ref["name"],
            "version": ref["version"],
            "revision_id": ref["revision_id"],
            "content_hash": ref["content_hash"],
        }

    def reconcile(self) -> list[dict]:
        return reconcile_execution(self.root, self.result_store)


def reconcile_execution(root: str | Path, result_store) -> list[dict]:
    """Read-only integrity findings over the journal, experiment files and result store."""
    root = Path(root)
    findings: list[dict] = []
    journal_path = root / "journal.sqlite"
    rows = []
    if journal_path.exists():
        with ExperimentJournal(journal_path).connection() as db:
            rows = [dict(r) for r in db.execute("SELECT * FROM experiments").fetchall()]
    for row in rows:
        work = experiment_dir(root, row["logical_hash"])
        effect, result = work / "domain-effect.json", work / "research-result.json"
        eid = row["experiment_id"]
        if effect.exists() and row["effect_hash"] and _sha(effect) != row["effect_hash"]:
            findings.append({"experiment_id": eid, "finding": "EFFECT_HASH_MISMATCH"})
        elif row["effect_hash"] and not effect.exists():
            findings.append({"experiment_id": eid, "finding": "EFFECT_MISSING_BYTES"})
        elif effect.exists() and not row["effect_hash"] and row["state"] != "REFUSED":
            findings.append({"experiment_id": eid, "finding": "ORPHAN_EFFECT_RECOVERABLE"})
        if result.exists() and row["result_hash"] and _sha(result) != row["result_hash"]:
            findings.append({"experiment_id": eid, "finding": "RESULT_HASH_MISMATCH"})
        elif row["state"] == "COMPLETED" and not result.exists():
            findings.append({"experiment_id": eid, "finding": "RESULT_MISSING_BYTES"})
        if row["state"] == "COMPLETED":
            with result_store.connection() as db:
                indexed = db.execute(
                    "SELECT 1 FROM results WHERE experiment_id=?", (eid,)
                ).fetchone()
            if indexed is None:
                findings.append({"experiment_id": eid, "finding": "RESULT_MISSING_FROM_INDEX"})
        if row["state"] == "RECONCILIATION_REQUIRED":
            findings.append(
                {"experiment_id": eid, "finding": "RECONCILIATION_REQUIRED", "error": row["error"]}
            )
    findings.extend(result_store.reconcile())
    return findings


__all__ = [
    "ExecutionError",
    "ExperimentJournal",
    "ReferenceStore",
    "ResearchExecutor",
    "FAULT_POINTS",
    "reconcile_execution",
    "experiment_dir",
    "EXEC_DIR",
    "EXPERIMENTS_DIR",
    "OPS_DIR",
    "MAX_STATE_ROOT_CHARS",
    "FAULT_ENV",
    "FAULT_EXIT",
    "fault",
    "digest",
]
