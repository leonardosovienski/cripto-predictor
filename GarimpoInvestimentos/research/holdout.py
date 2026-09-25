"""Holdout selado (Prompt 4, item 5): registro durável, abertura única com aprovação humana.

Ciclo, todo no ledger encadeado por hash (`run_ledger.RunLedger`):
  HOLDOUT_SEALED          intervalo, universo, identificador, momento da selagem, regra do
                          conteúdo e condições objetivas de abertura (o hash do conteúdo, se
                          o dado já existe)
  HOLDOUT_CONTENT_HASHED  para janela futura: o sha256 do conteúdo, gravado uma vez, depois
                          que a janela fecha e ANTES de qualquer abertura
  HOLDOUT_OPENED          uma única vez, com aprovação humana registrada (quem, quando,
                          evidência) e cada condição de abertura atestada. Nunca consultar
                          iterativamente: uma segunda abertura é recusada.

`assert_outside_holdouts` protege o desenvolvimento: um período que toca um holdout selado e
não aberto é recusado.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from GarimpoInvestimentos.run_ledger import RunLedger

SEALED, CONTENT_HASHED, OPENED = "HOLDOUT_SEALED", "HOLDOUT_CONTENT_HASHED", "HOLDOUT_OPENED"


class HoldoutError(RuntimeError):
    """Operação de holdout recusada: selo, hash ou aprovação não conferem."""


def _events(ledger: RunLedger, holdout_id: str) -> list[dict]:
    return [r for r in ledger.records() if r.get("holdout_id") == holdout_id]


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.removesuffix("Z")).replace(tzinfo=UTC)


def holdout_state(ledger: RunLedger, holdout_id: str) -> str:
    statuses = [r["status"] for r in _events(ledger, holdout_id)]
    if OPENED in statuses:
        return "OPENED"
    return "SEALED" if SEALED in statuses else "NOT_SEALED"


def seal_holdout(
    ledger: RunLedger,
    *,
    holdout_id: str,
    universe: str,
    interval_utc: tuple[str, str],
    content_rule: str,
    opening_conditions: Sequence[str],
    content_sha256: str | None = None,
) -> dict:
    if holdout_state(ledger, holdout_id) != "NOT_SEALED":
        raise HoldoutError(f"holdout já selado (ID imutável): {holdout_id}")
    start, end = interval_utc
    if _parse(start) >= _parse(end):
        raise HoldoutError("intervalo do holdout vazio ou invertido")
    if not opening_conditions:
        raise HoldoutError("holdout sem condições objetivas de abertura")
    return ledger.append(
        {
            "status": SEALED,
            "holdout_id": holdout_id,
            "sealed_at_utc": datetime.now(UTC).isoformat(),
            "universe": universe,
            "interval_utc": [start, end],
            "content_rule": content_rule,
            "content_sha256": content_sha256,
            "opening_conditions": list(opening_conditions),
        }
    )


def register_content_hash(ledger: RunLedger, holdout_id: str, content_sha256: str) -> dict:
    events = _events(ledger, holdout_id)
    sealed = next((r for r in events if r["status"] == SEALED), None)
    if sealed is None:
        raise HoldoutError(f"holdout não selado: {holdout_id}")
    if any(r["status"] in (CONTENT_HASHED, OPENED) for r in events) or sealed["content_sha256"]:
        raise HoldoutError("hash do conteúdo já registrado ou holdout já aberto")
    if datetime.now(UTC) < _parse(sealed["interval_utc"][1]):
        raise HoldoutError("a janela do holdout ainda não fechou")
    return ledger.append(
        {"status": CONTENT_HASHED, "holdout_id": holdout_id, "content_sha256": content_sha256}
    )


def open_holdout(
    ledger: RunLedger,
    holdout_id: str,
    *,
    approval: Mapping[str, Any],
    content_sha256: str,
    conditions_met: Mapping[str, str],
) -> dict:
    events = _events(ledger, holdout_id)
    sealed = next((r for r in events if r["status"] == SEALED), None)
    if sealed is None:
        raise HoldoutError(f"holdout não selado: {holdout_id}")
    if any(r["status"] == OPENED for r in events):
        raise HoldoutError("holdout já aberto: nunca consultar iterativamente")
    missing = [k for k in ("approved_by", "approved_at_utc", "evidence") if not approval.get(k)]
    if missing:
        raise HoldoutError(f"abertura sem aprovação humana registrada: falta {missing}")
    expected = sealed["content_sha256"] or next(
        (r["content_sha256"] for r in events if r["status"] == CONTENT_HASHED), None
    )
    if expected is None:
        raise HoldoutError("conteúdo sem hash registrado antes da abertura")
    if content_sha256 != expected:
        raise HoldoutError("conteúdo diferente do que foi selado")
    unmet = [c for c in sealed["opening_conditions"] if not conditions_met.get(c)]
    if unmet:
        raise HoldoutError(f"condições de abertura sem atestado: {unmet}")
    return ledger.append(
        {
            "status": OPENED,
            "holdout_id": holdout_id,
            "opened_at_utc": datetime.now(UTC).isoformat(),
            "approval": dict(approval),
            "content_sha256": content_sha256,
            "conditions_met": dict(conditions_met),
        }
    )


def assert_outside_holdouts(ledger: RunLedger, interval_utc: tuple[str, str]) -> None:
    start, end = (_parse(v) for v in interval_utc)
    for record in ledger.records():
        if record.get("status") != SEALED:
            continue
        if holdout_state(ledger, record["holdout_id"]) == "OPENED":
            continue
        h_start, h_end = (_parse(v) for v in record["interval_utc"])
        if start < h_end and end > h_start:
            raise HoldoutError(f"período de desenvolvimento toca o holdout {record['holdout_id']}")
