"""Prompt 3b: CPCV com purga e embargo, PSR/DSR/PBO com referência e política de decisão versionada.

Sem rede, sem credenciais, sem dado real: séries sintéticas determinísticas.
"""

from __future__ import annotations

import ast
import json
import math
import random
import statistics
from dataclasses import replace
from pathlib import Path

import pytest
from predictor_core.measurement.trials import DeflationNotEstimableError, expected_max_sharpe

from GarimpoInvestimentos.research import cpcv
from GarimpoInvestimentos.research import decision_policy as dp
from GarimpoInvestimentos.research import strategy_metrics as sm
from GarimpoInvestimentos.research.validation import LabelInterval
from GarimpoInvestimentos.run_ledger import RunLedger, canonical_sha256

HOUR = 3_600_000
STEP = 8 * HOUR  # cadência de decisão do V3 (funding a cada 8 h)
HORIZON = 24 * HOUR  # horizonte do rótulo do V3


def _labels(n: int, horizon: int = HORIZON) -> list[LabelInterval]:
    return [LabelInterval(i * STEP, i * STEP + horizon, i * STEP + horizon) for i in range(n)]


def _overlap(a: LabelInterval, b: LabelInterval) -> bool:
    """Janelas de informação [start, available] fechadas se cruzam."""
    return a.start <= b.available and a.available >= b.start


def _assert_no_forbidden_pair(labels, split, embargo):
    parts = split.train + split.test + split.purged + split.embargoed
    assert sorted(parts) == list(range(len(labels)))  # partição exata, sem duplicata
    for i in split.train:
        for j in split.test:
            assert not _overlap(labels[i], labels[j]), (split.test_groups, i, j)
            assert not labels[j].available < labels[i].start <= labels[j].available + embargo


# ---------------------------------------------------------------- CPCV: purga e embargo


def test_without_purge_train_labels_would_cross_test_and_cpcv_leaves_no_forbidden_pair():
    labels = _labels(60)
    embargo = 2 * STEP
    splits = cpcv.cpcv_splits(labels, n_groups=6, n_test_groups=2, embargo=embargo)
    assert len(splits) == 15  # C(6, 2)

    naive_leaks = 0
    for split in splits:
        test = set(split.test)
        naive_train = [i for i in range(len(labels)) if i not in test]
        naive_leaks += sum(
            1 for i in naive_train for j in split.test if _overlap(labels[i], labels[j])
        )
        _assert_no_forbidden_pair(labels, split, embargo)
    # rótulos de 24 h a cada 8 h: sem a purga, o complemento do teste vaza
    assert naive_leaks > 0


@pytest.mark.parametrize("seed", range(25))
def test_no_forbidden_pair_with_irregular_labels_and_late_availability(seed):
    rng = random.Random(seed)
    n = rng.randint(20, 80)
    labels = []
    for start in sorted(rng.sample(range(10_000), n)):
        end = start + rng.randint(0, 400)
        labels.append(LabelInterval(start, end, end + rng.randint(0, 150)))
    n_groups = rng.randint(3, 8)
    n_test_groups = rng.randint(1, n_groups - 1)
    embargo = rng.randint(0, 300)
    splits = cpcv.cpcv_splits(
        labels, n_groups=n_groups, n_test_groups=n_test_groups, embargo=embargo
    )
    assert len(splits) == math.comb(n_groups, n_test_groups)
    for split in splits:
        _assert_no_forbidden_pair(labels, split, embargo)


def test_purge_size_follows_the_label_horizon():
    labels = _labels(60)  # rótulo cobre 3 passos
    splits = cpcv.cpcv_splits(labels, n_groups=6, n_test_groups=1, embargo=0)
    by_group = {s.test_groups: s for s in splits}
    # grupo interior: 3 rótulos antes (terminam em t0 ou depois) e 3 depois (começam até t1)
    assert len(by_group[(2,)].purged) == 6
    assert len(by_group[(0,)].purged) == 3
    assert len(by_group[(5,)].purged) == 3
    wider = cpcv.cpcv_splits(_labels(60, 6 * STEP), n_groups=6, n_test_groups=1, embargo=0)
    assert len(wider[2].purged) == 12


