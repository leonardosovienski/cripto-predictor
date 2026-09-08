"""One registered historical diagnostic of the frozen net-payoff selection rule.

Daily prices are valuation proxies. No orders, independent Proof or model tuning.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from scripts.prepare_altcoin_payoff import payoff_summary
from scripts.research_altcoin_analogs import AnalogModel, extract_features, outcome

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/altcoin_retro_20260907"
BASE = date(2020, 10, 1)
END = date(2026, 9, 7)
EPOCH = date(1970, 1, 1)
DAY = 86_400_000
SLIPS = (0, 10, 40, 90)


def blob(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write(path: Path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def load_training(path: Path) -> list[dict]:
    frozen = json.loads((ROOT / "docs/evidence/altcoin_profit_20260907/freeze.json").read_text())
    if digest(path.read_bytes()) != frozen["training_sha256"]:
        raise ValueError("active training artifact changed")
    train = [r for r in json.loads(gzip.decompress(path.read_bytes())) if r["period"] == "train"]
    for row in train:
        if not date(2021, 1, 1) <= date.fromisoformat(row["date"]) or date.fromisoformat(
            row["date"]
        ) + timedelta(days=7) > date(2024, 1, 1):
            raise ValueError("training outcome crosses evaluation boundary")
    return train


def load_histories(directory: Path):
    manifest = json.loads((directory / "acquisition.json").read_text())
    if manifest["protocol_sha256"] != digest((EVIDENCE / "protocol.json").read_bytes()):
        raise ValueError("acquisition protocol changed")
    if manifest["errors"] or len(manifest["pairs"]) != len(manifest["selected"]):
        raise ValueError("incomplete acquisition")
    data = {}
    for row in manifest["pairs"]:
        path = directory / "pairs" / f"{row['symbol']}.json.gz"
        if digest(path.read_bytes()) != row["normalized_sha256"]:
            raise ValueError("normalized history changed")
        payload = json.loads(gzip.decompress(path.read_bytes()))
        values = np.full(((END - BASE).days, 6), np.nan)
        seen = set()
        for candle in payload["rows"]:
            opened = int(candle[0])
            idx = (EPOCH + timedelta(days=opened // DAY) - BASE).days
            if opened % DAY or not 0 <= idx < len(values) or idx in seen:
                raise ValueError("invalid or duplicate candle day")
            seen.add(idx)
            if any(not math.isfinite(v) or v <= 0 for v in (candle[5], candle[6])):
                # Zero-volume provider placeholders are already ineligible under
                # the fixed rule, including placeholders with stale close times.
                continue
            if not opened <= candle[7] < opened + DAY:
                raise ValueError("invalid UTC close time")
            if candle[7] != opened + DAY - 1:
                # An early halt is an incomplete day, not a full-day close or a fatal
                # universe error. Preserve raw data and leave this day missing.
                continue
            if candle[2] < max(candle[1], candle[4]) or candle[3] > min(candle[1], candle[4]):
                raise ValueError("inconsistent OHLC")
            values[idx] = candle[1:7]
        data[row["symbol"]] = values
    if set(data) != set(manifest["selected"]):
        raise ValueError("history/universe mismatch")
    return manifest, data


def feature_rows(data: dict) -> tuple[list[dict], list[str]]:
    records, days = [], []
    entry = date(2024, 1, 1)
    while entry + timedelta(days=7) <= END:
        days.append(entry.isoformat())
        idx = (entry - BASE).days
        for symbol in sorted(data):
            features = extract_features(data[symbol], data["BTCUSDT"], idx)
            if features is not None:
                vector, liquidity = features
                records.append(
                    {
                        "date": entry.isoformat(),
                        "symbol": symbol,
                        "features": vector.tolist(),
                        "median_quote_volume_30d": liquidity,
                    }
                )
        entry += timedelta(days=7)
    return records, days


def make_decisions(train: list[dict], records: list[dict], days: list[str]):
    model = AnalogModel().fit(np.array([s["features"] for s in train]), np.zeros(len(train)))
    ranked = []
    # Only candidate features enter the model; candidate future returns cannot enter scoring.
    if records:
        for start in range(0, len(records), 1000):
            chunk = records[start : start + 1000]
            _, _, indices = model.predict(np.array([r["features"] for r in chunk]))
            for row, neighbors in zip(chunk, indices, strict=True):
                ranked.append(
                    {
                        "date": row["date"],
                        "symbol": row["symbol"],
                        "features": row["features"],
                        **payoff_summary([train[int(i)] for i in neighbors]),
                    }
                )
    by_day = defaultdict(list)
    for row in ranked:
        by_day[row["date"]].append(row)
    weeks = []
    for day in days:
        candidates = by_day[day]
        qualifying = sorted(
            (r for r in candidates if r["qualified"]), key=lambda r: (-r["score_log"], r["symbol"])
        )
        selected = [r["symbol"] for r in qualifying[:5]] if len(candidates) >= 10 else []
        weeks.append(
            {
                "date": day,
                "eligible": len(candidates),
                "qualifying_before_minimum_universe": len(qualifying),
                "selected": selected,
                "cash_weight": 1 - 0.2 * len(selected),
                "selection_status": "SELECTED"
                if selected
                else "INSUFFICIENT_UNIVERSE"
                if len(candidates) < 10
                else "NO_POSITIVE_SCORE",
            }
        )
    return weeks, ranked


def cost_factor(gross: float, sell_legs: int = 1, extra_bps: int = 10) -> float:
    if not math.isfinite(gross) or gross < -1 or sell_legs < 1 or extra_bps not in SLIPS:
        raise ValueError("invalid payoff or cost scenario")
    per_leg = 0.999 * (1 - extra_bps / 10000)
    return (1 + gross) * per_leg ** (1 + sell_legs)


def portfolio_factor(holdings: list[dict], extra_bps: int, missing_scenario: str | None = None):
    if len(holdings) > 5:
        raise ValueError("more than five fixed-weight positions")
    factors = []
    for h in holdings:
        gross = h["gross_return"]
        if gross is None:
            if missing_scenario is None:
                return None
            if missing_scenario == "total_loss":
                factors.append(0.0)
                continue
            if missing_scenario != "flat_gross":
                raise ValueError("unregistered missing-outcome scenario")
            gross = 0.0
        factors.append(cost_factor(gross, h["sell_legs"], extra_bps))
    return 1 - 0.2 * len(holdings) + 0.2 * sum(factors)


def attach_outcomes(decisions: list[dict], data: dict, resolutions: list[dict]):
    lookup = {(r["symbol"], r["entry"]): r for r in resolutions}
    weeks = []
    for decision in decisions:
        idx = (date.fromisoformat(decision["date"]) - BASE).days
        holdings = []
        for symbol in decision["selected"]:
            gross, missing = outcome(data[symbol], idx)
            row = {
                "symbol": symbol,
                "date": decision["date"],
                "weight": 0.2,
                "gross_return": None if missing else gross,
                "sell_legs": 1,
                "outcome_status": missing or "DIRECT_DAILY_PRICE_PROXY",
            }
            resolution = lookup.get((symbol, decision["date"]))
            if missing and resolution:
                row.update(
                    {
                        "gross_return": resolution["gross_return"],
                        "sell_legs": resolution["sell_legs"],
                        "outcome_status": resolution["status"],
                        "resolution_source": resolution["source"],
                    }
                )
            row["net_returns_by_extra_bps"] = {
                str(s): None
                if row["gross_return"] is None
                else cost_factor(row["gross_return"], row["sell_legs"], s) - 1
                for s in SLIPS
            }
            holdings.append(row)
        weeks.append(
            {
                **decision,
                "holdings": holdings,
                "factors_by_extra_bps": {str(s): portfolio_factor(holdings, s) for s in SLIPS},
                "missing_scenarios": {
                    scenario: {str(s): portfolio_factor(holdings, s, scenario) for s in SLIPS}
                    for scenario in ("total_loss", "flat_gross")
                },
            }
        )
    return weeks


def wealth_metrics(factors: list[float | None]):
    if any(f is None for f in factors):
        return {
            "compounded_return": None,
            "ending_5000_usdt": None,
            "simulated_profit_5000_usdt": None,
            "max_drawdown_weekly_endpoints": None,
        }
    values = np.array(factors, dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("invalid portfolio factors")
    curve = np.r_[1.0, np.cumprod(values)]
    return {
        "compounded_return": float(curve[-1] - 1),
        "ending_5000_usdt": float(curve[-1] * 5000),
        "simulated_profit_5000_usdt": float((curve[-1] - 1) * 5000),
        "max_drawdown_weekly_endpoints": float((curve / np.maximum.accumulate(curve) - 1).min()),
    }


def descriptive_interval(factors: list[float | None], active_weeks: int):
    if not active_weeks or any(x is None or x <= 0 for x in factors):
        return {"interval": None, "reason": "NO_TRADING_EVIDENCE_OR_CENSORED"}
    values = np.log(np.asarray(factors, dtype=float))
    if np.std(values) == 0:
        return {"interval": None, "reason": "DEGENERATE_STREAM"}
    n = len(values)
    rng = np.random.default_rng(20260907)
    starts = rng.integers(0, n, size=(5000, (n + 3) // 4))
    indices = ((starts[:, :, None] + np.arange(4)) % n).reshape(5000, -1)[:, :n]
    return {
        "mean_weekly_log_return": float(values.mean()),
        "interval": np.quantile(values[indices].mean(axis=1), [0.025, 0.975]).tolist(),
        "meaning": "Descriptive 4-week block bootstrap only; not calibrated for full adaptive research/search history.",
    }


def summarize(weeks: list[dict]):
    holdings = [h for w in weeks for h in w["holdings"]]
    active = sum(bool(w["holdings"]) for w in weeks)
    known = [h["net_returns_by_extra_bps"]["10"] for h in holdings if h["gross_return"] is not None]
    gains, losses = [r for r in known if r > 0], [r for r in known if r < 0]
    summary = {
        "weeks": len(weeks),
        "active_weeks": active,
        "cash_weeks": len(weeks) - active,
        "selected_holdings": len(holdings),
        "censored_selected_holdings": sum(h["gross_return"] is None for h in holdings),
        "average_exposure": sum(0.2 * len(w["holdings"]) for w in weeks) / len(weeks),
        "trade_stats_primary": {
            "complete": len(known),
            "wins": len(gains),
            "losses": len(losses),
            "zero": len(known) - len(gains) - len(losses),
            "win_rate_among_complete": len(gains) / len(known) if known else None,
            "mean_gain": float(np.mean(gains)) if gains else None,
            "mean_loss": float(np.mean(losses)) if losses else None,
            "profit_factor_return_units": sum(gains) / -sum(losses) if losses else None,
        },
        "cost_scenarios": {
            str(s): wealth_metrics([w["factors_by_extra_bps"][str(s)] for w in weeks])
            for s in SLIPS
        },
        "missing_scenarios": {
            scenario: wealth_metrics([w["missing_scenarios"][scenario]["10"] for w in weeks])
            for scenario in ("total_loss", "flat_gross")
        },
        "uncertainty_primary": descriptive_interval(
            [w["factors_by_extra_bps"]["10"] for w in weeks], active
        ),
        "realized_profit": None,
        "investor_net_brl_profit": None,
    }
    primary = summary["cost_scenarios"]["10"]["compounded_return"]
    summary["decision"] = (
        "NO_TRADING_EVIDENCE_RULE_ABSTAINS"
        if not holdings
        else "INCONCLUSIVE_DATA_FIDELITY"
        if primary is None
        else "NOT_PROFITABLE_IN_THIS_DIAGNOSTIC"
        if primary <= 0
        else "POSITIVE_BUT_SPARSE"
        if active < 30
        else "POSITIVE_HISTORICAL_DIAGNOSTIC_NOT_PROOF"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    train = load_training(args.training)
    manifest, data = load_histories(args.data_dir)
    records, days = feature_rows(data)
    print(f"Scoring {len(records)} past-feature observations across {len(days)} weeks.", flush=True)
    decisions, scores = make_decisions(train, records, days)
    # First persist all selections and scores, then load/attach future valuation outcomes.
    decision_path = args.output_dir / "decisions.json"
    write(decision_path, decisions)
    (args.output_dir / "scores.json.gz").write_bytes(gzip.compress(blob(scores), mtime=0))
    resolutions = json.loads(
        (ROOT / "docs/evidence/altcoin_payoff_20260907/results.json").read_text()
    )["identity_resolutions"]
    weeks = attach_outcomes(decisions, data, resolutions)
    write(args.output_dir / "weekly_results.json", weeks)
    report = {
        "id": json.loads((EVIDENCE / "protocol.json").read_text())["id"],
        "protocol_sha256": digest((EVIDENCE / "protocol.json").read_bytes()),
        "decisions_sha256": digest(decision_path.read_bytes()),
        "training_sha256": digest(args.training.read_bytes()),
        "input_acquisition_sha256": digest((args.data_dir / "acquisition.json").read_bytes()),
        "historical_catalog_symbols": len(manifest["selected"]),
        "daily_bars": manifest["total_rows"],
        "evaluated_feature_observations": len(records),
        "start_entry": days[0],
        "last_entry": days[-1],
        "last_exit": (date.fromisoformat(days[-1]) + timedelta(days=6)).isoformat(),
        "overall": summarize(weeks),
        "by_entry_year": {
            str(year): summarize([w for w in weeks if w["date"].startswith(str(year))])
            for year in (2024, 2025, 2026)
        },
        "score_status_counts": dict(Counter(r["status"] for r in scores)),
        "week_status_counts": dict(Counter(w["selection_status"] for w in weeks)),
        "score_range": [
            min((r["score_log"] for r in scores if r["score_log"] is not None), default=None),
            max((r["score_log"] for r in scores if r["score_log"] is not None), default=None),
        ],
        "censored_selected": [h for w in weeks for h in w["holdings"] if h["gross_return"] is None],
        "coverage": {
            "empty_histories": [p["symbol"] for p in manifest["pairs"] if not p["rows"]],
            "histories_ending_before_cutoff": sum(
                p["last_open_ms"] is not None
                and p["last_open_ms"] < int((END - timedelta(days=1) - EPOCH).days * DAY)
                for p in manifest["pairs"]
            ),
            "histories_with_internal_gaps": [
                p["symbol"] for p in manifest["pairs"] if p["missing_internal_days"]
            ],
        },
        "claim": "One adaptive historical diagnostic. Returns use daily price proxies and assumed transaction costs, not historical executable fills or investor net BRL profit. No external benchmark; no parameter search or untouched-test claim. All-cash results contain no evidence about winning trades or market risk.",
        "model_changed": False,
        "active_automation_changed": False,
        "orders": False,
    }
    write(args.output_dir / "results.json", report)
    print(
        json.dumps(
            {
                "overall": report["overall"],
                "score_status_counts": report["score_status_counts"],
                "score_range": report["score_range"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
