"""Prompt 3c: métricas de previsão probabilística e avaliação pré-registrada do Chronos zero-shot.

Sem rede, sem torch/chronos: a etapa de previsão é substituída por documentos sintéticos; os
dados reais só são lidos para conferir o hash pré-registrado.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import random
import statistics
import zipfile
from datetime import UTC, datetime
from statistics import NormalDist

import pytest

from GarimpoInvestimentos.research import fm_zero_shot as fz
from GarimpoInvestimentos.research.forecast_metrics import (
    crps_from_quantiles,
    crps_gaussian,
    mean_quantile_loss,
    pinball_loss,
    weighted_quantile_loss,
)
from GarimpoInvestimentos.run_ledger import RunLedger

DAY = fz.DAY_MS
LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
START = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp() * 1000)


# ---------------------------------------------------------------- métricas


def test_pinball_and_crps_by_hand():
    assert pinball_loss(1.0, 0.0, 0.9) == pytest.approx(0.9)
    assert pinball_loss(-1.0, 0.0, 0.9) == pytest.approx(0.1)
    forecast = {0.1: -1.0, 0.5: 0.0, 0.9: 1.0}
    # y = 0,5: ρ0,1 = 1,5·0,1 = 0,15; ρ0,5 = 0,5·0,5 = 0,25; ρ0,9 = (−0,5)(−0,1) = 0,05
    assert mean_quantile_loss(0.5, forecast) == pytest.approx(0.15)
    assert crps_from_quantiles(0.5, forecast) == pytest.approx(0.30)
    # WQL: 2·Σρ / (K·Σ|y|) = 2·(0,45 + 0,45) / (3·(0,5 + 0,5)) com y = ±0,5 simétricos
    assert weighted_quantile_loss([0.5, -0.5], [forecast, forecast]) == pytest.approx(0.6)


def test_crps_gaussian_closed_form_and_quantile_approximation():
    # Gneiting & Raftery (2007): CRPS(N(0,1), 0) = 2φ(0) − 1/√π = (√2 − 1)/√π
    assert crps_gaussian(0.0, 0.0, 1.0) == pytest.approx((math.sqrt(2) - 1) / math.sqrt(math.pi))
    nd = NormalDist(0.1, 2.0)
    dense = {k / 1000: nd.inv_cdf(k / 1000) for k in range(1, 1000)}
    assert crps_from_quantiles(1.3, dense) == pytest.approx(crps_gaussian(1.3, 0.1, 2.0), rel=5e-3)


def test_crossed_or_non_finite_quantiles_are_rejected():
    with pytest.raises(ValueError):
        mean_quantile_loss(0.0, {0.1: 1.0, 0.9: -1.0})
    with pytest.raises(ValueError):
        mean_quantile_loss(0.0, {0.1: float("nan"), 0.9: 1.0})


def test_empirical_quantile_is_hyndman_fan_type_7():
    rng = random.Random(1)
    values = sorted(rng.gauss(0, 1) for _ in range(365))
    expected = statistics.quantiles(values, n=10, method="inclusive")
    assert [fz.empirical_quantile(values, t) for t in LEVELS] == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------- dados e contaminação


def _series_payload(closes, start=START):
    rows = [
        [start + i * DAY, c, c, c, c, 1.0, c, start + (i + 1) * DAY - 1]
        for i, c in enumerate(closes)
    ]
    return {
        "columns": [
            "open_ms",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "close_ms",
        ],
        "rows": rows,
    }


def _data_block(tmp_path, closes):
    member_bytes = gzip.compress(json.dumps(_series_payload(closes)).encode(), mtime=0)
    archive = tmp_path / "data.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("s/BTCUSDT.json.gz", member_bytes)
    return {
        "archive": str(archive),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "member": "s/BTCUSDT.json.gz",
        "member_sha256": hashlib.sha256(member_bytes).hexdigest(),
        "field": "close",
        "first_open_utc": _iso(START),
        "last_open_utc": _iso(START + (len(closes) - 1) * DAY),
        "rows": len(closes),
    }


def _iso(ms):
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _closes(n, seed=7):
    rng = random.Random(seed)
    price, out = 100.0, []
    for _ in range(n):
        price *= math.exp(rng.gauss(0.0005, 0.02))
        out.append(price)
    return out


def test_preregistered_real_data_matches_its_hashes():
    prereg, _ = fz.load_preregistration()
    series = fz.load_daily_series(prereg["data"])
    assert len(series.close) == prereg["data"]["rows"] == 2167
    tampered = {**prereg["data"], "member_sha256": "0" * 64}
    with pytest.raises(fz.DataIntegrityError):
        fz.load_daily_series(tampered)


def test_series_with_gap_or_wrong_period_is_rejected(tmp_path):
    data = _data_block(tmp_path, _closes(30))
    series = fz.load_daily_series(data, root=tmp_path)
    opens = list(series.open_ms)
    opens[10] += DAY
    with pytest.raises(fz.DataIntegrityError):
        fz.validate_series(opens, series.close, data, member_sha256="x")
    with pytest.raises(fz.DataIntegrityError):
        fz.validate_series(series.open_ms, series.close, {**data, "rows": 31}, member_sha256="x")


def test_targets_are_post_cutoff_and_no_post_cutoff_is_flagged(tmp_path):
    series = fz.load_daily_series(_data_block(tmp_path, _closes(30)), root=tmp_path)
    cutoff = START + 20 * DAY + 5
    idx = fz.target_indices(series, first_ms=START + 21 * DAY, last_ms=START + 29 * DAY)
    assert idx == list(range(21, 30))
    assert fz.contamination_status(series, idx, cutoff) == "POST_CUTOFF"
    assert all(series.open_ms[j] >= cutoff for j in idx)
    assert fz.contamination_status(series, [], cutoff) == "POTENTIALLY_CONTAMINATED"
    with pytest.raises(fz.DataIntegrityError):
        fz.contamination_status(series, [5, 21], cutoff)


def test_baselines_only_use_returns_up_to_the_origin():
    rng = random.Random(3)
    returns = [float("nan")] + [rng.gauss(0, 0.02) for _ in range(399)]
    before = fz.baseline_forecasts(returns, [380], LEVELS)
    changed = returns[:380] + [9.9] * 20  # muda o alvo e o futuro
    after = fz.baseline_forecasts(changed, [380], LEVELS)
    assert before == after
    with pytest.raises(fz.DataIntegrityError):
        fz.baseline_forecasts(returns, [100], LEVELS)  # menos de 365 dias de histórico


# ---------------------------------------------------------------- estratégia e poder


def test_strategy_accounting_by_hand():
    net = fz.strategy_net_returns([1, 1, 0, 1], [0.01, -0.02, 0.03, 0.01], 0.0015)
    assert net == pytest.approx([0.0085, -0.02, -0.0015, 0.007])
    assert fz.long_flat_positions([0.1, 0.0, -0.2]) == [1.0, 0.0, 0.0]


def test_power_formulas_by_hand():
    z = NormalDist().inv_cdf(0.975) + NormalDist().inv_cdf(0.8)
    assert fz.mde_sharpe_annual(650, periods_per_year=365, alpha=0.05, power=0.8) == pytest.approx(
        z * math.sqrt(365 / 650)
    )
    diffs = [0.1, -0.1] * 50
    assert fz.mde_relative(diffs, 2.0, alpha=0.05, power=0.8) == pytest.approx(
        z * statistics.stdev(diffs) / 10 / 2.0
    )


def test_transcribed_constants_match_the_preregistration_text():
    prereg, _ = fz.load_preregistration()
    assert "alpha 0,05" in prereg["forecast_metrics"]["test"] and fz._ALPHA == 0.05
    assert (
        "5%" in prereg["forecast_metrics"]["relevant_effect"]
        and fz._RELEVANT_FORECAST_EFFECT == 0.05
    )
    assert all(name.endswith(f"_{fz._BASELINE_WINDOW}") for name in prereg["forecast_baselines"])
    assert list(prereg["forecast_baselines"]) == list(fz.FORECAST_BASELINES)


# ---------------------------------------------------------------- avaliação ponta a ponta


def _synthetic_prereg(tmp_path, closes, *, cutoff_day, first_day, last_day):
    real, _ = fz.load_preregistration()
    prereg = json.loads(json.dumps(real))
    prereg["data"] = _data_block(tmp_path, closes)
    prereg["contamination"]["cutoff_utc"] = _iso(START + cutoff_day * DAY + 1000)
    prereg["evaluation_period"] = {
        "first_target_open_utc": _iso(START + first_day * DAY),
        "last_target_open_utc": _iso(START + last_day * DAY),
    }
    return prereg


def _forecast_doc(prereg, series, indices, *, scale=0.02, shift=0.0):
    nd = NormalDist()
    forecasts = {}
    for j in indices:
        origin = series.close[j - 1]
        forecasts[str(series.open_ms[j])] = [
            origin * math.exp(shift + scale * nd.inv_cdf(t)) for t in LEVELS
        ]
    candidate = prereg["candidate"]
    return {
        "model": {k: candidate[k] for k in ("model_id", "revision", "weights_sha256")},
        "quantile_levels": LEVELS,
        "run_id": "synthetic",
        "forecasts": forecasts,
    }


def test_end_to_end_evaluation_never_becomes_go_without_policy_and_dsr(tmp_path):
    closes = _closes(700)
    prereg = _synthetic_prereg(tmp_path, closes, cutoff_day=449, first_day=450, last_day=699)
    series = fz.load_daily_series(prereg["data"], root=tmp_path)
    idx = fz.target_indices(series, first_ms=START + 450 * DAY, last_ms=START + 699 * DAY)
    report = fz.evaluate(prereg, series, _forecast_doc(prereg, series, idx))
    assert report["contamination_status"] == "POST_CUTOFF" and report["n_targets"] == 250
    assert set(report["forecast"]) == {"chronos_bolt_small", *fz.FORECAST_BASELINES}
    assert report["forecast_status"] in {
        "INSUFFICIENT_SAMPLE",
        "CANDIDATE_BETTER",
        "CANDIDATE_WORSE",
        "NO_SIGNIFICANT_DIFFERENCE",
    }
    assert report["strategy_status"] == "INSUFFICIENT_SAMPLE"  # 250 dias: MDE ≈ 3,4 > 1
    assert report["dsr"]["status"] == "NOT_ESTIMABLE"
    assert report["pbo"]["status"] == "N/A"
    assert report["decision"]["decision"] == "NO_DECISION"
    assert report["decision"]["policy"]["id"] == "cripto-decision-policy"
    assert report["strategy"]["buy_and_hold"] == report["strategy"]["always_long"]


def test_evaluation_without_post_cutoff_targets_is_potentially_contaminated(tmp_path):
    prereg = _synthetic_prereg(tmp_path, _closes(400), cutoff_day=500, first_day=500, last_day=600)
    series = fz.load_daily_series(prereg["data"], root=tmp_path)
    report = fz.evaluate(prereg, series, {"forecasts": {}})
    assert report == {"contamination_status": "POTENTIALLY_CONTAMINATED", "n_targets": 0}


def test_forecast_from_another_checkpoint_or_missing_day_is_rejected(tmp_path):
    closes = _closes(700)
    prereg = _synthetic_prereg(tmp_path, closes, cutoff_day=449, first_day=450, last_day=699)
    series = fz.load_daily_series(prereg["data"], root=tmp_path)
    idx = fz.target_indices(series, first_ms=START + 450 * DAY, last_ms=START + 699 * DAY)
    doc = _forecast_doc(prereg, series, idx)
    wrong = {**doc, "model": {**doc["model"], "revision": "outra"}}
    with pytest.raises(fz.DataIntegrityError):
        fz.evaluate(prereg, series, wrong)
    missing = {**doc, "forecasts": dict(list(doc["forecasts"].items())[1:])}
    with pytest.raises(fz.DataIntegrityError):
        fz.evaluate(prereg, series, missing)


def test_every_evaluation_is_in_the_ledger_including_crashes(tmp_path):
    closes = _closes(700)
    prereg = _synthetic_prereg(tmp_path, closes, cutoff_day=449, first_day=450, last_day=699)
    series = fz.load_daily_series(prereg["data"], root=tmp_path)
    idx = fz.target_indices(series, first_ms=START + 450 * DAY, last_ms=START + 699 * DAY)
    prereg_path = tmp_path / "prereg.json"
    prereg_path.write_text(json.dumps(prereg), encoding="utf-8")
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_forecast_doc(prereg, series, idx)), encoding="utf-8")
    bad = tmp_path / "bad.json"
    doc = _forecast_doc(prereg, series, idx)
    doc["model"]["weights_sha256"] = "0" * 64
    bad.write_text(json.dumps(doc), encoding="utf-8")
    ledger_path = tmp_path / "runs.jsonl"
    report = fz.run_evaluation(
        prereg_path=prereg_path,
        forecasts_path=good,
        out_path=tmp_path / "r.json",
        ledger_path=ledger_path,
    )
    with pytest.raises(fz.DataIntegrityError):
        fz.run_evaluation(
            prereg_path=prereg_path,
            forecasts_path=bad,
            out_path=tmp_path / "r2.json",
            ledger_path=ledger_path,
        )
    ledger = RunLedger(ledger_path)
    statuses = [(r["kind"], r["status"]) for r in ledger.records()]
    assert statuses == [
        ("fm_zero_shot_evaluation", "STARTED"),
        ("fm_zero_shot_evaluation", "COMPLETED"),
        ("fm_zero_shot_evaluation", "STARTED"),
        ("fm_zero_shot_evaluation", "CRASHED"),
    ]
    assert ledger.verify_chain() == []
    started = ledger.records()[0]
    assert started["policy"]["id"] == "cripto-decision-policy"
    assert (
        ledger.records()[1]["metrics"]["decision"]
        == report["decision"]["decision"]
        == "NO_DECISION"
    )