def test_embargo_is_explicit_and_configurable():
    labels = _labels(60)
    trains = []
    for embargo in (0, 1 * STEP, 3 * STEP, 6 * STEP):
        splits = cpcv.cpcv_splits(labels, n_groups=6, n_test_groups=2, embargo=embargo)
        if embargo == 0:
            assert all(not s.embargoed for s in splits)
        else:
            assert any(s.embargoed for s in splits)
        trains.append(sum(len(s.train) for s in splits))
    assert trains == sorted(trains, reverse=True) and trains[0] > trains[-1]
    with pytest.raises(ValueError):
        cpcv.cpcv_splits(labels, n_groups=6, n_test_groups=2, embargo=-1)


def test_backtest_paths_cover_every_group_once():
    labels = _labels(60)
    splits = cpcv.cpcv_splits(labels, n_groups=6, n_test_groups=2, embargo=0)
    paths = cpcv.backtest_paths(splits, 6)
    assert len(paths) == cpcv.n_backtest_paths(6, 2) == 5  # C(5, 1)
    used = set()
    for path in paths:
        assert [g for _, g in path] == list(range(6))
        for split_index, group in path:
            assert group in splits[split_index].test_groups
            assert (split_index, group) not in used
            used.add((split_index, group))


def test_embargo_is_derived_from_the_autocorrelation_of_step_returns():
    rng = random.Random(11)
    noise = [rng.gauss(0, 1) for _ in range(20_003)]
    ma2 = [noise[t] + noise[t - 1] + noise[t - 2] for t in range(2, len(noise))]
    white = [rng.gauss(0, 1) for _ in range(20_000)]
    derived = cpcv.derive_purge_and_embargo(ma2, label_horizon=HORIZON, step=STEP, max_lag=10)
    # MA(2): ACF teórica 2/3, 1/3 e depois 0 → dependência de 2 passos
    assert derived["embargo_steps"] == 2 and derived["embargo_size"] == 2 * STEP
    assert derived["purge_size"] == HORIZON and not derived["capped"]
    assert (
        cpcv.derive_purge_and_embargo(white, label_horizon=HORIZON, step=STEP, max_lag=10)[
            "embargo_steps"
        ]
        == 0
    )


# ---------------------------------------------------------------- métricas


def test_dsr_matches_the_published_numerical_example():
    """Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", JPM 40(5), exemplo numérico:
    N = 100 tentativas, V[SR anual] = 1/2, SR anual = 2,5, T = 1250 observações diárias,
    assimetria −3, curtose 10 → SR0 ≈ 0,1132 por dia e DSR ≈ 0,9004.

    Conta à mão: fator = (1−γ)Φ⁻¹(0,99) + γΦ⁻¹(1 − 1/(100e)) = 0,4228·2,3263 + 0,5772·2,6804
    ≈ 2,5307; SR0 = √(0,5/250)·2,5307 ≈ 0,1132; SR = 2,5/√250 ≈ 0,1581;
    z = (0,1581 − 0,1132)·√1249 / √(1 + 3·0,1581 + (9/4)·0,1581²) ≈ 1,2835; Φ(z) ≈ 0,9004.
    """
    sr0 = expected_max_sharpe(100, 0.5 / 250)
    assert sr0 == pytest.approx(0.1132, abs=5e-5)
    dsr = sm.psr_from_moments(
        2.5 / math.sqrt(250), skew=-3.0, kurtosis=10.0, n=1250, benchmark_sharpe=sr0
    )
    assert dsr == pytest.approx(0.9004, abs=5e-5)


def test_psr_from_moments_equals_the_core_psr_on_a_series():
    rng = random.Random(3)
    returns = [rng.gauss(0.001, 0.02) + (0.05 if i % 50 == 0 else 0.0) for i in range(500)]
    n = len(returns)
    mean = sum(returns) / n
    m2 = sum((x - mean) ** 2 for x in returns) / n
    skew = sum((x - mean) ** 3 for x in returns) / n / m2**1.5
    kurt = sum((x - mean) ** 4 for x in returns) / n / m2**2
    for benchmark in (0.0, 0.02):
        by_moments = sm.psr_from_moments(
            mean / math.sqrt(m2), skew=skew, kurtosis=kurt, n=n, benchmark_sharpe=benchmark
        )
        assert by_moments == pytest.approx(sm.psr(returns, benchmark), rel=1e-12)


