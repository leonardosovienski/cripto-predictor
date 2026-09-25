"""Pré-registro de hipótese NOVA, gravado no ledger ANTES do primeiro backtest (Prompt 4, item 4).

O template exige: ID imutável, descrição, mecanismo esperado, features, target, período,
universo, custos, protocolo de validação, métrica primária, métricas secundárias, limiares da
política (id, versão e sha256), número máximo de variantes, seeds, definição do holdout e
critérios de GO, NO_GO e NO_DECISION. Um ID já registrado nunca é reescrito: mudar qualquer
coisa é hipótese nova, e ela conta no N de tentativas do DSR.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from GarimpoInvestimentos.research.holdout import HoldoutError, assert_outside_holdouts
from GarimpoInvestimentos.run_ledger import RunLedger, canonical_sha256

PREREGISTERED = "PREREGISTERED"
REQUIRED_FIELDS = (
    "id",
    "description",
    "expected_mechanism",
    "features",
    "target",
    "period",
    "universe",
    "costs",
    "validation_protocol",
    "primary_metric",
    "secondary_metrics",
    "policy",
    "max_variants",
    "seeds",
    "holdout",
    "criteria",
)
_CRITERIA = ("GO", "NO_GO", "NO_DECISION")


class PreregistrationError(ValueError):
    """Pré-registro incompleto, duplicado ou fora de ordem: o backtest não pode começar."""


def validate_preregistration(document: Mapping[str, Any]) -> list[str]:
    problems = [f"campo ausente ou vazio: {k}" for k in REQUIRED_FIELDS if not document.get(k)]
    policy = document.get("policy") or {}
    if isinstance(policy, Mapping):
        problems += [f"policy sem {k}" for k in ("id", "version", "sha256") if not policy.get(k)]
    else:
        problems.append("policy deve ter id, version e sha256")
    max_variants = document.get("max_variants")
    if max_variants is not None and (
        isinstance(max_variants, bool) or not isinstance(max_variants, int) or max_variants < 1
    ):
        problems.append("max_variants deve ser inteiro >= 1")
    criteria = document.get("criteria") or {}
    if isinstance(criteria, Mapping):
        problems += [f"criteria sem {k}" for k in _CRITERIA if not criteria.get(k)]
    else:
        problems.append("criteria deve definir GO, NO_GO e NO_DECISION")
    if document.get("period") and development_period(document) is None:
        problems.append("period.development deve ser [início, fim] em ISO-8601 UTC, início < fim")
    return problems


def development_period(document: Mapping[str, Any]) -> tuple[str, str] | None:
    period = document.get("period")
    development = period.get("development") if isinstance(period, Mapping) else None
    if not (isinstance(development, list | tuple) and len(development) == 2):
        return None
    start, end = development
    try:
        if _utc(start) >= _utc(end):
            return None
    except (TypeError, ValueError):
        return None
    return str(start), str(end)


def _utc(value: Any) -> datetime:
    return datetime.fromisoformat(str(value).removesuffix("Z")).replace(tzinfo=UTC)


def register_preregistration(
    ledger: RunLedger, document: Mapping[str, Any], *, holdouts: RunLedger | None = None
) -> dict:
    """Grava o pré-registro. Com `holdouts`, recusa desenvolvimento que toque holdout selado."""
    problems = validate_preregistration(document)
    if problems:
        raise PreregistrationError("; ".join(problems))
    if holdouts is not None:
        period = development_period(document)
        if period is None:
            raise PreregistrationError("sem period.development não há como conferir os holdouts")
        try:
            assert_outside_holdouts(holdouts, period)
        except HoldoutError as exc:
            raise PreregistrationError(str(exc)) from exc
    if any(
        r.get("status") == PREREGISTERED and r.get("preregistration_id") == document["id"]
        for r in ledger.records()
    ):
        raise PreregistrationError(f"ID já registrado e imutável: {document['id']}")
    return ledger.append(
        {
            "status": PREREGISTERED,
            "preregistration_id": document["id"],
            "registered_at_utc": datetime.now(UTC).isoformat(),
            "preregistration_sha256": canonical_sha256(dict(document)),
            "preregistration": dict(document),
        }
    )


def count_preregistered(ledger: RunLedger) -> int:
    """Hipóteses distintas pré-registradas: cada uma conta como tentativa no N do DSR."""
    return len(
        {
            r["preregistration_id"]
            for r in ledger.records()
            if r.get("status") == PREREGISTERED and r.get("preregistration_id")
        }
    )


def require_preregistered_before_run(ledger: RunLedger, preregistration_id: str) -> dict:
    """Chame antes do primeiro backtest: sem registro no ledger, não há backtest."""
    for record in ledger.records():
        if (
            record.get("status") == PREREGISTERED
            and record.get("preregistration_id") == preregistration_id
        ):
            return record
    raise PreregistrationError(f"sem pré-registro no ledger: {preregistration_id}")
