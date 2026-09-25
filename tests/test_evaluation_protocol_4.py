"""Prompt 4: reavaliação sem reabrir busca, pré-registro, holdout selado e deduplicação.

Sem rede, sem credenciais. Os status oficiais, o trials.json, o h6_status.json e o relatório do
Prompt 3c são lidos do repositório; o inventário de artefatos é sintético (o real depende da
máquina e vai como evidência).
"""

from __future__ import annotations

import json
import math
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import NormalDist

import pytest

from GarimpoInvestimentos.analyzers.trials import TRIALS_PATH, load_trials
from GarimpoInvestimentos.research import dedup, holdout, preregistration, reevaluation
from GarimpoInvestimentos.research.decision_policy import load_policy
from GarimpoInvestimentos.run_ledger import RunLedger

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "docs/evidence/2026-09-25-prompt4/protocol.json").read_text("utf-8"))
FM_DIR = ROOT / "docs/evidence/2026-09-24-prompt3c"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _inventory(usable_v3=(), usable_llm=()):
    families = {
        "v3": {"required": "retornos do WFA", "usable_artifacts": list(usable_v3)},
        "llm_d7": {"required": "pares previsão × D+7", "usable_artifacts": list(usable_llm)},
        "llm_generator": {"required": "propostas do gerador", "usable_artifacts": []},
    }
    mapping = {h: "v3" for h in ("H1", "H2", "H3", "H7", "H9", "V3-grid (16)")}
    mapping.update({h: "llm_d7" for h in ("H4", "H5", "H6", "v1-ancestral")})
    mapping["H8"] = "llm_generator"
    return {"hypothesis_family": mapping, "families": families}


def _reevaluate(**overrides):
    kwargs = {
        "scientific_state": _json(ROOT / "charters/scientific_state.json"),
        "trials": load_trials(TRIALS_PATH),
        "h6_status": _json(ROOT / "GarimpoInvestimentos/h6_status.json"),
        "inventory": _inventory(),
        "fm_report": _json(FM_DIR / "report.json"),
        "fm_prereg": _json(FM_DIR / "preregistro.json"),
        "protocol": PROTOCOL,
        "policy": load_policy(),
    }
    kwargs.update(overrides)
    return reevaluation.reevaluate(**kwargs)


# ---------------------------------------------------------------- reavaliação


def test_fisher_power_and_mde_by_hand():
    nd = NormalDist()
    shift = math.atanh(0.2) * math.sqrt(81)
    expected = nd.cdf(shift - 1.959964) + nd.cdf(-shift - 1.959964)
    assert reevaluation.fisher_power(0.2, 84, alpha=0.05) == pytest.approx(expected, abs=1e-6)
    assert reevaluation.fisher_power(0.2, 84, alpha=0.05) == pytest.approx(0.446, abs=2e-3)
    assert reevaluation.fisher_mde_rho(84, alpha=0.05, power=0.8) == pytest.approx(
        math.tanh((1.959964 + 0.841621) / 9), abs=1e-5
    )


def test_no_go_hypotheses_without_artifacts_are_not_reproducible_and_keep_status():
    report = _reevaluate()
    rows = {r["hypothesis"]: r for r in report["rows"]}
    for h in ("H1", "H2", "H3", "H5"):
        assert rows[h]["status_previous"] == "CLOSED_NO_GO"
        assert rows[h]["status_new_protocol"] == "NOT_REPRODUCIBLE"
        assert rows[h]["status_new"] == "CLOSED_NO_GO"
    for h in ("H4", "H9", "V3-grid (16)", "v1-ancestral"):
        assert rows[h]["status_new_protocol"] == "NOT_REPRODUCIBLE"
        assert rows[h]["status_new"] == rows[h]["status_previous"]
    for h in ("H7", "H8"):
        assert rows[h]["status_new_protocol"] == "NOT_EXECUTABLE"
        assert rows[h]["status_new"] == "REGISTERED_NOT_ACTIVATED"
        assert rows[h]["protocol_incompatibilities"]
    assert all(r["status_new"] != "GO" for r in report["rows"])
    assert report["integrity"]["new_variants_run_on_no_go"] == 0
    assert report["integrity"]["holdout_accessed"] == "NO"


def test_h6_is_reevaluated_as_a_correlation_and_stays_insufficient():
    row = next(r for r in _reevaluate()["rows"] if r["hypothesis"] == "H6")
    assert row["status_new_protocol"] == "REEVALUATED_ON_AGGREGATE"
    assert row["status_new"] == "CLOSED_INSUFFICIENT_SAMPLE"
    assert row["strategy_metrics"] == "N/A"
    assert max(row["powers"].values()) < 0.8
    assert row["powers"]["fisher_n_efetivo"] < row["powers"]["fisher_iid_n"]


