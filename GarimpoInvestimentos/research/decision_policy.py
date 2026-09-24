"""Política de decisão versionada: GO / NO_GO / NO_DECISION.

Os limiares vivem SÓ no arquivo de política (`policies/decision_policy_v<N>.json`), nunca
como constantes no código. DÍVIDA TÉCNICA: `predictor_core` 3.2.1 não tem arquivo de
política de decisão; este é local e deve migrar para o core.

Regras:
- ausência de evidência nunca vira GO: qualquer insumo faltando ou não finito → NO_DECISION;
- política que não está APPROVED → NO_DECISION (limiar só vale com aprovação humana);
- hipótese registrada antes de `effective_from_utc` → NO_DECISION (nada é retroativo);
- o DSR decide pelo pior caso entre os cenários de N (N, 2N, 5N… e N_upper) e a pior seed;
- toda decisão carrega id, versão, sha256 e status da política.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from GarimpoInvestimentos.research.strategy_metrics import scenario_label
from GarimpoInvestimentos.run_ledger import RunLedger, canonical_sha256

POLICY_DIR = Path(__file__).resolve().parent / "policies"
CURRENT_POLICY_PATH = POLICY_DIR / "decision_policy_v1.json"

_THRESHOLD_KEYS = (
    "min_seeds",
    "dsr_min",
    "pbo_max_exclusive",
    "required_baselines",
    "require_dataset_sha256",
    "max_missing_fraction",
    "min_oos_observations",
)
_STATUSES = ("PROPOSED", "APPROVED", "RETIRED")


class PolicyError(ValueError):
    """Arquivo de política inválido: nenhuma decisão pode sair dele."""


def _utc(value: Any, field: str) -> datetime:
    try:
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError(value)
        return datetime.fromisoformat(value.removesuffix("Z")).replace(tzinfo=UTC)
    except ValueError as exc:
        raise PolicyError(f"{field}: instante UTC ISO-8601 terminado em Z obrigatório") from exc


@dataclass(frozen=True)
class DecisionPolicy:
    document: Mapping[str, Any]
    sha256: str

    @property
    def status(self) -> str:
        return self.document["status"]

    @property
    def thresholds(self) -> Mapping[str, Any]:
        return self.document["thresholds"]

    @property
    def dsr_scenario_labels(self) -> list[str]:
        return [scenario_label(m) for m in self.document["dsr_n_sensitivity"]["multipliers"]]

    def reference(self) -> dict[str, Any]:
        return {
            "id": self.document["policy_id"],
            "version": self.document["version"],
            "sha256": self.sha256,
            "status": self.status,
        }


def validate_policy(document: Mapping[str, Any]) -> DecisionPolicy:
    if not isinstance(document.get("policy_id"), str) or not document["policy_id"]:
        raise PolicyError("policy_id obrigatório")
    version = document.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise PolicyError("version deve ser inteiro >= 1")
    if document.get("status") not in _STATUSES:
        raise PolicyError(f"status deve ser um de {_STATUSES}")
    thresholds = document.get("thresholds")
    if not isinstance(thresholds, Mapping):
        raise PolicyError("thresholds obrigatório")
    missing = [k for k in _THRESHOLD_KEYS if k not in thresholds]
    if missing:
        raise PolicyError(f"limiares ausentes: {missing}")
    multipliers = document.get("dsr_n_sensitivity", {}).get("multipliers")
    if (
        not isinstance(multipliers, list)
        or 1 not in multipliers
        or any(isinstance(m, bool) or not isinstance(m, int) or m < 1 for m in multipliers)
    ):
        raise PolicyError("dsr_n_sensitivity.multipliers: inteiros >= 1, incluindo 1")
    if document["status"] == "APPROVED":
        approval = document.get("approval") or {}
        if not approval.get("approved_by"):
            raise PolicyError("política APPROVED sem approved_by")
        approved_at = _utc(approval.get("approved_at_utc"), "approval.approved_at_utc")
        if _utc(document.get("effective_from_utc"), "effective_from_utc") < approved_at:
            raise PolicyError("effective_from_utc anterior à aprovação: seria retroativa")
    return DecisionPolicy(document=dict(document), sha256=canonical_sha256(document))


def load_policy(path: Path | str = CURRENT_POLICY_PATH) -> DecisionPolicy:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"política ilegível: {path}: {exc}") from exc
    return validate_policy(document)


@dataclass(frozen=True)
class SeedResult:
    net_sharpe: float
    dsr_by_n: Mapping[str, float]


@dataclass(frozen=True)
class CandidateEvidence:
    hypothesis_id: str
    registered_at_utc: str
    by_seed: Mapping[int, SeedResult]
    pbo: float | None
    baselines_net_sharpe: Mapping[str, float] | None
    dataset_sha256: str | None
    missing_fraction: float | None
    n_oos_observations: int | None


def _finite(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def decide(evidence: CandidateEvidence, policy: DecisionPolicy) -> dict[str, Any]:
    t = policy.thresholds
    missing: list[str] = []
    failed: list[str] = []

    if policy.status != "APPROVED":
        missing.append(f"política não aprovada (status {policy.status})")
    elif _utc(evidence.registered_at_utc, "registered_at_utc") < _utc(
        policy.document["effective_from_utc"], "effective_from_utc"
    ):
        missing.append("hipótese registrada antes da vigência da política (não retroativa)")

    if t["require_dataset_sha256"] and not evidence.dataset_sha256:
        missing.append("dataset sem sha256")
    fraction = evidence.missing_fraction if _finite(evidence.missing_fraction) else None
    if fraction is None:
        missing.append("fração de dados ausentes desconhecida")
    elif fraction > t["max_missing_fraction"]:
        missing.append("qualidade de dados abaixo do exigido (fração ausente)")
    n_oos = evidence.n_oos_observations if _finite(evidence.n_oos_observations) else None
    if n_oos is None:
        missing.append("número de observações OOS desconhecido")
    elif n_oos < t["min_oos_observations"]:
        missing.append("observações OOS insuficientes")

    if len(evidence.by_seed) < t["min_seeds"]:
        missing.append(f"seeds avaliadas {len(evidence.by_seed)} < {t['min_seeds']}")
    dsr_values, sharpe_values = [], []
    for seed, result in evidence.by_seed.items():
        absent = [label for label in policy.dsr_scenario_labels if label not in result.dsr_by_n]
        if absent:
            missing.append(f"seed {seed}: DSR sem os cenários {absent}")
        if not result.dsr_by_n or not all(_finite(v) for v in result.dsr_by_n.values()):
            missing.append(f"seed {seed}: DSR não computável")
        else:
            dsr_values.extend((v, label, seed) for label, v in result.dsr_by_n.items())
        if _finite(result.net_sharpe):
            sharpe_values.append(result.net_sharpe)
        else:
            missing.append(f"seed {seed}: Sharpe líquido não computável")

    pbo = evidence.pbo if _finite(evidence.pbo) else None
    if pbo is None:
        missing.append("PBO não computado")
    baselines = evidence.baselines_net_sharpe or {}
    absent_baselines = [
        b for b in t["required_baselines"] if b not in baselines or not _finite(baselines[b])
    ]
    if absent_baselines:
        missing.append(f"sem comparação com baseline: {absent_baselines}")

    worst: dict[str, Any] = {}
    if dsr_values:
        value, label, seed = min(dsr_values)
        worst["dsr"] = {"value": value, "n_scenario": label, "seed": seed}
    if sharpe_values:
        worst["net_sharpe"] = min(sharpe_values)

    if missing or pbo is None:
        decision = "NO_DECISION"
    else:
        best_baseline = max(t["required_baselines"], key=lambda b: baselines[b])
        worst["best_baseline"] = {"name": best_baseline, "net_sharpe": baselines[best_baseline]}
        if worst["dsr"]["value"] < t["dsr_min"]:
            failed.append(f"DSR pior caso {worst['dsr']['value']:.4f} < {t['dsr_min']}")
        if pbo >= t["pbo_max_exclusive"]:
            failed.append(f"PBO {pbo:.4f} >= {t['pbo_max_exclusive']}")
        if worst["net_sharpe"] <= baselines[best_baseline]:
            failed.append(f"Sharpe líquido não supera o baseline {best_baseline}")
        decision = "NO_GO" if failed else "GO"

    return {
        "decision": decision,
        "hypothesis_id": evidence.hypothesis_id,
        "reasons": missing + failed,
        "worst_case": worst,
        "policy": policy.reference(),
    }


def record_decision(ledger: RunLedger, *, run_id: str, decision: Mapping[str, Any]) -> dict:
    return ledger.append(
        {
            "status": "DECISION",
            "run_id": run_id,
            "decided_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            **decision,
        }
    )
