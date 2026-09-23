"""Closed local worker for admitted crypto research (handler backtest_existing_hypothesis.v1).

The executor, never the request, chooses this module; predictor_ops runs it as a child
process. It consumes an operator-materialized request and writes one immutable,
deterministic domain effect plus one Core trial row. It has no network, trading,
dynamic-import or arbitrary-command path.

Core participation (predictor_core, frozen wheel):
  * temporal validation: predictor_core.measurement.replay (LookaheadError when a row is
    available after the data cutoff; ValueError when observations are not monotonic);
  * the signal only ever sees the past (replay feeds a PastView per observation);
  * statistics: predictor_core.measurement.bootstrap.bootstrap_ci (gross and net) and
    predictor_core.measurement.stats.max_drawdown;
  * trial identity: predictor_core.contracts.trial_v2 (dataset_fingerprint, TrialRegistryV2).

Exit codes: 0 effect written; 4 temporal integrity violation; 5 contract refusal;
6 reference integrity violation. All three write worker-refusal.json next to the effect
and never write an effect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import time
from datetime import datetime
from pathlib import Path

from predictor_core.contracts.trial_v2 import (
    TRIAL_SCHEMA_VERSION,
    TrialRegistryV2,
    dataset_fingerprint,
)
from predictor_core.measurement.bootstrap import bootstrap_ci
from predictor_core.measurement.replay import LookaheadError, replay
from predictor_core.measurement.stats import max_drawdown

from GarimpoInvestimentos.durable_io import atomic_write, strict_json_loads
from GarimpoInvestimentos.v3.costs import CostModel
from GarimpoInvestimentos.v3.economic_gate import decide_cost_aware, estimate_edge

HANDLER = "crypto.handlers.backtest_existing_hypothesis.v1"
EXIT_TEMPORAL = 4
EXIT_REFUSED = 5
EXIT_INTEGRITY = 6
CI = {"scheme": "iid", "n_boot": 500, "seed": 17, "confidence": 0.95}
ROW_FIELDS = ("observed_at", "available_at", "gross_return", "funding_rate")


class TemporalViolation(ValueError):
    pass


class Refusal(ValueError):
    pass


class IntegrityViolation(ValueError):
    pass


def _load(path: Path) -> dict:
    value = strict_json_loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Refusal("materialized reference must be a JSON object")
    return value


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise Refusal("malformed timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Refusal("malformed timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TemporalViolation("time requires timezone")
    return parsed


def _frozen_families() -> set[str]:
    from GarimpoInvestimentos.governance import load_scientific_state

    return set(load_scientific_state().frozen_families)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _bps(value: float) -> int:
    return round(value * 10_000)


def _quality_problem(rows: list) -> str | None:
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != set(ROW_FIELDS):
            return f"row {index}: fields"
        for field in ("gross_return", "funding_rate"):
            value = row[field]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                return f"row {index}: {field} not finite number"
        if abs(row["gross_return"]) >= 1.0 or abs(row["funding_rate"]) >= 0.05:
            return f"row {index}: implausible magnitude"
        if row["observed_at"] in seen:
            return f"row {index}: duplicate observed_at"
        seen.add(row["observed_at"])
    return None


def temporal_validation(rows: list, cutoff_text: str) -> dict:
    """Core replay enforces the PIT inequality available_at <= data_cutoff and ordering."""
    cutoff = _utc(cutoff_text)
    events = tuple((_utc(r["observed_at"]), _utc(r["available_at"])) for r in rows)
    for observed, available in events:
        if available < observed:
            raise TemporalViolation("row available before it was observed")
    try:
        replay(events, lambda past: None, key=lambda e: e[0])  # monotonic observation time
        replay(events, lambda past: None, key=lambda e: cutoff, available_at=lambda e: e[1])
    except LookaheadError as exc:
        raise TemporalViolation(f"LookaheadError: {exc}") from exc
    except ValueError as exc:
        raise TemporalViolation(f"replay: {exc}") from exc
    return {
        "method": "predictor_core.measurement.replay",
        "inequality": "available_at <= data_cutoff and observed_at monotonic and observed_at <= available_at",
        "rows": len(rows),
        "data_cutoff": cutoff_text,
        "max_available_at": max(r["available_at"] for r in rows) if rows else None,
        "status": "PASS",
    }


def directions(rows: list, placebo_seed: int | None) -> list[int]:
    """Signal decided through Core replay: the handler only receives the past."""
    rng = random.Random(placebo_seed) if placebo_seed is not None else None

    def handler(past):
        # Fixed shadow signal: long one unit each non-overlapping observation.
        # Placebo control: sign drawn independently of any data.
        return 1 if rng is None else rng.choice((-1, 1))

    return replay(tuple(rows), handler)


def evaluate(request: dict) -> dict:
    expected = {
        "schema",
        "experiment_id",
        "trial_id",
        "request",
        "references",
        "identities",
        "registered_at",
        "code_version",
    }
    if set(request) != expected or request["schema"] != "crypto-admitted-backtest/2":
        raise Refusal("invalid closed worker request")
    task = request["request"]
    if task["request_type"] != "BACKTEST_EXISTING_HYPOTHESIS":
        raise Refusal("handler mismatch")
    for item in request["references"]:
        observed = hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()
        if observed != request["identities"].get(item["kind"]):
            raise IntegrityViolation(f"reference {item['kind']} changed after materialization")
    refs = {item["kind"]: _load(Path(item["path"])) for item in request["references"]}
    if set(refs) != {"protocol", "dataset", "baseline", "cost_model", "evidence"}:
        raise Refusal("exact admitted reference kinds required")
    protocol, dataset = refs["protocol"], refs["dataset"]
    if protocol.get("handler") != HANDLER:
        raise Refusal("protocol does not authorize this handler")
    if protocol.get("hypothesis_family") in _frozen_families():
        raise Refusal("FROZEN_FAMILY: protocol belongs to a frozen family")
    params = task["parameters"]
    if dataset.get("data_cutoff") != task["data_cutoff"]:
        raise TemporalViolation("dataset data_cutoff differs from the requested data_cutoff")
    cost_ref = refs["cost_model"]
    if (cost_ref.get("fee_bps"), cost_ref.get("slippage_bps")) != (
        params["fee_bps"],
        params["slippage_bps"],
    ):
        raise Refusal("admitted cost model conflicts with request parameters")
    rows = dataset.get("rows")
    if not isinstance(rows, list) or not rows:
        raise Refusal("dataset without rows")
    if len(rows) > params["max_observations"]:
        raise Refusal("dataset exceeds max_observations")
    base = {
        "schema": "crypto-domain-effect/2",
        "experiment_id": request["experiment_id"],
        "data_cutoff": task["data_cutoff"],
        "temporal_validation": None,
        "identities": request["identities"],
        "placebo_seed": params.get("placebo_seed"),
    }
    shape = next(
        (
            f"row {i}: fields"
            for i, r in enumerate(rows)
            if not isinstance(r, dict) or set(r) != set(ROW_FIELDS)
        ),
        None,
    )
    if shape is not None:
        return base | {
            "result_state": "INCONCLUSIVE_DATA_QUALITY",
            "scientific_state": "NOT_EVALUATED",
            "economic_state": "NOT_EVALUATED",
            "data_quality": {"ok": False, "problem": shape},
            "trial": None,
            "metrics": {"sample_size": len(rows)},
            "costs": None,
            "baseline_comparison": None,
        }
    base["temporal_validation"] = temporal_validation(
        rows, task["data_cutoff"]
    )  # before any statistic
    quality = _quality_problem(rows)
    minimum = int(protocol["minimum_sample"])
    if quality is not None:
        return base | {
            "result_state": "INCONCLUSIVE_DATA_QUALITY",
            "scientific_state": "NOT_EVALUATED",
            "economic_state": "NOT_EVALUATED",
            "data_quality": {"ok": False, "problem": quality},
            "trial": None,
            "metrics": {"sample_size": len(rows)},
            "costs": None,
            "baseline_comparison": None,
        }
    if len(rows) < minimum:
        return base | {
            "result_state": "CLOSED_INSUFFICIENT_SAMPLE",
            "scientific_state": "INSUFFICIENT_SAMPLE",
            "economic_state": "NOT_EVALUATED",
            "data_quality": {"ok": True},
            "trial": None,
            "metrics": {"sample_size": len(rows), "minimum_sample": minimum},
            "costs": None,
            "baseline_comparison": None,
        }

    signs = directions(rows, params.get("placebo_seed"))
    costs = CostModel(float(cost_ref["fee_bps"]), float(cost_ref["slippage_bps"]))
    horizon_hours = float(params["horizon_days"] * 24)
    gross = [d * float(r["gross_return"]) for d, r in zip(signs, rows, strict=True)]
    net = [
        costs.net_return(g, float(d), float(r["funding_rate"]), horizon_hours)
        for g, d, r in zip(gross, signs, rows, strict=True)
    ]
    friction = [costs.friction(float(d)) for d in signs]
    funding_pnl = [
        costs.funding_pnl(float(d), float(r["funding_rate"]), horizon_hours)
        for d, r in zip(signs, rows, strict=True)
    ]
    g_lo, g_hi, _ = bootstrap_ci(gross, _mean, **CI)
    n_lo, n_hi, _ = bootstrap_ci(net, _mean, **CI)
    equity, current = [], 1.0
    for value in net:
        current *= 1.0 + value
        if current <= 0:
            return base | {
                "result_state": "INCONCLUSIVE_DATA_QUALITY",
                "scientific_state": "NOT_EVALUATED",
                "economic_state": "NOT_EVALUATED",
                "data_quality": {"ok": False, "problem": "non-positive equity path"},
                "trial": None,
                "metrics": {"sample_size": len(rows)},
                "costs": None,
                "baseline_comparison": None,
            }
        equity.append(current)
    scientific = "SUPPORTED" if g_lo > 0 else "REFUTED" if g_hi < 0 else "INCONCLUSIVE"
    estimate = estimate_edge(gross, minimum_sample=minimum)
    decision = decide_cost_aware(
        estimate,
        direction=1,
        funding_rate=_mean([float(r["funding_rate"]) for r in rows]),
        horizon_hours=horizon_hours,
        costs=costs,
    )
    economic = (
        "WATCH"
        if scientific == "SUPPORTED" and n_lo > 0 and decision.action == "SHADOW_TRADE"
        else "NO_EDGE"
    )
    result_state = {
        ("SUPPORTED", "WATCH"): "WATCH_NO_CAPITAL",
        ("SUPPORTED", "NO_EDGE"): "NO_EDGE",
        ("INCONCLUSIVE", "NO_EDGE"): "INCONCLUSIVE",
        ("REFUTED", "NO_EDGE"): "REFUTED",
    }[(scientific, economic)]
    gross_bps, net_bps = _bps(_mean(gross)), _bps(_mean(net))
    baseline = refs["baseline"]
    dataset_hash = dataset_fingerprint(rows, fields=ROW_FIELDS).removeprefix("sha256:")
    trial = {
        "schema_version": TRIAL_SCHEMA_VERSION,
        "experiment_id": request["experiment_id"],
        "hypothesis_id": task["hypothesis_id"],
        "hypothesis_family": protocol["hypothesis_family"],
        "trial_id": request["trial_id"],
        "registered_at": request["registered_at"],
        "executed_at": request["registered_at"],
        "seed": CI["seed"],
        "forecast_horizon": f"P{params['horizon_days']}D",
        "data_cutoff": task["data_cutoff"],
        "label_start": dataset["label_start"],
        "label_end": dataset["label_end"],
        "dataset_hash": dataset_hash,
        "dataset_version": dataset["dataset_version"],
        "feature_version": protocol["feature_version"],
        "model_version": protocol["model_version"],
        "code_version": request["code_version"],
        "params": params,
        "selection_path": protocol["selection_path"],
        "n_trials_family": 1,
        "n_trials_domain": 1,
        "n_trials_ecosystem": 1,
        "metric": "mean_signed_gross_return",
        "result": {
            "mean_gross_return": _mean(gross),
            "gross_ci_low": g_lo,
            "gross_ci_high": g_hi,
            "mean_net_return": _mean(net),
            "net_ci_low": n_lo,
            "net_ci_high": n_hi,
        },
        "status": scientific,
        "notes": "placebo control"
        if params.get("placebo_seed") is not None
        else "fixed shadow signal; no capital permission",
    }
    return base | {
        "result_state": result_state,
        "scientific_state": scientific,
        "economic_state": economic,
        "data_quality": {"ok": True},
        "trial": trial,
        "metrics": {
            "sample_size": len(rows),
            "gross_return_bps": gross_bps,
            "net_return_bps": net_bps,
            "gross_ci_low_bps": _bps(g_lo),
            "gross_ci_high_bps": _bps(g_hi),
            "net_ci_low_bps": _bps(n_lo),
            "net_ci_high_bps": _bps(n_hi),
            "ci": CI,
            "max_drawdown_bps": -_bps(max_drawdown(equity)),
            "turnover_round_trips": sum(1 for d in signs if d != 0),
            "long_observations": sum(1 for d in signs if d > 0),
            "short_observations": sum(1 for d in signs if d < 0),
        },
        "costs": {
            "model": "GarimpoInvestimentos.v3.costs.CostModel",
            "taker_fee_bps_per_leg": int(params["fee_bps"]),
            "slippage_bps_per_leg": int(params["slippage_bps"]),
            "round_trip_friction_bps": _bps(_mean(friction)),
            "mean_funding_pnl_bps": _bps(_mean(funding_pnl)),
            "mean_total_cost_bps": gross_bps - net_bps,
            "cost_aware_decision": decision.action,
        },
        "baseline_comparison": {
            "baseline_id": baseline["baseline_id"],
            "outcome": "BEATS"
            if net_bps > int(baseline["net_return_bps"])
            else "LOSES"
            if net_bps < int(baseline["net_return_bps"])
            else "TIES",
            "gross_delta_bps": gross_bps - int(baseline["gross_return_bps"]),
            "net_delta_bps": net_bps - int(baseline["net_return_bps"]),
        },
    }


def _refuse(path: Path, code: int, error: Exception) -> int:
    atomic_write(
        path,
        json.dumps(
            {"exit_code": code, "kind": type(error).__name__, "reason": str(error)[:1000]},
            sort_keys=True,
        ).encode(),
    )
    return code


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
        time.sleep(600)
    refusal = args.effect.with_name("worker-refusal.json")
    try:
        effect = evaluate(_load(args.request))
    except TemporalViolation as exc:
        return _refuse(refusal, EXIT_TEMPORAL, exc)
    except IntegrityViolation as exc:
        return _refuse(refusal, EXIT_INTEGRITY, exc)
    except Refusal as exc:
        return _refuse(refusal, EXIT_REFUSED, exc)
    if effect["trial"] is not None:
        registry = TrialRegistryV2(args.trial_registry)
        existing = next(
            (row for row in registry.load() if row["trial_id"] == effect["trial"]["trial_id"]), None
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