def test_larger_n_makes_the_dsr_more_conservative_with_identical_candidate():
    rng = random.Random(5)
    returns = [rng.gauss(0.004, 0.02) for _ in range(750)]
    scenarios = sm.n_trials_scenarios(32, multipliers=[1, 2, 5], n_upper=42)
    assert scenarios == {"N": 32, "2N": 64, "5N": 160, "N_upper": 42}
    result = sm.dsr_sensitivity(returns, scenarios=scenarios, var_trials_sr=0.002)
    ordered = sorted(result["by_n"].values(), key=lambda r: r["n_trials"])
    assert [r["n_trials"] for r in ordered] == [32, 42, 64, 160]
    for smaller, larger in zip(ordered, ordered[1:], strict=False):
        assert larger["sr0"] > smaller["sr0"]
        assert larger["dsr"] < smaller["dsr"]
    assert result["worst_label"] == "5N"
    assert result["worst_dsr"] == result["by_n"]["5N"]["dsr"]


@pytest.mark.parametrize(
    ("n_trials", "var"), [(1, 0.002), (32, 0.0), (32, float("nan")), (32, -1.0)]
)
def test_dsr_refuses_to_pass_as_deflated_without_a_discount(n_trials, var):
    with pytest.raises(DeflationNotEstimableError):
        sm.deflated_sharpe([0.01, -0.02, 0.03, 0.0], n_trials=n_trials, var_trials_sr=var)


def test_trial_variance_requires_a_single_sharpe_basis():
    trials = [
        {"name": f"t{i}", "sharpe": s, "params": {"sharpe_basis": sm.SHARPE_BASIS}}
        for i, s in enumerate([0.1, 0.3, -0.2])
    ] + [{"name": "sem-metrica", "sharpe": None, "params": {}}]
    assert sm.trial_sharpe_variance(trials) == pytest.approx(statistics.variance([0.1, 0.3, -0.2]))
    with pytest.raises(DeflationNotEstimableError):
        sm.trial_sharpe_variance(trials + [{"name": "por-trade", "sharpe": 0.5, "params": {}}])
    with pytest.raises(DeflationNotEstimableError):
        sm.trial_sharpe_variance(trials[:1])


def test_pbo_matches_a_hand_computed_cscv():
    """CSCV com S = 4 blocos de 2 observações → C(4, 2) = 6 combinações.

    A = blocos constantes (5, 2, 1, −3); B = (+1, −1) em todo bloco → Sharpe de B = 0 exato.
    O sinal do Sharpe de A num conjunto de blocos é o sinal da média desses blocos:
      IS {1,2} +3,5 → escolhe A; OOS {3,4} −1,0 → A abaixo de B → logit < 0
      IS {1,3} +3,0 → A; OOS {2,4} −0,5 → logit < 0
      IS {1,4} +1,0 → A; OOS {2,3} +1,5 → A acima de B → logit > 0
      IS {2,3} +1,5 → A; OOS {1,4} +1,0 → logit > 0
      IS {2,4} −0,5 → B; OOS {1,3} +3,0 → B abaixo de A → logit < 0
      IS {3,4} −1,0 → B; OOS {1,2} +3,5 → logit < 0
    PBO = 4/6. Com 2 configurações, ω = 1/3 ou 2/3 e o logit é ±ln 2.
    """
    result = sm.pbo_cscv({"A": [5, 5, 2, 2, 1, 1, -3, -3], "B": [1, -1] * 4}, n_splits=4)
    assert result.pbo == pytest.approx(4 / 6, abs=1e-15)
    assert result.n_combinations == 6
    assert sorted(result.logits) == pytest.approx([-math.log(2)] * 4 + [math.log(2)] * 2)


