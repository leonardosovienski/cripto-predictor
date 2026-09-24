"""Manifesto de execução + ledger append-only de TODAS as execuções avaliativas.

Cada execução avaliativa grava duas linhas neste ledger, nunca reescritas:

  STARTED    run_id, tipo, código (versão, commit e flag dirty), config e seu sha256,
             custos, protocolo de validação, modelo, seeds, versão da política,
             número da tentativa (quantas vezes esta MESMA config já rodou, +1);
  COMPLETED  dataset (sha256 dos insumos e intervalo temporal), métricas, baselines,
  ou CRASHED tipo e mensagem do erro. Execução ruim ou quebrada também conta.

Cada linha carrega `prev_sha256` (sha256 canônico da linha anterior) e `record_sha256`:
uma alteração ou remoção de linha antiga quebra a cadeia e `verify_chain` acusa.

Dívida técnica registrada: o `predictor_core` 3.2.1 não tem `RunManifest`/`TrialLedger`
nem arquivo de política (pendência do `01-core.md`). Este é o mínimo compatível, sobre o
`JsonlStore` append-only do core; os nomes seguem o `TrialRegistryV2` quando existem.
O `trials.json` legado (artefato protegido da qualificação) NÃO é tocado.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import traceback
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from predictor_core.kernel.jsonl_store import JsonlStore

SCHEMA_VERSION = "cripto-run-manifest/1"
# Execução não governada por política aprovada (a v1 de research/decision_policy.py está
# PROPOSED). A ausência é registrada, nunca inventada.
POLICY_NOT_DEFINED = {"id": None, "version": None, "sha256": None, "status": "NOT_DEFINED"}
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def code_identity(repo: Path | None = None) -> dict[str, Any]:
    """Versão do pacote e, quando roda de um checkout Git, commit e flag dirty."""
    try:
        package_version = version("cripto-predictor")
    except PackageNotFoundError:
        package_version = None
    root = repo or _PACKAGE_ROOT
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return {
            "package_version": package_version,
            "commit": None,
            "dirty": None,
            "source": "installed_package",
        }
    return {
        "package_version": package_version,
        "commit": commit,
        "dirty": dirty,
        "source": "git_checkout",
    }


class RunLedger:
    """Ledger JSONL append-only e encadeado por hash."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._store = JsonlStore(self.path)

    def records(self) -> list[dict]:
        return list(self._store) if self.path.exists() else []

    def attempt_number(self, config_sha256: str) -> int:
        return 1 + sum(
            1
            for r in self.records()
            if r.get("status") == "STARTED" and r.get("config_sha256") == config_sha256
        )

    def append(self, record: Mapping[str, Any]) -> dict:
        previous = self.records()
        entry = {
            **record,
            "schema_version": SCHEMA_VERSION,
            "prev_sha256": previous[-1]["record_sha256"] if previous else None,
        }
        entry["record_sha256"] = canonical_sha256(entry)
        self._store.append(entry)
        return entry

    def verify_chain(self) -> list[str]:
        problems, previous = [], None
        for index, record in enumerate(self.records()):
            body = {k: v for k, v in record.items() if k != "record_sha256"}
            if canonical_sha256(body) != record.get("record_sha256"):
                problems.append(f"linha {index}: record_sha256 não confere (linha alterada)")
            if record.get("prev_sha256") != previous:
                problems.append(f"linha {index}: prev_sha256 não aponta para a linha anterior")
            previous = record.get("record_sha256")
        return problems


@dataclass
class RunRecord:
    """O que a execução preenche antes de terminar (vai na linha COMPLETED)."""

    run_id: str
    dataset: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    baselines: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:12]


@contextmanager
def recorded_run(
    ledger: RunLedger,
    *,
    kind: str,
    config: Mapping[str, Any],
    costs: Mapping[str, Any] | None,
    validation_protocol: Mapping[str, Any],
    model: Mapping[str, Any],
    seeds: list[int] | None,
    policy: Mapping[str, Any] | None = None,
    run_id: str | None = None,
) -> Iterator[RunRecord]:
    """Grava STARTED; depois COMPLETED com o que a execução preencheu, ou CRASHED e re-levanta."""
    config_sha = canonical_sha256(dict(config))
    record = RunRecord(run_id=run_id or new_run_id())
    ledger.append(
        {
            "run_id": record.run_id,
            "kind": kind,
            "status": "STARTED",
            "at_utc": datetime.now(UTC).isoformat(),
            "attempt": ledger.attempt_number(config_sha),
            "code": code_identity(),
            "config": dict(config),
            "config_sha256": config_sha,
            "costs": dict(costs) if costs is not None else None,
            "validation_protocol": dict(validation_protocol),
            "model": dict(model),
            "seeds": list(seeds) if seeds is not None else None,
            "policy": dict(policy) if policy is not None else dict(POLICY_NOT_DEFINED),
        }
    )
    try:
        yield record
    except BaseException as exc:
        ledger.append(
            {
                "run_id": record.run_id,
                "kind": kind,
                "status": "CRASHED",
                "at_utc": datetime.now(UTC).isoformat(),
                "config_sha256": config_sha,
                "dataset": record.dataset,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc)[:500],
                    "where": traceback.format_exception(exc)[-2].strip()[:300]
                    if exc.__traceback__
                    else None,
                },
            }
        )
        raise
    ledger.append(
        {
            "run_id": record.run_id,
            "kind": kind,
            "status": "COMPLETED",
            "at_utc": datetime.now(UTC).isoformat(),
            "config_sha256": config_sha,
            "dataset": record.dataset,
            "metrics": record.metrics,
            "baselines": record.baselines,
            "artifacts": record.artifacts,
        }
    )
