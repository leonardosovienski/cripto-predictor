"""Offline, fixed-specification pre-rally analog Discovery screen.

Nothing in this module submits orders, changes production or promotes a trial.
The protocol is the specification; synthetic controls must pass before results.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from sklearn.neighbors import NearestNeighbors

from scripts.collect_altcoin_analogs import PROTOCOL, select_symbols

EPOCH = date(1970, 1, 1)
BASE = date(2020, 10, 1)
CUTOFF = date(2026, 9, 7)
DAY_MS = 86_400_000
FEATURE_NAMES = [
    "log_return_1d",
    "excess_log_return_7d",
    "excess_log_return_30d",
    "log_volume_acceleration",
    "volatility_30d",
    "log_distance_30d_high",
    "mean_range_7d",
    "btc_log_return_30d",
]


def extract_features(bars: np.ndarray, btc: np.ndarray, entry_index: int):
    """Read exactly 90 past bars through entry-2; never read entry-1 or later.

    Columns: open, high, low, close, base volume, quote volume.
    """
    window = bars[entry_index - 91 : entry_index - 1]
    reference = btc[entry_index - 91 : entry_index - 1]
    if len(window) != 90 or len(reference) != 90:
        return None
    if not np.isfinite(window).all() or not np.isfinite(reference).all():
        return None
    if (window <= 0).any() or (reference <= 0).any():
        return None
    quote_median = float(np.median(window[-30:, 5]))
    if quote_median < 5_000_000:
        return None
    close, bc = window[:, 3], reference[:, 3]
    btc_r7 = np.log(bc[-1] / bc[-8])
    btc_r30 = np.log(bc[-1] / bc[-31])
    values = np.array(
        [
            np.log(close[-1] / close[-2]),
            np.log(close[-1] / close[-8]) - btc_r7,
            np.log(close[-1] / close[-31]) - btc_r30,
            np.log(window[-7:, 5].mean() / window[-30:-7, 5].mean()),
            np.std(np.diff(np.log(close[-31:])), ddof=0),
            np.log(close[-1] / window[-30:, 1].max()),
            np.mean((window[-7:, 1] - window[-7:, 2]) / window[-7:, 3]),
            btc_r30,
        ]
    )
    if not np.isfinite(values).all():
        return None
    return values, quote_median


def outcome(bars: np.ndarray, entry_index: int) -> tuple[float, str | None]:
    window = bars[entry_index : entry_index + 7]
    if len(window) != 7:
        return -1.0, "calendar_incomplete"
    if not np.isfinite(window[0, 0]) or window[0, 0] <= 0:
        return -1.0, "missing_entry"
    if not np.isfinite(window).all() or (window <= 0).any():
        return -1.0, "missing_or_invalid_outcome_bar"
    return float(window[-1, 3] / window[0, 0] - 1), None


def net_returns(gross: np.ndarray, side_bps: float) -> np.ndarray:
    side = side_bps / 10000
    return (1 + gross) * (1 - side) / (1 + side) - 1


class AnalogModel:
    def __init__(self, neighbors: int = 200):
        self.neighbors = neighbors

    def fit(self, x: np.ndarray, y: np.ndarray):
        if len(x) < self.neighbors or not np.isfinite(x).all():
            raise ValueError("insufficient/invalid training observations")
        self.median = np.median(x, axis=0)
        q25, q75 = np.percentile(x, [25, 75], axis=0)
        self.iqr = q75 - q25
        self.iqr[self.iqr == 0] = 1
        self.labels = np.asarray(y, dtype=float).copy()
        self.nn = NearestNeighbors(n_neighbors=self.neighbors, algorithm="brute", n_jobs=2)
        self.nn.fit(self.transform(x))
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        return np.clip((x - self.median) / self.iqr, -5, 5)

    def predict(self, x: np.ndarray):
        distances, indices = self.nn.kneighbors(self.transform(x))
        return self.labels[indices].mean(axis=1), distances, indices


def load_data(directory: Path):
    manifest = json.loads((directory / "acquisition.json").read_text())
    protocol = json.loads(PROTOCOL.read_text())
    if manifest["protocol_sha256"] != hashlib.sha256(PROTOCOL.read_bytes()).hexdigest():
        raise ValueError("protocol changed after acquisition started")
    if manifest["errors"]:
        raise ValueError("acquisition failures must be resolved or explicitly amended")
    if select_symbols(manifest["catalog"], protocol) != manifest["selected"]:
        raise ValueError("universe does not match deterministic protocol")
    n_days = (CUTOFF - BASE).days
    data = {}
    for symbol in manifest["selected"] + ["BTCUSDT"]:
        payload = json.loads(
            gzip.decompress((directory / "pairs" / f"{symbol}.json.gz").read_bytes())
        )
        values = np.full((n_days, 6), np.nan)
        for row in payload["rows"]:
            day = EPOCH + timedelta(days=int(row[0]) // DAY_MS)
            index = (day - BASE).days
            if not 0 <= index < n_days or row[7] >= (CUTOFF - EPOCH).days * DAY_MS:
                raise ValueError("future or out-of-range candle")
            if np.isfinite(values[index]).any():
                raise ValueError("duplicate input day")
            if row[2] < max(row[1], row[4]) or row[3] > min(row[1], row[4]):
                raise ValueError(f"inconsistent candle OHLC {symbol} {day}")
            values[index] = row[1:7]
        data[symbol] = values
    return manifest, data


def period_for(day: date) -> str | None:
    end_exclusive = day + timedelta(days=7)
    if date(2021, 1, 1) <= day and end_exclusive <= date(2024, 1, 1):
        return "train"
    if date(2024, 1, 1) <= day and end_exclusive <= date(2025, 1, 1):
        return "evaluation_1"
    if date(2025, 1, 1) <= day and end_exclusive <= CUTOFF:
        return "evaluation_2"
    if day == CUTOFF:
        return "current"
    return None


def build_samples(manifest: dict, data: dict):
    samples = []
    weeks = []
    day = date(2021, 1, 4)
    btc = data["BTCUSDT"]
    while day <= CUTOFF:
        period = period_for(day)
        if period is None:
            day += timedelta(days=7)
            continue
        index = (day - BASE).days
        btc_gross, btc_missing = (None, None) if period == "current" else outcome(btc, index)
        if btc_missing:
            raise ValueError(f"missing benchmark {day}")
        week = {
            "date": day.isoformat(),
            "period": period,
            "btc_gross": btc_gross,
            "sample_indices": [],
        }
        for symbol in sorted(manifest["selected"]):
            extracted = extract_features(data[symbol], btc, index)
            if extracted is None:
                continue
            features, quote_volume = extracted
            gross, missing = (None, None) if period == "current" else outcome(data[symbol], index)
            if period == "current":
                label = None
            else:
                assert gross is not None and btc_gross is not None
                label = int(gross >= 0.2 and gross - btc_gross >= 0.1)
            sample = {
                "date": day.isoformat(),
                "symbol": symbol,
                "period": period,
                "features_available_assumed_utc": (day - timedelta(days=1)).isoformat()
                + "T00:00:00Z",
                "features": features.tolist(),
                "median_quote_volume_30d": quote_volume,
                "gross_return": gross,
                "btc_gross_return": btc_gross,
                "target": label,
                "missing_outcome": missing,
            }
            week["sample_indices"].append(len(samples))
            samples.append(sample)
        weeks.append(week)
        day += timedelta(days=7)
    return samples, weeks


def block_ci(differences: np.ndarray, repetitions: int = 5000):
    n = len(differences)
    if not n or not np.isfinite(differences).all():
        raise ValueError("invalid paired differences")
    rng = np.random.default_rng(20260907)
    starts = rng.integers(0, n, size=(repetitions, (n + 3) // 4))
    indices = ((starts[:, :, None] + np.arange(4)) % n).reshape(repetitions, -1)[:, :n]
    estimates = differences[indices].mean(axis=1)
    effective = max(1, n // 4)
    return {
        "mean_weekly_log_difference": float(differences.mean()),
        "ci95_block4": np.quantile(estimates, [0.025, 0.975]).tolist(),
        "n_paired_weeks": n,
        "effective_n_power_heuristic": effective,
        "mde80_in_weekly_sd": float(2.802 / np.sqrt(effective)),
        "mde80_weekly_log_difference_descriptive": float(
            2.802 * np.std(differences, ddof=1) / np.sqrt(effective)
        ),
    }


def equity_metrics(returns: list[float]):
    values = np.asarray(returns)
    factors = 1 + values
    equity = np.r_[1.0, np.cumprod(factors)]
    drawdown = equity / np.maximum.accumulate(equity) - 1
    total = float(equity[-1] - 1)
    annual = float(equity[-1] ** (365.25 / (7 * len(values))) - 1)
    return {
        "compounded_return": total,
        "annualized_geometric_return": annual,
        "max_drawdown_weekly_endpoints": float(drawdown.min()),
        "positive_weeks": int((values > 0).sum()),
        "weeks": len(values),
        "mean_weekly_return": float(values.mean()),
        "ending_wealth_per_unit": float(equity[-1]),
        "conditional_5000_usdt_pnl": total * 5000,
        "conditional_brl_pnl_at_flat_5_1253": total * 5000 * 5.1253,
    }


def evaluate(samples: list[dict], weeks: list[dict]):
    evaluated = []
    for week in weeks:
        if not week["period"].startswith("evaluation"):
            continue
        members = [samples[i] for i in week["sample_indices"]]
        enough = len(members) >= 10
        analogs = sorted(members, key=lambda s: (-s["score"], s["symbol"]))[:5] if enough else []
        momentum = (
            sorted(members, key=lambda s: (-s["features"][2], s["symbol"]))[:5] if enough else []
        )
        selections = {
            "analogs": analogs,
            "momentum": momentum,
            "equal_basket": members if enough else [],
        }
        record = {k: v for k, v in week.items() if k != "sample_indices"}
        record.update(
            {
                "eligible": len(members),
                "cash_week": not enough,
                "selections": {m: [s["symbol"] for s in v] for m, v in selections.items()},
                "returns": {},
            }
        )
        for cost in (20, 50, 100):
            returns = {}
            for method, holdings in selections.items():
                returns[method] = (
                    float(net_returns(np.array([s["gross_return"] for s in holdings]), cost).mean())
                    if holdings
                    else 0.0
                )
            returns["btc"] = (
                float(net_returns(np.array([week["btc_gross"]]), cost)[0]) if enough else 0.0
            )
            returns["cash"] = 0.0
            record["returns"][str(cost)] = returns
        record["target_rates"] = {
            m: float(np.mean([s["target"] for s in h])) if h else None
            for m, h in selections.items()
        }
        record["missing_outcomes"] = {
            m: [s["symbol"] for s in h if s["missing_outcome"]] for m, h in selections.items()
        }
        if any(s["missing_outcome"] == "missing_entry" for s in members):
            # Fixed protocol sensitivity only: an unfillable order leaves that allocation in cash.
            record["missing_entry_cash_sensitivity_20bps"] = {
                method: float(
                    np.mean(
                        [
                            0.0
                            if s["missing_outcome"] == "missing_entry"
                            else net_returns(np.array([s["gross_return"]]), 20)[0]
                            for s in holdings
                        ]
                    )
                )
                if holdings
                else 0.0
                for method, holdings in selections.items()
            }
        evaluated.append(record)
    reports = {}
    for segment in ("evaluation_1", "evaluation_2"):
        segment_weeks = [w for w in evaluated if w["period"] == segment]
        report = {
            "start": segment_weeks[0]["date"],
            "last_entry": segment_weeks[-1]["date"],
            "cost_scenarios": {},
        }
        for cost in (20, 50, 100):
            streams = {
                method: [w["returns"][str(cost)][method] for w in segment_weeks]
                for method in ("analogs", "equal_basket", "momentum", "btc", "cash")
            }
            if any(min(stream) <= -1 for stream in streams.values()):
                raise ValueError("catastrophic portfolio loss: no finite log comparison")
            contrasts = {
                other: block_ci(np.log1p(streams["analogs"]) - np.log1p(streams[other]))
                for other in ("equal_basket", "momentum")
            }
            report["cost_scenarios"][str(cost)] = {
                "methods": {m: equity_metrics(r) for m, r in streams.items()},
                "paired_contrasts": contrasts,
            }
        target_rates = {
            method: float(
                np.mean(
                    [
                        w["target_rates"][method]
                        for w in segment_weeks
                        if w["target_rates"][method] is not None
                    ]
                )
            )
            for method in ("analogs", "equal_basket", "momentum")
        }
        report["mean_weekly_target_rates"] = target_rates
        report["target_lift_vs_basket"] = (
            target_rates["analogs"] / target_rates["equal_basket"]
            if target_rates["equal_basket"]
            else None
        )
        report["eligible_count_range"] = [
            min(w["eligible"] for w in segment_weeks),
            max(w["eligible"] for w in segment_weeks),
        ]
        report["cash_weeks"] = sum(w["cash_week"] for w in segment_weeks)
        report["missing_outcomes"] = {
            m: sum(len(w["missing_outcomes"][m]) for w in segment_weeks)
            for m in ("analogs", "equal_basket", "momentum")
        }
        reports[segment] = report
    return reports, evaluated


def decision(reports: dict, train: list[dict]):
    first, second = reports["evaluation_1"], reports["evaluation_2"]
    primary = second["cost_scenarios"]["20"]["paired_contrasts"]["equal_basket"]
    if sum(s["target"] for s in train) < 100 or any(
        r["cost_scenarios"]["20"]["methods"]["analogs"]["weeks"] < 40 for r in (first, second)
    ):
        return "UNDERPOWERED"
    all_positive = all(
        r["cost_scenarios"]["20"]["paired_contrasts"][control]["mean_weekly_log_difference"] > 0
        for r in (first, second)
        for control in ("equal_basket", "momentum")
    )
    stress = (
        second["cost_scenarios"]["50"]["paired_contrasts"]["equal_basket"][
            "mean_weekly_log_difference"
        ]
        > 0
    )
    if (
        primary["ci95_block4"][0] > 0
        and all_positive
        and second["target_lift_vs_basket"] > 1
        and stress
    ):
        return "PROMISING"
    return (
        "REJECT_FOR_THIS_SPECIFICATION"
        if primary["mean_weekly_log_difference"] <= 0
        else "INCONCLUSIVE"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest, data = load_data(args.data_dir)
    samples, weeks = build_samples(manifest, data)
    train = [s for s in samples if s["period"] == "train"]
    if any(date.fromisoformat(s["date"]) + timedelta(days=7) > date(2024, 1, 1) for s in train):
        raise ValueError("label leakage")
    model = AnalogModel().fit(
        np.array([s["features"] for s in train]), np.array([s["target"] for s in train])
    )
    others = [s for s in samples if s["period"] != "train"]
    scores, distances, neighbors = model.predict(np.array([s["features"] for s in others]))
    current = []
    for sample, score, dist, near in zip(others, scores, distances, neighbors, strict=True):
        sample["score"] = float(score)
        if sample["period"] != "current":
            continue
        row = dict(sample)
        row["nearest_winners"] = []
        row["nearest_non_winners"] = []
        for distance, idx in zip(dist, near, strict=True):
            past = train[int(idx)]
            key = "nearest_winners" if past["target"] else "nearest_non_winners"
            if len(row[key]) < 3:
                row[key].append(
                    {
                        "symbol": past["symbol"],
                        "entry_date": past["date"],
                        "gross_return_7d": past["gross_return"],
                        "btc_gross_return_7d": past["btc_gross_return"],
                        "distance": float(distance),
                    }
                )
        row["positive_neighbors"] = int(round(float(score) * 200))
        row["neighbor_count"] = 200
        current.append(row)
    current.sort(key=lambda s: (-s["score"], s["symbol"]))
    reports, evaluated = evaluate(samples, weeks)
    verdict = decision(reports, train)
    issues = [p for p in manifest["pairs"] if p["missing_internal_days"] or not p["rows"]]
    result = {
        "screen_id": manifest["screen_id"],
        "mode": "DISCOVERY",
        "decision": verdict,
        "no_capital_or_live_activation": True,
        "protocol_sha256": manifest["protocol_sha256"],
        "data_known_at": {"start": manifest["started_at_utc"], "end": manifest["completed_at_utc"]},
        "coverage": {
            "catalog_pairs": manifest["catalog_count"],
            "catalog_usdt_pairs": manifest["catalog_usdt_count"],
            "sampled_altcoins": len(manifest["selected"]),
            "downloaded_daily_bars": sum(p["rows"] for p in manifest["pairs"]),
            "archive_fallback_pairs": [
                p["symbol"] for p in manifest["pairs"] if p["source"] == "ARCHIVE"
            ],
            "coverage_issues": issues,
            "current_eligible": len(current),
        },
        "training": {
            "observations": len(train),
            "distinct_symbols": len({s["symbol"] for s in train}),
            "weeks": len({s["date"] for s in train}),
            "positive_targets": sum(s["target"] for s in train),
            "negative_controls": sum(1 - s["target"] for s in train),
            "target_base_rate": float(np.mean([s["target"] for s in train])),
            "missing_outcome_count": sum(bool(s["missing_outcome"]) for s in train),
        },
        "evaluation": reports,
        "current_signal": {
            "as_of_assumed_utc": "2026-09-07T00:00:00Z",
            "features_through_day": "2026-09-05",
            "horizon_days": 7,
            "score_semantics": "uncalibrated frequency in 200 historical neighbors; research ranking, not a buy recommendation",
            "ranking": current,
        },
        "model": {
            "training_median": model.median.tolist(),
            "training_iqr": model.iqr.tolist(),
            "features": FEATURE_NAMES,
            "neighbors": 200,
        },
        "limitations": [
            "Retrospective Discovery only; existing project may already have seen parts of these periods.",
            "Archive retention and pair reuse prevent a claim of complete historical membership or perfect survivorship correction.",
            "Daily open/close and assumed fees/slippage are accounting proxies, not fills.",
            "24-hour historical availability is simulated; actual known_at is retrieval in 2026.",
            "Weekly endpoint drawdown understates possible intraday drawdown.",
            "USDT returns are not BRL purchasing-power alpha; benchmark/tax/FX/risk/attention constraints remain open.",
            "One fixed model; block CIs are not adjusted for all historical project research or market-wide model selection.",
        ],
    }
    for segment in ("evaluation_1", "evaluation_2"):
        subset = [s for s in others if s["period"] == segment]
        base = result["training"]["target_base_rate"]
        result["evaluation"][segment]["brier_score_all_eligible"] = float(
            np.mean([(s["score"] - s["target"]) ** 2 for s in subset])
        )
        result["evaluation"][segment]["brier_constant_training_rate"] = float(
            np.mean([(base - s["target"]) ** 2 for s in subset])
        )
    (args.output_dir / "results.json").write_text(
        json.dumps(result, indent=2, allow_nan=False), encoding="utf-8"
    )
    (args.output_dir / "weekly_portfolios.json").write_text(
        json.dumps(evaluated, indent=2, allow_nan=False), encoding="utf-8"
    )
    (args.output_dir / "samples.json.gz").write_bytes(
        gzip.compress(json.dumps(samples, allow_nan=False).encode(), mtime=0)
    )
    print(
        json.dumps(
            {
                "decision": verdict,
                "coverage": {
                    k: v
                    for k, v in result["coverage"].items()
                    if k not in ("coverage_issues", "archive_fallback_pairs")
                },
                "training": result["training"],
                "evaluation": reports,
                "current_top5": [
                    {k: s[k] for k in ("symbol", "score", "median_quote_volume_30d")}
                    for s in current[:5]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