def test_h6_with_conclusive_aggregate_is_flagged_for_review_not_promoted():
    strong = {"n": 2000, "rho": 0.3, "ic_lower": 0.25, "ic_upper": 0.35}
    protocol = {**PROTOCOL, "h6_declared_block_bootstrap_power": 0.99}
    row = next(
        r
        for r in _reevaluate(h6_status=strong, protocol=protocol)["rows"]
        if r["hypothesis"] == "H6"
    )
    assert row["status_new"] == "REVIEW_REQUIRED"


def test_found_artifact_requires_human_review_instead_of_automatic_change():
    report = _reevaluate(inventory=_inventory(usable_v3=["git:v3/returns.json"]))
    row = next(r for r in report["rows"] if r["hypothesis"] == "H1")
    assert row["status_new_protocol"] == "REVIEW_REQUIRED"
    assert row["status_new"] == "CLOSED_NO_GO"


def test_fm_hypothesis_is_no_decision_because_the_policy_is_not_retroactive():
    row = next(r for r in _reevaluate()["rows"] if r["hypothesis"] == "FM-3c")
    assert row["status_new"] == "NO_DECISION"
    assert any("retroativa" in reason for reason in row["decision"]["reasons"])
    assert row["decision"]["policy"]["status"] == "APPROVED"
    assert row["run_id"] == _json(FM_DIR / "report.json")["run_id"]


def test_n_trials_accumulates_and_dsr_sensitivity_is_not_estimable():
    summary = _reevaluate()["n_trials"]
    assert summary["trials_json_entries"] == 26
    assert summary["lineage_h1_h6"] == "LOWER_BOUND(32)"
    assert summary["all_families"] == "LOWER_BOUND(36)"
    assert summary["all_families_upper_estimate"] == 46
    dsr = summary["dsr_sensitivity"]
    assert dsr["status"] == "NOT_ESTIMABLE"
    assert {k: v["n_trials"] for k, v in dsr["scenarios"].items()} == {
        "N": 36,
        "2N": 72,
        "5N": 180,
        "N_upper": 46,
    }


def test_reevaluation_run_is_in_the_ledger_with_the_policy(tmp_path):
    paths = {
        "scientific_state": ROOT / "charters/scientific_state.json",
        "trials": TRIALS_PATH,
        "h6_status": ROOT / "GarimpoInvestimentos/h6_status.json",
        "inventory": tmp_path / "inventory.json",
        "fm_report": FM_DIR / "report.json",
        "fm_prereg": FM_DIR / "preregistro.json",
    }
    paths["inventory"].write_text(json.dumps(_inventory()), encoding="utf-8")
    ledger_path = tmp_path / "runs.jsonl"
    report = reevaluation.run_reevaluation(
        ledger_path=ledger_path, out_path=tmp_path / "r.json", paths=paths, protocol=PROTOCOL
    )
    ledger = RunLedger(ledger_path)
    assert [r["status"] for r in ledger.records()] == ["STARTED", "COMPLETED"]
    assert ledger.records()[0]["policy"]["status"] == "APPROVED"
    assert ledger.verify_chain() == []
    assert all(r["run_id"] for r in report["rows"])


# ---------------------------------------------------------------- pré-registro


def _complete_prereg(**overrides):
    policy = load_policy().reference()
    doc = {
        "id": "h-teste-v1",
        "description": "d",
        "expected_mechanism": "m",
        "features": ["f"],
        "target": "t",
        "period": {"development": ["2026-01-01", "2026-06-01"]},
        "universe": ["BTCUSDT"],
        "costs": {"per_leg_bps": 15},
        "validation_protocol": "cpcv",
        "primary_metric": "net_sharpe",
        "secondary_metrics": ["max_dd"],
        "policy": {"id": policy["id"], "version": policy["version"], "sha256": policy["sha256"]},
        "max_variants": 1,
        "seeds": [42, 43, 44, 45, 46],
        "holdout": {"holdout_id": "h"},
        "criteria": {"GO": "política v1", "NO_GO": "política v1", "NO_DECISION": "insumo ausente"},
    }
    doc.update(overrides)
    return doc


def test_preregistration_template_requires_every_field(tmp_path):
    assert preregistration.validate_preregistration(_complete_prereg()) == []
    problems = preregistration.validate_preregistration(
        _complete_prereg(expected_mechanism="", max_variants=0, criteria={"GO": "x"})
    )
    assert any("expected_mechanism" in p for p in problems)
    assert any("max_variants" in p for p in problems)
    assert any("NO_GO" in p for p in problems)
    ledger = RunLedger(tmp_path / "prereg.jsonl")
    with pytest.raises(preregistration.PreregistrationError):
        preregistration.require_preregistered_before_run(ledger, "h-teste-v1")
    preregistration.register_preregistration(ledger, _complete_prereg())
    assert preregistration.require_preregistered_before_run(ledger, "h-teste-v1")
    with pytest.raises(preregistration.PreregistrationError):
        preregistration.register_preregistration(ledger, _complete_prereg(description="outra"))


