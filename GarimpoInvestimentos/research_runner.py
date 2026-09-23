"""`cripto-research`: composition root of the crypto research circuit (file requests).

    request file -> admission (AdmissionStore, operator policy) -> reference materialization
    (ReferenceStore) -> handler from the compiled allowlist run as a real predictor_ops job
    -> predictor_core trial/temporal validation -> ResultStore (authoritative)

Commands (all take --state DIR; process/run also --policy FILE --objects DIR):
    process FILE...        submit and execute each request file, in order
    run --inbox DIR        process every *.json in DIR (sorted by name)
    show REQUEST_ID        re-read the authoritative result (never recomputed)
    reconcile              report journal/result integrity findings (read-only)
    backup --out DIR       consistent recovery bundle of the state (never mutates the source)
    restore --bundle B --into DIR   restore a bundle into a new, empty directory
    put-object FILE        operator provisioning of an immutable reference object

Each submission writes one outcome file to <state>/outcomes/ and prints it as one JSON
line. Exit code: the highest of the per-request codes in research_contract.EXIT_CODES
(0 result/duplicate, 2 rejected/conflict, 3 not ready/retryable Ops failure,
4 temporal integrity violation, 5 reconciliation required).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from GarimpoInvestimentos.durable_io import atomic_write
from GarimpoInvestimentos.research_admission import AdmissionStore
from GarimpoInvestimentos.research_contract import (
    EXIT_CODES,
    OUTCOME_SCHEMA,
    ContractError,
    canonical,
    digest,
    loads_strict,
)
from GarimpoInvestimentos.research_execution import (
    ExecutionError,
    ReferenceStore,
    ResearchExecutor,
)
from GarimpoInvestimentos.research_faults import fault
from GarimpoInvestimentos.research_results import ResultConflict, ResultIntegrityError, ResultStore

MAX_REQUEST_FILE_BYTES = 256 * 1024


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class Circuit:
    """Real composition of the crypto research components for one state root."""

    def __init__(self, state: Path, policy: Path | None = None, objects: Path | None = None):
        self.state = Path(state).resolve()
        self.state.mkdir(parents=True, exist_ok=True)
        self.results = ResultStore(self.state / "results.sqlite")
        self.admission = AdmissionStore(self.state / "admission.sqlite", policy) if policy else None
        self.references = ReferenceStore(objects) if objects else None
        self.executor = (
            ResearchExecutor(
                self.state / "execution",
                admission_store=self.admission,
                result_store=self.results,
                reference_store=self.references,
            )
            if self.admission and self.references
            else None
        )
        self.outcomes = self.state / "outcomes"
        self.outcomes.mkdir(exist_ok=True)

    def _write_outcome(self, outcome: dict) -> dict:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", outcome.get("request_id") or "invalid")
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        path = self.outcomes / f"{safe}.{stamp}.{outcome['submission_sha256'][:12]}.json"
        atomic_write(path, canonical(outcome))
        outcome = outcome | {"outcome_file": str(path)}
        return outcome

    def submit_file(self, path: Path) -> dict:
        """Entrypoint path: a request file placed by the operator."""
        return self.submit_request(Path(path).read_bytes(), source=str(path))

    def submit_request(self, raw: bytes, *, source: str) -> dict:
        """adapter_api (C24.1): request bytes -> outcome, the same path as the entrypoint."""
        admission, executor = self.admission, self.executor
        if admission is None or executor is None:
            raise RuntimeError("processing requires --policy and --objects")
        base = {
            "schema": OUTCOME_SCHEMA,
            "submission_file": source,
            "submission_sha256": digest(raw),
            "at": _now(),
        }
        try:
            if len(raw) > MAX_REQUEST_FILE_BYTES:
                raise ContractError("REQUEST_SIZE_LIMIT", "file larger than the entrypoint bound")
            request = loads_strict(raw)
            receipt = admission.submit(request, size=len(raw))
        except ContractError as exc:
            admission.record_invalid(raw, exc)
            request_id = None
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and isinstance(parsed.get("request_id"), str):
                    request_id = parsed["request_id"][:140]
            except ValueError:
                pass
            return self._finish(
                base
                | {
                    "request_id": request_id,
                    "status": "REJECTED",
                    "reason": exc.reason,
                    "detail": str(exc)[:300],
                }
            )
        client = {"client_ref": request["client_ref"]} if "client_ref" in request else {}
        base = base | {
            "request_id": request["request_id"],
            **client,
            "admission": {k: receipt[k] for k in ("admission_id", "decision", "reason_code")}
            | {"duplicate": bool(receipt.get("duplicate"))},
        }
        if receipt["decision"] == "CONFLICT":
            return self._finish(base | {"status": "CONFLICT", "reason": receipt["reason_code"]})
        if receipt["decision"] != "ACCEPTED":
            return self._finish(base | {"status": "REJECTED", "reason": receipt["reason_code"]})
        fault("after_admission")
        try:
            executed = executor.execute(request["request_id"])
        except ExecutionError as exc:
            detail = {
                "operational_state": exc.detail.get("operational_state", "NOT_RUN"),
                "scientific_state": "NOT_EVALUATED",
                "economic_state": "NOT_EVALUATED",
                **{k: v for k, v in exc.detail.items() if k != "operational_state"},
            }
            return self._finish(base | {"status": exc.status, "reason": exc.reason} | detail)
        except (ResultConflict, ResultIntegrityError) as exc:
            return self._finish(
                base
                | {
                    "status": "RECONCILIATION_REQUIRED",
                    "reason": type(exc).__name__,
                    "detail": str(exc)[:300],
                }
            )
        result = executed["result"]
        # DUPLICATE = the authoritative result already existed; RESULT = produced by this submission
        # (a retry of an admitted request after an operational failure produces it for the first time).
        status = executed["status"]
        return self._finish(
            base
            | {
                "status": status,
                "result_id": result["result_id"],
                "experiment_id": result["experiment_id"],
                "result_state": result["result_state"],
                "operational_state": result["operational_state"],
                "scientific_state": result["scientific_state"],
                "economic_state": result["economic_state"],
                "capital_permission": False,
                "result": result,
            }
        )

    def _finish(self, outcome: dict) -> dict:
        outcome["exit_code"] = EXIT_CODES[outcome["status"]]
        return self._write_outcome(outcome)

    def show(self, request_id: str) -> tuple[int, dict]:
        try:
            result = self.results.read_by_request(request_id)
        except (ResultIntegrityError, ValueError) as exc:
            return 5, {
                "status": "RECONCILIATION_REQUIRED",
                "request_id": request_id,
                "reason": str(exc)[:300],
            }
        if result is None:
            return 3, {"status": "NOT_FOUND", "request_id": request_id}
        return 0, {
            "status": "RESULT",
            "request_id": request_id,
            "source": "authoritative_result_store",
            "result_sha256": digest(canonical(result)),
            "result": result,
        }


def _circuit(args) -> Circuit:
    return Circuit(args.state, getattr(args, "policy", None), getattr(args, "objects", None))


def _route_ops_logs_to_stderr() -> None:
    """stdout carries only outcome lines; predictor_ops structured logs go to stderr."""
    import logging

    from predictor_ops.observability import JsonFormatter

    ops_logger = logging.getLogger("predictor_ops")
    if not ops_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        ops_logger.addHandler(handler)
        ops_logger.setLevel(logging.INFO)
        ops_logger.propagate = False


def main(argv: list[str] | None = None) -> int:
    _route_ops_logs_to_stderr()
    parser = argparse.ArgumentParser(
        prog="cripto-research", description=(__doc__ or "").splitlines()[0]
    )
    parser.add_argument("--state", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("process", "run"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--policy", type=Path, required=True)
        cmd.add_argument("--objects", type=Path, required=True)
        if name == "process":
            cmd.add_argument("files", type=Path, nargs="+")
        else:
            cmd.add_argument("--inbox", type=Path, required=True)
    show = sub.add_parser("show")
    show.add_argument("request_id")
    sub.add_parser("reconcile")
    backup = sub.add_parser("backup")
    backup.add_argument("--out", type=Path, required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("--bundle", type=Path, required=True)
    restore.add_argument("--into", type=Path, required=True)
    put = sub.add_parser("put-object")
    put.add_argument("--objects", type=Path, required=True)
    put.add_argument("file", type=Path)
    args = parser.parse_args(argv)

    if args.command == "put-object":
        object_hash = ReferenceStore(args.objects).put_operator_bytes(args.file.read_bytes())
        print(json.dumps({"object_hash": object_hash}))
        return 0
    if args.command in {"backup", "restore"}:
        from GarimpoInvestimentos.research_recovery import (
            create_recovery_bundle,
            restore_recovery_bundle,
        )

        if args.command == "restore":
            print(json.dumps(restore_recovery_bundle(args.bundle, args.into), sort_keys=True))
            return 0
        state = args.state.resolve()
        databases = {
            name: state / path
            for name, path in (
                ("admission", "admission.sqlite"),
                ("results", "results.sqlite"),
                ("journal", "execution/journal.sqlite"),
            )
            if (state / path).exists()
        }
        roots = {
            name: state / path
            for name, path in (
                ("experiments", "execution/experiments"),
                ("outcomes", "outcomes"),
                ("ops_runtime", "execution/ops-runtime"),
            )
            if (state / path).is_dir()
        }
        manifest = create_recovery_bundle(
            args.out, sqlite_databases=databases, artifact_roots=roots
        )
        print(
            json.dumps({"bundle": str(args.out), "files": len(manifest["files"])}, sort_keys=True)
        )
        return 0
    if args.command == "show":
        code, payload = Circuit(args.state).show(args.request_id)
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        return code
    if args.command == "reconcile":
        from GarimpoInvestimentos.research_execution import reconcile_execution

        circuit = Circuit(args.state)
        findings = reconcile_execution(circuit.state / "execution", circuit.results)
        print(json.dumps({"findings": findings}, sort_keys=True, ensure_ascii=False))
        return 5 if findings else 0

    circuit = _circuit(args)
    files = args.files if args.command == "process" else sorted(args.inbox.glob("*.json"))
    code = 0
    for path in files:
        outcome = circuit.submit_file(path)
        printable = {k: v for k, v in outcome.items() if k != "result"}
        print(json.dumps(printable, sort_keys=True, ensure_ascii=False))
        code = max(code, outcome["exit_code"])
    return code


if __name__ == "__main__":
    sys.exit(main())
