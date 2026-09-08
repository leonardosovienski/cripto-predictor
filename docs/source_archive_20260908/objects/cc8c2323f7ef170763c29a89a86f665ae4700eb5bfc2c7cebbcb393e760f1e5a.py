"""Synthetic scorer controls and conditional planning; no historical price trials."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from scripts.prepare_altcoin_payoff import payoff_summary
from scripts.research_altcoin_analogs import AnalogModel


def controls():
    rng = np.random.default_rng(20260907)
    weeks = np.repeat(np.arange(80), 20)
    cluster = np.tile(np.repeat([-1, 1], 10), 80)
    x = rng.normal(0, 0.2, (1600, 8)) + cluster[:, None] * 3
    returns = np.where(cluster > 0, 0.03, -0.02) + rng.normal(0, 0.003, 1600)
    model = AnalogModel().fit(x, np.zeros(1600))
    _, _, indices = model.predict(np.array([[-3.0] * 8, [3.0] * 8]))
    train = [
        {"date": f"synthetic-{week}", "gross_return": float(r)}
        for week, r in zip(weeks, returns, strict=True)
    ]
    pattern = [payoff_summary([train[int(i)] for i in row]) for row in indices]
    assert not pattern[0]["qualified"] and pattern[1]["qualified"]
    null_qualified = 0
    null_scores = []
    # Week-common zero-log-drift variation plus asset noise. Keep geometry fixed.
    # This checks one stipulated null; it does not calibrate all financial nulls.
    for _ in range(100):
        shock = rng.normal(0, 0.03, 80)[weeks] + rng.normal(0, 0.02, 1600)
        null_train = [
            {"date": f"synthetic-{week}", "gross_return": math.expm1(float(r))}
            for week, r in zip(weeks, shock, strict=True)
        ]
        for row in indices:
            summary = payoff_summary([null_train[int(i)] for i in row])
            null_qualified += int(summary["qualified"])
            null_scores.append(summary["score_log"])
    poisoned = [dict(train[int(i)]) for i in indices[1]]
    poisoned[0]["gross_return"] = None
    assert not payoff_summary(poisoned)["qualified"]
    return {
        "seed": 20260907,
        "full_geometry_positive_and_negative_controls": pattern,
        "censored_neighbor_guard": "PASS",
        "stipulated_null_queries": len(null_scores),
        "stipulated_null_qualified": null_qualified,
        "null_score_range": [min(null_scores), max(null_scores)],
        "meaning": "Synthetic implementation checks only; neither calibrated probability nor a Core harness/power attestation or real-market edge evidence.",
    }


def power_grid():
    result = []
    # A conditional benchmark scenario already consumed in the funding screen.
    benchmark = 0.113177
    for extra_annual_pp in (0.05, 0.10, 0.20):
        delta_weekly_log = math.log((1 + benchmark + extra_annual_pp) / (1 + benchmark)) / 52
        for paired_weekly_sd in (0.01, 0.03, 0.05):
            independent_weeks = math.ceil(
                ((1.96 + 0.842) * paired_weekly_sd / delta_weekly_log) ** 2
            )
            for dependence_factor in (1, 4):
                calendar_weeks = independent_weeks * dependence_factor
                result.append(
                    {
                        "extra_annual_percentage_points": extra_annual_pp * 100,
                        "paired_weekly_log_sd_assumed": paired_weekly_sd,
                        "dependence_multiplier_assumed": dependence_factor,
                        "target_weekly_log_difference": delta_weekly_log,
                        "calendar_weeks_normal_design": calendar_weeks,
                        "calendar_years": calendar_weeks / 52,
                    }
                )
    return {
        "scenario_benchmark_annual_net": benchmark,
        "benchmark_status": "DATED_CONDITIONAL_SCENARIO_NOT_USER_CONFIRMED",
        "alpha": 0.05,
        "power": 0.8,
        "formula": "ceil(((1.96+0.842)*assumed paired weekly SD / target weekly log difference)^2) * assumed dependence multiplier",
        "limitations": "Normal-design sensitivity, not empirical attestation. Actual variance, dependence, tails, attainable benchmark, costs, risk premium, selection and full search adjustment are unresolved. Means and SDs share weekly log-return units. Twelve calendar weeks are not twelve independent observations automatically.",
        "grid": result,
        "twelve_week_pilot_purpose": "Operational feasibility and new descriptive observations; never declare profitability solely because 12 weeks passed.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = {
        "synthetic_controls": controls(),
        "power_planning": power_grid(),
        "formal_attestation": False,
        "historical_performance_trials": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "controls": output["synthetic_controls"],
                "minimum_conditional_years": min(
                    x["calendar_years"] for x in output["power_planning"]["grid"]
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