def test_prompt3c_preregistration_predates_the_prompt4_template():
    problems = preregistration.validate_preregistration(_json(FM_DIR / "preregistro.json"))
    for field in ("expected_mechanism", "max_variants", "holdout", "criteria"):
        assert any(field in p for p in problems)


# ---------------------------------------------------------------- holdout


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_future_holdout_cannot_be_hashed_or_opened_early(tmp_path):
    ledger = RunLedger(tmp_path / "holdouts.jsonl")
    now = datetime.now(UTC)
    window = (_iso(now + timedelta(days=1)), _iso(now + timedelta(days=181)))
    holdout.seal_holdout(
        ledger,
        holdout_id="fut",
        universe="BTCUSDT",
        interval_utc=window,
        content_rule="sha256 da série",
        opening_conditions=["aprovação"],
    )
    assert holdout.holdout_state(ledger, "fut") == "SEALED"
    with pytest.raises(holdout.HoldoutError):
        holdout.seal_holdout(
            ledger,
            holdout_id="fut",
            universe="x",
            interval_utc=window,
            content_rule="x",
            opening_conditions=["x"],
        )
    with pytest.raises(holdout.HoldoutError):
        holdout.register_content_hash(ledger, "fut", "a" * 64)
    approval = {"approved_by": "dono", "approved_at_utc": _iso(now), "evidence": "doc"}
    with pytest.raises(holdout.HoldoutError):
        holdout.open_holdout(
            ledger,
            "fut",
            approval=approval,
            content_sha256="a" * 64,
            conditions_met={"aprovação": "ok"},
        )
    with pytest.raises(holdout.HoldoutError):
        holdout.assert_outside_holdouts(ledger, (_iso(now), _iso(now + timedelta(days=30))))
    holdout.assert_outside_holdouts(ledger, (_iso(now - timedelta(days=30)), _iso(now)))


def test_holdout_opens_once_with_human_approval_and_matching_content(tmp_path):
    ledger = RunLedger(tmp_path / "holdouts.jsonl")
    now = datetime.now(UTC)
    window = (_iso(now - timedelta(days=40)), _iso(now - timedelta(days=10)))
    holdout.seal_holdout(
        ledger,
        holdout_id="past",
        universe="BTCUSDT",
        interval_utc=window,
        content_rule="sha256 da série",
        opening_conditions=["hipótese pré-registrada", "aprovação do dono"],
    )
    holdout.register_content_hash(ledger, "past", "b" * 64)
    conditions = {"hipótese pré-registrada": "h-1", "aprovação do dono": "chat"}
    approval = {"approved_by": "dono", "approved_at_utc": _iso(now), "evidence": "doc"}
    with pytest.raises(holdout.HoldoutError):
        holdout.open_holdout(
            ledger,
            "past",
            approval={"approved_by": "dono"},
            content_sha256="b" * 64,
            conditions_met=conditions,
        )
    with pytest.raises(holdout.HoldoutError):
        holdout.open_holdout(
            ledger, "past", approval=approval, content_sha256="c" * 64, conditions_met=conditions
        )
    with pytest.raises(holdout.HoldoutError):
        holdout.open_holdout(
            ledger, "past", approval=approval, content_sha256="b" * 64, conditions_met={}
        )
    holdout.open_holdout(
        ledger, "past", approval=approval, content_sha256="b" * 64, conditions_met=conditions
    )
    assert holdout.holdout_state(ledger, "past") == "OPENED"
    with pytest.raises(holdout.HoldoutError):
        holdout.open_holdout(
            ledger, "past", approval=approval, content_sha256="b" * 64, conditions_met=conditions
        )
    assert ledger.verify_chain() == []


# ---------------------------------------------------------------- deduplicação


def test_redundant_candidate_is_rejected_before_any_backtest():
    rng = random.Random(4)
    factor = [rng.gauss(0, 1) for _ in range(200)]
    same_ranks = [2 * x + 1 for x in factor]
    independent = [rng.gauss(0, 1) for _ in range(200)]
    kwargs = {
        "development_period": ("2025-01-01", "2025-12-31"),
        "threshold": 0.99,
        "threshold_source": "pré-registro de teste",
    }
    result = dedup.redundancy_check("cand", same_ranks, {"f1": factor, "f2": independent}, **kwargs)
    assert result["status"] == "REJECTED_REDUNDANT"
    assert result["closest_factor"] == "f1" and result["value"] == pytest.approx(1.0)
    fresh = [rng.gauss(0, 1) for _ in range(200)]
    assert (
        dedup.redundancy_check("c2", fresh, {"f1": factor}, **kwargs)["status"] == "NOT_REDUNDANT"
    )
    with pytest.raises(dedup.DedupError):
        dedup.redundancy_check("c3", fresh[:10], {"f1": factor}, **kwargs)
    with pytest.raises(dedup.DedupError):
        dedup.redundancy_check("c4", fresh, {"f1": factor}, **{**kwargs, "threshold_source": ""})
