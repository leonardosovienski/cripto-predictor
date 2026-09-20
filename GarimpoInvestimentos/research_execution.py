"""Recoverable CRIPTO-owned execution adapter for admitted research tasks."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import stat
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from predictor_ops import JobConfig, JobType, RunStatus, run_job
from predictor_ops.models import RuntimeConfig
from research_protocol import canonical, digest, validate_result

from GarimpoInvestimentos.durable_io import atomic_write, strict_json_loads

HANDLER = "crypto.handlers.backtest_existing_hypothesis.v1"
STATES = (
    "PLANNED", "MATERIALIZED", "SCHEDULED", "RUNNING", "DOMAIN_EFFECT_COMMITTED",
    "MEASURED", "RESULT_CREATED", "RESULT_ENQUEUED", "COMPLETED", "FAILED",
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


class ReferenceStore:
    """Operator-owned immutable objects; task references only select registry hashes."""

    def __init__(self, root: str | Path, *, max_bytes: int = 8 * 1024 * 1024):
        self.root = Path(root).resolve()
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def object_path(self, content_hash: str) -> Path:
        if not _HASH.fullmatch(content_hash):
            raise ValueError("invalid content hash")
        return self.root / content_hash[:2] / content_hash

    def put_operator_bytes(self, raw: bytes) -> str:
        """Administrative provisioning boundary; never called from task payload data."""
        if not raw or len(raw) > self.max_bytes:
            raise ValueError("operator object size denied")
        strict_json_loads(raw.decode("utf-8"))
        content_hash = hashlib.sha256(raw).hexdigest()
        target = self.object_path(content_hash)
        if target.exists():
            if _sha(target) != content_hash:
                raise ValueError("operator object corruption")
            return content_hash
        atomic_write(target, raw)
        target.chmod(stat.S_IREAD)
        return content_hash

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
            if not source.exists() or source.is_symlink() or getattr(source, "is_junction", lambda: False)():
                raise FileNotFoundError("admitted reference object unavailable")
            resolved = source.resolve(strict=True)
            if not resolved.is_relative_to(self.root) or not resolved.is_file():
                raise PermissionError("reference object escapes operator store")
            size = resolved.stat().st_size
            if size <= 0 or size > self.max_bytes or _sha(resolved) != expected:
                raise ValueError("reference size/hash verification failed")
            strict_json_loads(resolved.read_text(encoding="utf-8"))
            target = destination / f"{kind}.json"
            if target.exists() and _sha(target) != expected:
                raise ValueError("materialized reference conflict")
            if not target.exists():
                shutil.copyfile(resolved, target)
                target.chmod(stat.S_IREAD)
            if _sha(target) != expected:
                raise ValueError("materialized reference changed")
            materialized.append({**reference, "path": str(target), "size": size})
        return materialized


class ExperimentJournal:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS experiments(
                  experiment_id TEXT PRIMARY KEY, task_id TEXT NOT NULL UNIQUE,
                  logical_hash TEXT NOT NULL, state TEXT NOT NULL,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                  effect_path TEXT, effect_hash TEXT, result_path TEXT, result_hash TEXT,
                  ops_run_id TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS transitions(
                  experiment_id TEXT NOT NULL, sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  state TEXT NOT NULL, recorded_at TEXT NOT NULL, detail TEXT
                );
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

    def ensure(self, experiment_id: str, task_id: str, logical_hash: str) -> dict:
        now = _now()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM experiments WHERE task_id=?", (task_id,)).fetchone()
            if row:
                if row["experiment_id"] != experiment_id or row["logical_hash"] != logical_hash:
                    raise ValueError("EXPERIMENT_CONFLICT")
                return dict(row)
            db.execute(
                "INSERT INTO experiments(experiment_id,task_id,logical_hash,state,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?)", (experiment_id, task_id, logical_hash, "PLANNED", now, now)
            )
            db.execute(
                "INSERT INTO transitions(experiment_id,state,recorded_at,detail) VALUES(?,?,?,?)",
                (experiment_id, "PLANNED", now, "admitted logical identity"),
            )
        return self.get(experiment_id)

    def transition(self, experiment_id: str, state: str, *, detail: str = "", **fields) -> dict:
        if state not in STATES or set(fields) - {
            "effect_path", "effect_hash", "result_path", "result_hash", "ops_run_id", "error"
        }:
            raise ValueError("invalid journal transition")
        now = _now()
        assignments = ["state=?", "updated_at=?"] + [f"{key}=?" for key in fields]
        values = [state, now, *fields.values(), experiment_id]
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone() is None:
                raise ValueError("unknown experiment")
            db.execute(f"UPDATE experiments SET {','.join(assignments)} WHERE experiment_id=?", values)
            db.execute(
                "INSERT INTO transitions(experiment_id,state,recorded_at,detail) VALUES(?,?,?,?)",
                (experiment_id, state, now, detail[:1000]),
            )
        return self.get(experiment_id)

    def get(self, experiment_id: str) -> dict:
        with self.connection() as db:
            row = db.execute("SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)).fetchone()
        return dict(row) if row else None


class ResearchExecutor:
    def __init__(
        self, root: str | Path, *, admission_store, result_outbox, reference_store: ReferenceStore,
        crypto_source_sha: str, artifact_identities: dict[str, dict], python_executable: str | None = None,
    ):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.admission_store = admission_store
        self.result_outbox = result_outbox
        self.references = reference_store
        self.crypto_source_sha = crypto_source_sha
        self.identities = artifact_identities
        self.python = python_executable or sys.executable
        self.journal = ExperimentJournal(self.root / "journal.sqlite")

    @staticmethod
    def logical_identity(context: dict) -> tuple[str, str]:
        receipt, task = context["receipt"], context["task"]
        logical_hash = digest(canonical({
            "task_id": task["task_id"], "admission_id": receipt["admission_id"],
            "handler": receipt["admitted_handler"], "parameters": task["bounded_parameters"],
            "references": receipt["resolved_references"],
        }))
        return "EXP-" + logical_hash[:32], logical_hash

    def _result(self, context: dict, experiment_id: str, effect: dict, effect_path: Path, run) -> dict:
        task, receipt = context["task"], context["receipt"]
        produced_at = _now()
        started = run.record["started_at"]
        finished = run.record["finished_at"]
        result = {
            "schema_version": "ResearchResultV1",
            "result_id": "RESULT-" + experiment_id.removeprefix("EXP-"),
            "task_id": task["task_id"], "admission_id": receipt["admission_id"],
            "research_id": task["research_id"], "hypothesis_id": task["hypothesis_id"],
            "experiment_id": experiment_id, "result_envelope_state": "PRODUCED",
            "envelope_failure_reason": None, "produced_at": produced_at,
            "core_facts": {
                "identity": self.identities["core"], "trial_ids": [effect["trial"]["trial_id"]],
                "scientific_state": effect["scientific_state"], "temporal_integrity": "PASS",
                "statistics_receipt_hash": digest(
                    json.dumps(
                        effect["trial"]["result"], sort_keys=True, separators=(",", ":"),
                        allow_nan=False,
                    ).encode()
                ),
            },
            "ops_facts": {
                "identity": self.identities["ops"], "ops_run_ids": [run.run_id],
                "operational_state": run.run_status.value, "started_at": started,
                "finished_at": finished, "exit_code": run.exit_code,
                "runtime_provenance_hash": digest(canonical(run.record)),
            },
            "crypto_facts": {
                "identity": self.identities["crypto"],
                "dataset_identity": self._content(receipt, "dataset"),
                "model_identity": self._content(receipt, "protocol"),
                "feature_set_identity": self._content(receipt, "evidence"),
                "data_cutoff": effect["data_cutoff"], "metrics": effect["metrics"],
                "baseline_comparison": effect["baseline_comparison"], "costs": effect["costs"],
                "economic_state": effect["economic_state"],
                "artifacts": [{
                    "artifact_id": "ARTIFACT-" + experiment_id.removeprefix("EXP-"),
                    "role": "domain_effect", "sha256": _sha(effect_path),
                    "media_type": "application/json", "size": effect_path.stat().st_size,
                }],
            },
            "provenance": {
                "task_payload_hash": context["task_payload_hash"],
                "admission_policy_hash": receipt["policy_hash"],
                "resolved_references_hash": digest(canonical(receipt["resolved_references"])),
                "crypto_source_sha": self.crypto_source_sha,
            },
        }
        return validate_result(result)

    @staticmethod
    def _content(receipt: dict, kind: str) -> dict:
        ref = next(item for item in receipt["resolved_references"] if item["kind"] == kind)
        return {"name": ref["name"], "version": ref["version"], "content_hash": ref["content_hash"]}

    def execute(self, task_id: str, *, crash_at: str | None = None) -> dict:
        revalidated = self.admission_store.revalidate(task_id)
        if revalidated["decision"] != "ACCEPTED":
            raise PermissionError(f"EXECUTION_DENIED: {revalidated['reason_code']}")
        context = self.admission_store.admitted_context(task_id)
        if context["receipt"]["admitted_handler"] != HANDLER:
            raise PermissionError("EXECUTION_DENIED: handler not compiled")
        experiment_id, logical_hash = self.logical_identity(context)
        row = self.journal.ensure(experiment_id, task_id, logical_hash)
        work = self.root / "experiments" / experiment_id
        refs_dir, effect_path = work / "references", work / "domain-effect.json"
        result_path, trial_path = work / "research-result.json", work / "trials-v2.json"
        materialized = self.references.materialize(context["receipt"]["resolved_references"], refs_dir)
        if row["state"] == "PLANNED":
            self.journal.transition(experiment_id, "MATERIALIZED", detail="all admitted hashes verified")
        registered_at = self.journal.get(experiment_id)["created_at"]
        request = {
            "schema": "crypto-admitted-backtest/1", "experiment_id": experiment_id,
            "trial_id": "TRIAL-" + logical_hash[:32], "task": context["task"],
            "references": [{"kind": item["kind"], "path": item["path"]} for item in materialized],
            "identities": {item["kind"]: item["content_hash"] for item in materialized},
            "registered_at": registered_at, "code_version": f"crypto:{self.crypto_source_sha}",
        }
        request_path = work / "worker-request.json"
        raw_request = json.dumps(request, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if request_path.exists() and request_path.read_bytes() != raw_request:
            raise ValueError("worker request conflict")
        if not request_path.exists():
            atomic_write(request_path, raw_request)
        if crash_at == "after_persist":
            raise RuntimeError("INJECTED_CRASH_AFTER_PERSIST")

        recorded = self.journal.get(experiment_id)
        if recorded["effect_hash"] and effect_path.exists() and _sha(effect_path) != recorded["effect_hash"]:
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="effect hash mismatch"
            )
            raise ValueError("domain effect hash mismatch")
        if recorded["effect_hash"] and not effect_path.exists():
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED",
                error="effect metadata exists without immutable bytes",
            )
            raise ValueError("domain effect bytes missing")
        if recorded["result_hash"] and not result_path.exists():
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED",
                error="result metadata exists without immutable bytes",
            )
            raise ValueError("result bytes missing")
        if recorded["result_hash"] and result_path.exists() and _sha(result_path) != recorded["result_hash"]:
            self.journal.transition(
                experiment_id, "RECONCILIATION_REQUIRED", error="result hash mismatch"
            )
            raise ValueError("research result hash mismatch")

        run = None
        if not effect_path.exists():
            self.journal.transition(experiment_id, "SCHEDULED", detail="static worker selected")
            command = [
                self.python, "-m", "GarimpoInvestimentos.research_worker",
                "--request", str(request_path), "--effect", str(effect_path),
                "--trial-registry", str(trial_path),
            ]
            if crash_at == "runner_crash":
                command.extend(["--fault", "crash"])
            elif crash_at == "runner_timeout":
                command.extend(["--fault", "hang"])
            config = JobConfig(
                id="research-" + logical_hash[:24],
                command=command,
                cwd=Path(__file__).resolve().parents[1],
                timeout_seconds=context["receipt"]["resource_budget"]["timeout_seconds"],
                expected_artifact=effect_path,
                provenance={"admission_id": context["receipt"]["admission_id"], "logical_hash": logical_hash},
                input_reference=digest(raw_request), output_reference=str(effect_path),
                scientific_state="ACTIVE", job_type=JobType.SHADOW_DECISION,
                capital_permission=False, runtime=RuntimeConfig(root=self.root / "ops-runtime"),
            )
            self.journal.transition(experiment_id, "RUNNING", detail="delegated to predictor_ops")
            run = run_job(config)
            if run.run_status is not RunStatus.SUCCEEDED:
                self.journal.transition(experiment_id, "FAILED", detail="OPS execution failed", error=str(run.record))
                raise RuntimeError(f"OPS_EXECUTION_FAILED: {run.run_status}")
            if crash_at == "after_domain_effect":
                raise RuntimeError("INJECTED_CRASH_AFTER_DOMAIN_EFFECT")
            self.journal.transition(
                experiment_id, "DOMAIN_EFFECT_COMMITTED", detail="immutable effect verified",
                effect_path=str(effect_path), effect_hash=_sha(effect_path), ops_run_id=run.run_id,
            )
        else:
            effect_hash = _sha(effect_path)
            recorded = self.journal.get(experiment_id)
            if recorded["effect_hash"] and recorded["effect_hash"] != effect_hash:
                self.journal.transition(experiment_id, "RECONCILIATION_REQUIRED", error="effect hash mismatch")
                raise ValueError("domain effect hash mismatch")
            if not trial_path.exists():
                self.journal.transition(experiment_id, "RECONCILIATION_REQUIRED", error="trial registry missing")
                raise ValueError("trial registry missing")
            self.journal.transition(
                experiment_id, "DOMAIN_EFFECT_COMMITTED", detail="reconciled committed effect",
                effect_path=str(effect_path), effect_hash=effect_hash,
            )
        effect = _json(effect_path)
        self.journal.transition(experiment_id, "MEASURED", detail="causal domain output loaded")

        if result_path.exists():
            result = _json(result_path)
        else:
            if run is None:
                events = self.root / "ops-runtime" / ("research-" + logical_hash[:24]) / "events.jsonl"
                if not events.exists():
                    raise ValueError("OPS receipt missing during reconciliation")
                lines = [line for line in events.read_text(encoding="utf-8").splitlines() if line.strip()]
                record = strict_json_loads(lines[-1])
                if not isinstance(record, dict) or record.get("run_status") != "SUCCEEDED":
                    raise ValueError("OPS terminal receipt invalid during reconciliation")
                run = SimpleNamespace(
                    run_id=record["run_id"], run_status=RunStatus(record["run_status"]),
                    exit_code=record["exit_code"], record=record,
                )
            result = self._result(context, experiment_id, effect, effect_path, run)
            atomic_write(result_path, canonical(result))
        self.journal.transition(
            experiment_id, "RESULT_CREATED", detail="ResearchResultV1 validated",
            result_path=str(result_path), result_hash=_sha(result_path),
        )
        if crash_at == "after_result":
            raise RuntimeError("INJECTED_CRASH_AFTER_RESULT")
        produced = self.result_outbox.produce(result)
        self.journal.transition(experiment_id, "RESULT_ENQUEUED", detail=produced["status"])
        self.journal.transition(experiment_id, "COMPLETED", detail="logical execution completed")
        return {"experiment": self.journal.get(experiment_id), "result": result, "outbox": produced}

    def reconcile(self) -> list[dict]:
        findings = []
        with self.journal.connection() as db:
            rows = db.execute("SELECT * FROM experiments").fetchall()
        for raw in rows:
            row = dict(raw)
            effect = Path(row["effect_path"]) if row["effect_path"] else self.root / "experiments" / row["experiment_id"] / "domain-effect.json"
            result = Path(row["result_path"]) if row["result_path"] else self.root / "experiments" / row["experiment_id"] / "research-result.json"
            if effect.exists() and row["effect_hash"] and _sha(effect) != row["effect_hash"]:
                findings.append({"experiment_id": row["experiment_id"], "finding": "HASH_MISMATCH"})
            elif row["effect_hash"] and not effect.exists():
                findings.append({"experiment_id": row["experiment_id"], "finding": "MISSING_BYTES"})
            elif effect.exists() and not row["effect_hash"]:
                findings.append({"experiment_id": row["experiment_id"], "finding": "ORPHAN_EFFECT_RECOVERABLE"})
            if result.exists() and row["result_hash"] and _sha(result) != row["result_hash"]:
                findings.append({"experiment_id": row["experiment_id"], "finding": "RESULT_HASH_MISMATCH"})
            elif row["result_hash"] and not result.exists():
                findings.append({"experiment_id": row["experiment_id"], "finding": "RESULT_MISSING_BYTES"})
            elif result.exists() and not row["result_hash"]:
                findings.append({"experiment_id": row["experiment_id"], "finding": "ORPHAN_RESULT_RECOVERABLE"})
        return findings


__all__ = ["ExperimentJournal", "ReferenceStore", "ResearchExecutor"]
