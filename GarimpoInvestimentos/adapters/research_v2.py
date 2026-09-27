"""Stage B adapter of the crypto research contract: ResearchTaskV2 → adapter_api → domain outcome.

Loaded by module name by the V2 transport consumer (``predictor-research-consumer``, ecosystem-predictor), which
owns the envelope code: this module has no console script and no dependency on the envelope package, so the frozen
Stage A rules keep holding (tests/conformance/test_import_closure.py; nothing outside ``adapters`` imports it).

What it does, and nothing else:
  * V2 → contract request: the bytes submitted are the canonical form of ``task["payload"]`` (the contract request,
    with the envelope's ``client_ref``), exactly ``research_protocol.v2.request_bytes(task)``;
  * calls the domain only through the adapter_api (``Circuit(state, policy, objects).submit_request`` and
    ``Circuit(state).show``) and returns the domain outcome unchanged; the consumer wraps it into the
    ResearchResultV2 with the normative ``build_result`` and checks byte identity against ``show``;
  * declares its identity for the ``adapter`` field of the envelope (distribution, installed version, module).

The domain decides admission, handler, budget, priority and every state; nothing here grants capital.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.metadata import version
from pathlib import Path
from typing import Any

from GarimpoInvestimentos.research_runner import Circuit

DOMAIN = "crypto"
DISTRIBUTION = "cripto-predictor"
TASK_SCHEMA = "research-task/2"
CLIENT_REF_SCHEMA = "research-client-ref/2"


class AdapterRefusal(ValueError):
    """A task this adapter will not submit (fail closed before the domain sees any byte)."""


def identity() -> dict[str, str]:
    return {"distribution": DISTRIBUTION, "version": version(DISTRIBUTION), "module": __name__}


def request_bytes(task: Mapping[str, Any]) -> bytes:
    """Canonical JSON of the contract request carried by the task (the domain's canonical form)."""
    if task.get("schema") != TASK_SCHEMA or task.get("domain") != DOMAIN:
        raise AdapterRefusal("not a research-task/2 of the crypto domain")
    payload = task.get("payload")
    task_id = task.get("task_id")
    if not isinstance(payload, Mapping) or not isinstance(task_id, str):
        raise AdapterRefusal("task without payload or task_id")
    if payload.get("client_ref") != {"schema": CLIENT_REF_SCHEMA, "task_id": task_id}:
        raise AdapterRefusal("payload.client_ref is not the envelope's client_ref for this task")
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def submit_task(task: Mapping[str, Any], config: Mapping[str, str]) -> dict:
    """adapter_api: the task's request bytes → the domain outcome, the same path as the entrypoint."""
    raw = request_bytes(task)
    circuit = Circuit(Path(config["state"]), Path(config["policy"]), Path(config["objects"]))
    return circuit.submit_request(raw, source=f"research-task-v2:{task['task_id']}")


def reread(request_id: str, config: Mapping[str, str]) -> tuple[int, dict]:
    """The domain's authoritative re-read (never recomputed)."""
    return Circuit(Path(config["state"])).show(request_id)