def test_net_sharpe_drawdown_and_turnover_by_hand():
    # média 0,02; variância amostral 0,002/3 → Sharpe = 0,02/√(0,002/3) = √0,6
    assert sm.per_decision_sharpe([0.01, 0.03, -0.01, 0.05]) == pytest.approx(math.sqrt(0.6))
    # equity 1 → 1,1 → 0,88 → 0,924 → 0,8316 → 1,08108; pico 1,1; vale 0,8316
    assert sm.max_drawdown([0.1, -0.2, 0.05, -0.1, 0.3]) == pytest.approx(1 - 0.8316 / 1.1)
    # |0,5| + 0 + |−1,0| + |0,5| + liquidação 0 = 2,0 em 4 períodos
    assert sm.turnover([0.5, 0.5, -0.5, 0.0]) == pytest.approx(0.5)
    # V3: cada decisão abre e fecha → 2·(0,5 + 0,5 + 0,5 + 0)/4
    assert sm.turnover([0.5, 0.5, -0.5, 0.0], round_trip=True) == pytest.approx(0.75)
    metrics = sm.strategy_metrics([0.01, 0.03, -0.01, 0.05], [1, 1, 1, 1], round_trip=True)
    assert metrics["sharpe_basis"] == "per_decision_unannualized_sample_std"


# ---------------------------------------------------------------- política de decisão

_SEEDS = (42, 43, 44, 45, 46)
_STRONG_DSR = {"N": 0.99, "2N": 0.985, "5N": 0.97, "N_upper": 0.988}


def _approved(**thresholds) -> dp.DecisionPolicy:
    document = json.loads(dp.CURRENT_POLICY_PATH.read_text(encoding="utf-8"))
    document["status"] = "APPROVED"
    document["approval"].update(approved_by="teste", approved_at_utc="2026-09-24T00:00:00Z")
    document["effective_from_utc"] = "2026-09-24T00:00:00Z"
    document["thresholds"].update(thresholds)
    return dp.validate_policy(document)


def _evidence(**overrides) -> dp.CandidateEvidence:
    base = dp.CandidateEvidence(
        hypothesis_id="h-sintetica",
        registered_at_utc="2026-10-01T00:00:00Z",
        by_seed={s: dp.SeedResult(net_sharpe=0.30, dsr_by_n=dict(_STRONG_DSR)) for s in _SEEDS},
        pbo=0.05,
        baselines_net_sharpe={
            "random_walk": 0.0,
            "naive_persistence": 0.05,
            "always_long": 0.10,
            "buy_and_hold": 0.12,
        },
        dataset_sha256="a" * 64,
        missing_fraction=0.0,
        n_oos_observations=200,
    )
    return replace(base, **overrides)


def test_versioned_policy_file_is_proposed_and_hashed():
    policy = dp.load_policy()
    assert policy.status == "PROPOSED"
    document = json.loads(dp.CURRENT_POLICY_PATH.read_text(encoding="utf-8"))
    assert policy.sha256 == canonical_sha256(document)
    assert policy.reference() == {
        "id": "cripto-decision-policy",
        "version": 1,
        "sha256": policy.sha256,
        "status": "PROPOSED",
    }
    assert policy.dsr_scenario_labels == ["N", "2N", "5N"]


def test_unapproved_policy_never_decides():
    decision = dp.decide(_evidence(), dp.load_policy())
    assert decision["decision"] == "NO_DECISION"
    assert any("não aprovada" in r for r in decision["reasons"])


def test_strong_evidence_under_approved_policy_is_go_and_records_the_policy():
    policy = _approved()
    decision = dp.decide(_evidence(), policy)
    assert decision["decision"] == "GO", decision["reasons"]
    assert decision["policy"] == policy.reference()
    assert decision["policy"]["sha256"] == policy.sha256
    assert decision["worst_case"]["dsr"]["n_scenario"] == "5N"
    assert decision["worst_case"]["best_baseline"]["name"] == "buy_and_hold"


