"""Prompt 4: reavaliar hipóteses SEM reabrir o espaço de busca.

Regras: hipótese NO-GO não ganha variante, filtro, hiperparâmetro nem período novo. A régua nova
(custos, validação temporal/CPCV, baselines, PSR, DSR com sensibilidade de N, PBO, política) é
aplicada só ao artefato histórico que existir. Sem artefato, o status do protocolo novo é
NOT_REPRODUCIBLE e o status científico fica como está: a régua nova nunca promove sem evidência,
e só pode deixar o status mais conservador.

Entradas, todas versionadas e com hash: `charters/scientific_state.json` (status oficiais),
`trials.json` (ledger histórico), `h6_status.json` (artefato agregado da H6), o inventário de
artefatos (script de evidência) e o relatório do Prompt 3c. Nada aqui lê credencial nem importa
o `config` do projeto.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from statistics import NormalDist
from typing import Any

from predictor_core.measurement.trials import DeflationNotEstimableError

from GarimpoInvestimentos.research import ledgers
from GarimpoInvestimentos.research import strategy_metrics as sm
from GarimpoInvestimentos.research.decision_policy import (
    CandidateEvidence,
    DecisionPolicy,
    SeedResult,
    decide,
    load_policy,
)
from GarimpoInvestimentos.research.preregistration import count_preregistered
from GarimpoInvestimentos.run_ledger import RunLedger, recorded_run
from GarimpoInvestimentos.v3.cost_spec import CostSpec

_NEW_PROTOCOL = (
    "custos explícitos (CostSpec), walk-forward estrito/CPCV com purga e embargo, baselines no "
    "mesmo protocolo, PSR, DSR com sensibilidade de N (pior caso), PBO via CSCV e política v1"
)


def fisher_power(rho: float, n: float, *, alpha: float) -> float:
    """Poder bilateral do teste de ρ = 0 via Fisher-z, aproximação iid."""
    if n <= 3:
        return 0.0
    nd = NormalDist()
    shift = math.atanh(rho) * math.sqrt(n - 3)
    z = nd.inv_cdf(1 - alpha / 2)
    return nd.cdf(shift - z) + nd.cdf(-shift - z)


def fisher_mde_rho(n: float, *, alpha: float, power: float) -> float:
    nd = NormalDist()
    return math.tanh((nd.inv_cdf(1 - alpha / 2) + nd.inv_cdf(power)) / math.sqrt(n - 3))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def h6_row(h6: Mapping[str, Any], protocol: Mapping[str, Any], previous: str) -> dict:
    alpha, power_target = protocol["alpha"], protocol["power"]
    n, rho_alt = h6["n"], protocol["h6_relevant_rho"]
    n_eff = n / protocol["h6_overlap_days"]
    powers = {
        "fisher_iid_n": fisher_power(rho_alt, n, alpha=alpha),
        "fisher_n_efetivo": fisher_power(rho_alt, n_eff, alpha=alpha),
        "bootstrap_em_blocos_declarado": protocol["h6_declared_block_bootstrap_power"],
    }
    crosses_zero = h6["ic_lower"] <= 0 <= h6["ic_upper"]
    insufficient = max(powers.values()) < power_target
    status = previous if (crosses_zero and insufficient) else "REVIEW_REQUIRED"
    return {
        "hypothesis": "H6",
        "status_previous": previous,
        "protocol_applied": (
            "H6 não é estratégia: relação Spearman (IC95 em blocos) do sinal invertido com o "
            "retorno D+7 contra o nulo ρ = 0. Custos, CPCV, PSR, DSR e PBO: N/A. Régua nova "
            "aplicada ao artefato agregado versionado (h6_status.json): IC e poder"
        ),
        "status_new_protocol": "REEVALUATED_ON_AGGREGATE",
        "full_reproduction": "NOT_REPRODUCIBLE (pares brutos previsão × retorno ausentes no PC 2)",
        "status_new": status,
        "reason": (
            f"n = {n}, ρ = {h6['rho']:.4f}, IC95 [{h6['ic_lower']:.4f}; {h6['ic_upper']:.4f}] cruza "
            f"zero; poder para ρ = {rho_alt} ≤ {max(powers.values()):.3f} < {power_target}; o MDE "
            f"de ρ com n = {n} é {fisher_mde_rho(n, alpha=alpha, power=power_target):.3f}"
        ),
        "powers": powers,
        "mde_rho_fisher_iid": fisher_mde_rho(n, alpha=alpha, power=power_target),
        "strategy_metrics": "N/A",
    }


def closed_row(hypothesis: str, previous: str, trial: str, inventory: Mapping[str, Any]) -> dict:
    family = inventory["hypothesis_family"][hypothesis]
    found = inventory["families"][family]["usable_artifacts"]
    if found:
        return {
            "hypothesis": hypothesis,
            "trial": trial,
            "status_previous": previous,
            "protocol_applied": _NEW_PROTOCOL,
            "status_new_protocol": "REVIEW_REQUIRED",
            "status_new": previous,
            "reason": f"artefato encontrado ({found}); aplicação exige revisão humana",
        }
    return {
        "hypothesis": hypothesis,
        "trial": trial,
        "status_previous": previous,
        "protocol_applied": _NEW_PROTOCOL + " (não aplicável sem o artefato histórico)",
        "status_new_protocol": "NOT_REPRODUCIBLE",
        "status_new": previous,
        "reason": (
            f"artefato exigido ausente: {inventory['families'][family]['required']}. Sem "
            "recriar variantes; a régua nova não promove e o status fica como estava"
        ),
    }


def open_row(
    hypothesis: str, previous: str, trial: str, inventory: Mapping[str, Any], protocol: Mapping
) -> dict:
    family = inventory["hypothesis_family"][hypothesis]
    return {
        "hypothesis": hypothesis,
        "trial": trial,
        "status_previous": previous,
        "protocol_applied": "só a configuração registrada; nenhuma variante",
        "status_new_protocol": "NOT_EXECUTABLE",
        "status_new": previous,
        "reason": f"sem execução válida anterior e sem dado local: {inventory['families'][family]['required']}",
        "protocol_incompatibilities": protocol["incompatibilities"].get(hypothesis, []),
    }


def fm_row(report: Mapping[str, Any], prereg: Mapping[str, Any], policy: DecisionPolicy) -> dict:
    strategies = report["strategy"]
    baselines = {
        b: strategies[b]["net_sharpe"] for b in ("naive_persistence", "always_long", "buy_and_hold")
    }
    baselines["random_walk"] = 0.0
    decision = decide(
        CandidateEvidence(
            hypothesis_id=prereg["id"],
            registered_at_utc=prereg["registered_at_utc"],
            by_seed={0: SeedResult(strategies["chronos_bolt_small"]["net_sharpe"], {})},
            pbo=None,
            baselines_net_sharpe=baselines,
            dataset_sha256=prereg["data"]["member_sha256"],
            missing_fraction=0.0,
            n_oos_observations=report["n_targets"],
        ),
        policy,
    )
    return {
        "hypothesis": "FM-3c",
        "trial": prereg["id"],
        "status_previous": "NO_DECISION (política PROPOSED)",
        "protocol_applied": "pré-registrado antes do primeiro backtest (Prompt 3c); nenhuma execução nova",
        "status_new_protocol": "EVALUATED_PREREGISTERED",
        "status_new": decision["decision"],
        "reason": (
            f"previsão {report['forecast_status']}, estratégia {report['strategy_status']}; "
            + "; ".join(decision["reasons"])
        ),
        "decision": decision,
        "run_id": report["run_id"],
    }


def n_trials_summary(
    trials: list[dict],
    protocol: Mapping[str, Any],
    policy: DecisionPolicy,
    *,
    preregistered_count: int = 0,
) -> dict:
    lineage_lower = protocol["n_lineage_h1_h6_lower_bound"]
    registered = len(trials)
    # FM-3c é anterior ao ledger de pré-registros (entra pelo protocolo); as hipóteses
    # pré-registradas no ledger entram sozinhas, sem número digitado.
    new_hypotheses = protocol["new_hypotheses_since_prompt2"] + preregistered_count
    all_lower = registered + protocol["documented_unregistered"] + new_hypotheses
    all_upper = all_lower + protocol["n_upper_extra"]
    scenarios = sm.n_trials_scenarios(
        all_lower,
        multipliers=policy.document["dsr_n_sensitivity"]["multipliers"],
        n_upper=all_upper,
    )
    try:
        var_sr = sm.trial_sharpe_variance(trials)
        dsr = {"status": "ESTIMABLE", "var_trials_sr": var_sr, "scenarios": scenarios}
    except DeflationNotEstimableError as exc:
        dsr = {
            "status": "NOT_ESTIMABLE",
            "reason": str(exc),
            "scenarios": {label: {"n_trials": n, "dsr": "N/A"} for label, n in scenarios.items()},
        }
    return {
        "trials_json_entries": registered,
        "lineage_h1_h6": f"LOWER_BOUND({lineage_lower})",
        "all_families": f"LOWER_BOUND({all_lower})",
        "all_families_upper_estimate": all_upper,
        "added_by_prompt4": 0,
        "preregistered_in_ledger": preregistered_count,
        "dsr_sensitivity": dsr,
    }


def reevaluate(
    *,
    scientific_state: Mapping[str, Any],
    trials: list[dict],
    h6_status: Mapping[str, Any],
    inventory: Mapping[str, Any],
    fm_report: Mapping[str, Any],
    fm_prereg: Mapping[str, Any],
    protocol: Mapping[str, Any],
    policy: DecisionPolicy,
    preregistered_count: int = 0,
) -> dict:
    statuses = scientific_state["hypotheses"]
    trial_of = scientific_state["hypothesis_trials"]
    rows = []
    for h in sorted(statuses, key=lambda k: int(k[1:])):
        previous = statuses[h]
        if h == "H6":
            rows.append({**h6_row(h6_status, protocol, previous), "trial": trial_of[h]})
        elif previous == "REGISTERED_NOT_ACTIVATED":
            rows.append(open_row(h, previous, trial_of[h], inventory, protocol))
        else:
            rows.append(closed_row(h, previous, trial_of[h], inventory))
    for extra in protocol["extra_closed_rows"]:
        rows.append(
            closed_row(extra["hypothesis"], extra["status_previous"], extra["trial"], inventory)
        )
    rows.append(fm_row(fm_report, fm_prereg, policy))
    return {
        "rows": rows,
        "n_trials": n_trials_summary(
            trials, protocol, policy, preregistered_count=preregistered_count
        ),
        "integrity": {
            "new_variants_run_on_no_go": 0,
            "holdout_accessed": "NO",
            "preregistrations_before_new_experiments": "N/A (nenhum experimento novo no Prompt 4); YES para o 3c",
            "trials_deleted": 0,
        },
    }


def run_reevaluation(
    *,
    ledger_path: Path,
    out_path: Path,
    paths: Mapping[str, Path],
    protocol: Mapping[str, Any],
    preregistrations_path: Path = ledgers.PREREGISTRATIONS,
) -> dict:
    policy = load_policy()
    preregistered = count_preregistered(RunLedger(preregistrations_path))
    loaded = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in paths.items()}
    with recorded_run(
        RunLedger(ledger_path),
        kind="hypothesis_reevaluation",
        config={
            "inputs_sha256": {k: _sha256(p) for k, p in paths.items()},
            "protocol": dict(protocol),
        },
        costs=CostSpec().as_dict(),
        validation_protocol={"new_protocol": _NEW_PROTOCOL, "search_reopened": False},
        model={"kind": "nenhum modelo: reavaliação de artefatos"},
        seeds=None,
        policy=policy.reference(),
    ) as run:
        report = reevaluate(
            scientific_state=loaded["scientific_state"],
            trials=loaded["trials"],
            h6_status=loaded["h6_status"],
            inventory=loaded["inventory"],
            fm_report=loaded["fm_report"],
            fm_prereg=loaded["fm_prereg"],
            protocol=protocol,
            policy=policy,
            preregistered_count=preregistered,
        )
        for row in report["rows"]:
            row.setdefault("run_id", run.run_id)
        report["run_id"] = run.run_id
        out_path.write_text(
            json.dumps(report, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        run.metrics = {
            "rows": len(report["rows"]),
            "status_new_protocol": {
                r["hypothesis"]: r["status_new_protocol"] for r in report["rows"]
            },
            "n_trials_all_families": report["n_trials"]["all_families"],
        }
        run.artifacts = {"report": str(out_path), "report_sha256": _sha256(out_path)}
    return report
