"""Closed local worker for admitted crypto research.

The scheduler, never the ResearchTask, chooses this module.  It consumes an
operator-materialized request and writes one immutable, deterministic domain
effect.  It has no network, trading, dynamic-import, or arbitrary-command path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path

from predictor_core.contracts.trial_v2 import (
    TRIAL_SCHEMA_VERSION,
    TrialRegistryV2,
    dataset_fingerprint,
)
from predictor_core.measurement.bootstrap import bootstrap_ci
from predictor_core.measurement.stats import max_drawdown

from GarimpoInvestimentos.durable_io import atomic_write, strict_json_loads
from GarimpoInvestimentos.v3.costs import CostModel
from GarimpoInvestimentos.v3.economic_gate import decide_cost_aware, estimate_edge


def _load(path: Path) -> dict:
    value = strict_json_loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("materialized reference must be a JSON object")
    return value


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("time requires timezone")
    return parsed


def evaluate(request: dict) -> dict:
    if (
        set(request)
        != {
            "schema",
            "experiment_id",
            "trial_id",
            "task",
            "references",
            "identities",
            "registered_at",
            "code_version",
        }
        or request["schema"] != "crypto-admitted-backtest/1"
    ):
        raise ValueError("invalid closed worker request")
    task = request["task"]
    if task["request_type"] != "BACKTEST_EXISTING_HYPOTHESIS":
        raise ValueError("handler mismatch")
    refs = {item["kind"]: _load(Path(item["path"])) for item in request["references"]}
    required = {"protocol", "dataset", "baseline", "cost_model", "evidence"}
    if set(refs) != required:
        raise ValueError("exact admitted reference kinds required")
    if refs["protocol"].get("handler") != "crypto.handlers.backtest_existing_hypothesis.v1":
        raise ValueError("protocol does not authorize this handler")

    rows = refs["dataset"].get("rows")
    if (
        not isinstance(rows, list)
        or not 4 <= len(rows) <= task["bounded_parameters"]["max_observations"]
    ):
        raise ValueError("invalid bounded dataset")
    cutoff = _utc(refs["dataset"]["data_cutoff"])
    gross: list[float] = []
    funding: list[float] = []
    prior_observed = None
    for row in rows:
        if set(row) != {"observed_at", "available_at", "gross_return", "funding_rate"}:
            raise ValueError("invalid dataset row")
        observed, available = _utc(row["observed_at"]), _utc(row["available_at"])
        if (
            available < observed
            or available > cutoff
            or (prior_observed and observed <= prior_observed)
        ):
            raise ValueError("temporal integrity failure")
        prior_observed = observed
        values = (float(row["gross_return"]), float(row["funding_rate"]))
        if any(not math.isfinite(value) for value in values):
            raise ValueError("non-finite dataset value")
        gross.append(values[0])
        funding.append(values[1])

    params = task["bounded_parameters"]
    cost_ref = refs["cost_model"]
    if (cost_ref.get("fee_bps"), cost_ref.get("slippage_bps")) != (
        params["fee_bps"],
        params["slippage_bps"],
    ):
        raise ValueError("admitted cost model conflicts with bounded parameters")
    costs = CostModel(float(cost_ref["fee_bps"]), float(cost_ref["slippage_bps"]))
    horizon_hours = float(params["horizon_days"] * 24)
    net = [
        costs.net_return(value, 1.0, rate, horizon_hours)
        for value, rate in zip(gross, funding, strict=True)
    ]
    estimate = estimate_edge(gross, minimum_sample=int(refs["protocol"]["minimum_sample"]))
    decision = decide_cost_aware(
        estimate,
        direction=1,
        funding_rate=sum(funding) / len(funding),
        horizon_hours=horizon_hours,
        costs=costs,
    )
    mean = lambda values: sum(values) / len(values)
    ci_low, ci_high, _ = bootstrap_ci(gross, mean, scheme="iid", n_boot=500, seed=17)
    equity, current = [], 1.0
    for value in net:
        current *= 1.0 + value
        if current <= 0:
            raise ValueError("invalid non-positive equity path")
        equity.append(current)
    dataset_hash = dataset_fingerprint(
        rows,
        fields=("observed_at", "available_at", "gross_return", "funding_rate"),
    ).removeprefix("sha256:")
    gross_bps = round(mean(gross) * 10_000)
    total_cost_bps = int(params["fee_bps"] + params["slippage_bps"])
    net_bps = gross_bps - total_cost_bps
    baseline_net = int(refs["baseline"]["net_return_bps"])
    scientific_state = "SUPPORTED" if ci_low > 0 else "REFUTED" if ci_high < 0 else "INCONCLUSIVE"
    economic_state = "WATCH" if decision.action == "SHADOW_TRADE" and net_bps > 0 else "NO_EDGE"
    trial = {
        "schema_version": TRIAL_SCHEMA_VERSION,
        "experiment_id": request["experiment_id"],
        "hypothesis_id": task["hypothesis_id"],
        "hypothesis_family": refs["protocol"]["hypothesis_family"],
        "trial_id": request["trial_id"],
        "registered_at": request["registered_at"],
        "executed_at": request["registered_at"],
        "seed": 17,
        "forecast_horizon": f"P{params['horizon_days']}D",
        "data_cutoff": refs["dataset"]["data_cutoff"],
        "label_start": refs["dataset"]["label_start"],
        "label_end": refs["dataset"]["label_end"],
        "dataset_hash": dataset_hash,
        "dataset_version": refs["dataset"]["dataset_version"],
        "feature_version": refs["protocol"]["feature_version"],
        "model_version": refs["protocol"]["model_version"],
        "code_version": request["code_version"],
        "params": params,
        "selection_path": refs["protocol"]["selection_path"],
        "n_trials_family": 1,
        "n_trials_domain": 1,
        "n_trials_ecosystem": 1,
        "metric": "mean_gross_return",
        "result": {"mean_gross_return": mean(gross), "ci_low": ci_low, "ci_high": ci_high},
        "status": scientific_state,
        "notes": "Deterministic frozen shadow fixture; no capital permission.",
    }
    return {
        "schema": "crypto-domain-effect/1",
        "experiment_id": request["experiment_id"],
        "trial": trial,
        "metrics": {
            "sample_size": len(gross),
            "gross_return_bps": gross_bps,
            "net_return_bps": net_bps,
            "max_drawdown_bps": -round(max_drawdown(equity) * 10_000),
            "turnover_bps": int(refs["protocol"]["turnover_bps"]),
            "ci_low_bps": round(ci_low * 10_000),
            "ci_high_bps": round(ci_high * 10_000),
        },
        "baseline_comparison": {
            "baseline_id": refs["baseline"]["baseline_id"],
            "outcome": "BEATS"
            if net_bps > baseline_net
            else "LOSES"
            if net_bps < baseline_net
            else "TIES",
            "gross_delta_bps": gross_bps - int(refs["baseline"]["gross_return_bps"]),
            "net_delta_bps": net_bps - baseline_net,
        },
        "costs": {
            "fee_bps": int(params["fee_bps"]),
            "slippage_bps": int(params["slippage_bps"]),
            "total_cost_bps": total_cost_bps,
        },
        "scientific_state": scientific_state,
        "economic_state": economic_state,
        "data_cutoff": refs["dataset"]["data_cutoff"],
        "dataset_identity": request["identities"]["dataset"],
        "model_identity": request["identities"]["protocol"],
        "feature_identity": request["identities"]["evidence"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--effect", type=Path, required=True)
    parser.add_argument("--trial-registry", type=Path, required=True)
    parser.add_argument("--fault", choices=("crash", "hang"))
    args = parser.parse_args(argv)
    if args.fault == "crash":
        os._exit(97)
    if args.fault == "hang":
        time.sleep(5)
    request = _load(args.request)
    effect = evaluate(request)
    registry = TrialRegistryV2(args.trial_registry)
    existing = next(
        (row for row in registry.load() if row["trial_id"] == effect["trial"]["trial_id"]),
        None,
    )
    if existing is None:
        registry.register(effect["trial"])
    elif existing != effect["trial"]:
        raise ValueError("existing trial identity conflicts")
    raw = (
        json.dumps(effect, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()
    expected = hashlib.sha256(raw).hexdigest()
    if args.effect.exists():
        if hashlib.sha256(args.effect.read_bytes()).hexdigest() != expected:
            raise ValueError("existing domain effect conflicts")
        return 0
    atomic_write(args.effect, raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
