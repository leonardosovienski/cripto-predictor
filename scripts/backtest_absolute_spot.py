"""One registered cross-sectional momentum rule and frozen-selector diagnosis."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

from scripts.backtest_altcoin_payoff import (
    BASE,
    attach_outcomes,
    feature_rows,
    load_histories,
    summarize,
    write,
)


def concentration(increments: list[float]) -> dict:
    positive = sorted((v for v in increments if v > 0), reverse=True)
    top = sum(positive[:5])
    return {
        "net_profit_usdt": sum(increments),
        "positive_increment_sum_usdt": sum(positive),
        "top_five_positive_sum_usdt": top,
        "top_five_share_of_positive_increments": top / sum(positive) if positive else None,
        "profit_less_top_five_increments_usdt": sum(increments) - top,
        "exclusion_meaning": "Arithmetic contribution diagnostic, not a rerun with those trades removed or a new strategy.",
    }


def block_interval(increments: list[float]) -> dict:
    values = np.asarray(increments, dtype=float)
    if len(values) < 8 or not np.isfinite(values).all() or values.std() == 0:
        return {
            "mean_weekly_pnl_usdt": None,
            "interval_95_usdt": None,
            "reason": "INSUFFICIENT_OR_DEGENERATE",
        }
    rng = np.random.default_rng(20260908)
    n = len(values)
    starts = rng.integers(n, size=(5000, math.ceil(n / 4)))
    indices = ((starts[:, :, None] + np.arange(4)) % n).reshape(5000, -1)[:, :n]
    return {
        "mean_weekly_pnl_usdt": float(values.mean()),
        "interval_95_usdt": np.quantile(values[indices].mean(axis=1), [0.025, 0.975]).tolist(),
        "meaning": "Descriptive four-week circular bootstrap, conditional on adaptive history; neither independent nor search-adjusted.",
    }


def momentum_decisions(data: dict):
    records, days = feature_rows(data)
    grouped = {d: [] for d in days}
    for row in records:
        idx = (date.fromisoformat(row["date"]) - BASE).days
        close = data[row["symbol"]][: idx - 1, 3]
        r30 = float(np.log(close[-1] / close[-31]))
        r7 = float(np.log(close[-1] / close[-8]))
        grouped[row["date"]].append(
            {
                "symbol": row["symbol"],
                "r30": r30,
                "r7": r7,
                "median_quote_volume": row["median_quote_volume_30d"],
            }
        )
    decisions = []
    for day in days:
        eligible = grouped[day]
        qualified = sorted(
            (r for r in eligible if r["r30"] > 0 and r["r7"] > 0),
            key=lambda r: (-r["r30"], r["symbol"]),
        )
        selected = [r["symbol"] for r in qualified[:5]] if len(eligible) >= 10 else []
        decisions.append(
            {
                "date": day,
                "eligible": len(eligible),
                "qualified": len(qualified),
                "selected": selected,
                "selected_past_features": qualified[:5] if selected else [],
                "cash_weight": 1 - 0.2 * len(selected),
                "selection_status": "SELECTED" if selected else "CASH",
            }
        )
    return decisions


def selector_diagnosis(scores_path: Path) -> dict:
    scores = json.loads(gzip.decompress(scores_path.read_bytes()))
    known = [r for r in scores if r.get("score_log") is not None]
    positive_mean = [r for r in known if r["mean_log_payoff"] > 0]
    return {
        "source": "Preserved v5 scores.json.gz",
        "source_sha256": hashlib.sha256(scores_path.read_bytes()).hexdigest(),
        "observations": len(scores),
        "status_counts": dict(Counter(r["status"] for r in scores)),
        "scorable": len(known),
        "positive_mean_after_frozen_cost_before_penalty": len(positive_mean),
        "positive_after_penalty": sum(r["score_log"] > 0 for r in known),
        "mean_log_payoff_quantiles": np.quantile(
            [r["mean_log_payoff"] for r in known], [0, 0.25, 0.5, 0.75, 1]
        ).tolist(),
        "penalty_log_quantiles": np.quantile(
            [r["uncertainty_penalty_log"] for r in known], [0, 0.25, 0.5, 0.75, 1]
        ).tolist(),
        "distinct_training_weeks_range": [
            min(r["distinct_weeks"] for r in known),
            max(r["distinct_weeks"] for r in known),
        ],
        "effective_n_range": [
            min(r["effective_n_heuristic"] for r in known),
            max(r["effective_n_heuristic"] for r in known),
        ],
        "best_frozen_score": max(r["score_log"] for r in known),
        "interpretation": "Abstention is explained by training conditional means, heuristic week-dependent uncertainty penalty and censored neighbors. This decomposition does not show that removing the penalty would be profitable. No threshold variant was evaluated.",
    }


def run_spot(history: Path, output: Path, root: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    manifest, data = load_histories(history)
    decisions = momentum_decisions(data)
    write(output / "decisions.json", decisions)
    resolutions = json.loads(
        (root / "docs/evidence/altcoin_payoff_20260907/results.json").read_text(encoding="utf-8")
    )["identity_resolutions"]
    weeks = attach_outcomes(decisions, data, resolutions)
    write(output / "weekly_results.json", weeks)
    report = {
        "id": "AR3_UNIVERSE",
        "overall": summarize(weeks),
        "by_entry_year": {
            str(y): summarize([w for w in weeks if w["date"].startswith(str(y))])
            for y in (2024, 2025, 2026)
        },
        "concentration": {},
        "registered_bootstrap": {},
        "symbol_contributions_usdt_primary": {},
        "daily_bar_count": manifest["total_rows"],
        "catalog_symbols": len(manifest["selected"]),
        "unresolved": [h for w in weeks for h in w["holdings"] if h["gross_return"] is None],
    }
    for cost in (0, 10, 40, 90):
        equity = 5000.0
        increments = []
        contributions = Counter()
        for week in weeks:
            factor = week["factors_by_extra_bps"][str(cost)]
            if factor is None:
                increments = []
                break
            for h in week["holdings"]:
                contributions[h["symbol"]] += (
                    0.2 * equity * h["net_returns_by_extra_bps"][str(cost)]
                )
            next_equity = equity * factor
            increments.append(next_equity - equity)
            equity = next_equity
        report["concentration"][str(cost)] = concentration(increments) if increments else None
        report["registered_bootstrap"][str(cost)] = block_interval(increments)
        if cost == 10 and increments:
            report["symbol_contributions_usdt_primary"] = dict(contributions.most_common())
    adverse = report["overall"]["cost_scenarios"]["40"]["simulated_profit_5000_usdt"]
    ci = report["registered_bootstrap"]["40"]["interval_95_usdt"]
    report["future_observation_candidate"] = bool(
        adverse is not None and adverse > 0 and ci and ci[0] > 0
    )
    report["executable_ready"] = False
    report["measured_investor_net_profit"] = None
    write(output / "results.json", report)
    return report