@pytest.mark.parametrize(
    "baselines",
    [
        None,
        {},
        {"random_walk": 0.0, "naive_persistence": 0.05, "always_long": 0.10},
        {"random_walk": 0.0, "naive_persistence": 0.05, "always_long": 0.1, "buy_and_hold": None},
        {
            "random_walk": 0.0,
            "naive_persistence": float("nan"),
            "always_long": 0.1,
            "buy_and_hold": 0.1,
        },
    ],
)
def test_without_baseline_comparison_the_decision_is_no_decision(baselines):
    decision = dp.decide(_evidence(baselines_net_sharpe=baselines), _approved())
    assert decision["decision"] == "NO_DECISION"
    assert any("baseline" in r for r in decision["reasons"])


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"by_seed": {s: dp.SeedResult(0.3, {}) for s in _SEEDS}}, "DSR não computável"),
        (
            {"by_seed": {s: dp.SeedResult(0.3, {"N": 0.99, "2N": 0.99}) for s in _SEEDS}},
            "cenários",
        ),
        ({"by_seed": {s: dp.SeedResult(0.3, dict(_STRONG_DSR)) for s in _SEEDS[:2]}}, "seeds"),
        ({"pbo": None}, "PBO"),
        ({"dataset_sha256": None}, "sha256"),
        ({"missing_fraction": 0.5}, "qualidade"),
        ({"missing_fraction": None}, "ausentes"),
        ({"n_oos_observations": 10}, "OOS"),
        ({"registered_at_utc": "2026-09-01T00:00:00Z"}, "retroativa"),
    ],
)
def test_missing_or_invalid_evidence_never_becomes_go(overrides, fragment):
    decision = dp.decide(_evidence(**overrides), _approved())
    assert decision["decision"] == "NO_DECISION"
    assert any(fragment in r for r in decision["reasons"]), decision["reasons"]


def test_worst_case_n_scenario_and_worst_seed_decide():
    weak_5n = {**_STRONG_DSR, "5N": 0.90}
    by_seed = {s: dp.SeedResult(0.30, dict(_STRONG_DSR)) for s in _SEEDS}
    by_seed[44] = dp.SeedResult(0.30, weak_5n)
    decision = dp.decide(_evidence(by_seed=by_seed), _approved())
    assert decision["decision"] == "NO_GO"
    assert decision["worst_case"]["dsr"] == {"value": 0.90, "n_scenario": "5N", "seed": 44}

    by_seed = {s: dp.SeedResult(0.30, dict(_STRONG_DSR)) for s in _SEEDS}
    by_seed[45] = dp.SeedResult(0.11, dict(_STRONG_DSR))  # abaixo do buy_and_hold (0,12)
    assert dp.decide(_evidence(by_seed=by_seed), _approved())["decision"] == "NO_GO"
    assert dp.decide(_evidence(pbo=0.20), _approved())["decision"] == "NO_GO"


def test_thresholds_come_from_the_policy_file_not_from_code():
    strict = _approved(dsr_min=0.98)
    assert dp.decide(_evidence(), strict)["decision"] == "NO_GO"
    assert dp.decide(_evidence(), _approved())["decision"] == "GO"
    assert strict.sha256 != _approved().sha256

    source = Path(dp.__file__).read_text(encoding="utf-8")
    numbers = {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, int | float)
        and not isinstance(node.value, bool)
    }
    document = json.loads(dp.CURRENT_POLICY_PATH.read_text(encoding="utf-8"))
    policy_numbers = {
        v for v in document["thresholds"].values() if isinstance(v, int | float) and v is not True
    } | {document["pbo_n_splits"]}
    assert not numbers & policy_numbers


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["thresholds"].pop("dsr_min"),
        lambda d: d.update(status="APPROVED"),
        lambda d: d.update(
            status="APPROVED",
            effective_from_utc="2026-09-01T00:00:00Z",
            approval={"approved_by": "x", "approved_at_utc": "2026-09-24T00:00:00Z"},
        ),
        lambda d: d["dsr_n_sensitivity"].update(multipliers=[2, 5]),
        lambda d: d.update(version=0),
    ],
)
def test_invalid_policy_is_rejected(mutate):
    document = json.loads(dp.CURRENT_POLICY_PATH.read_text(encoding="utf-8"))
    mutate(document)
    with pytest.raises(dp.PolicyError):
        dp.validate_policy(document)


def test_decision_is_appended_to_the_hash_chained_ledger(tmp_path):
    ledger = RunLedger(tmp_path / "runs.jsonl")
    decision = dp.decide(_evidence(baselines_net_sharpe=None), _approved())
    record = dp.record_decision(ledger, run_id="run-x", decision=decision)
    assert record["status"] == "DECISION" and record["decision"] == "NO_DECISION"
    assert record["policy"]["sha256"] == _approved().sha256
    assert ledger.verify_chain() == []
    assert ledger.attempt_number("qualquer") == 1  # DECISION não conta como tentativa
