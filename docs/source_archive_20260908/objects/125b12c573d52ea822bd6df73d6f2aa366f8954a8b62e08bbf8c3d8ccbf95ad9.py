"""Independent raw-feature, scorer and portfolio checks for the saved diagnostic."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

DAY = 86_400_000
EPOCH = date(1970, 1, 1)


def stamp(value):
    value = int(value)
    return value // 1000 if value > 100_000_000_000_000 else value


def independent_features(bars: list, btc: list):
    closes = [float(r[4]) for r in bars]
    reference = [float(r[4]) for r in btc]
    volume = [float(r[7]) for r in bars]
    log = math.log
    return [
        log(closes[-1] / closes[-2]),
        log(closes[-1] / closes[-8]) - log(reference[-1] / reference[-8]),
        log(closes[-1] / closes[-31]) - log(reference[-1] / reference[-31]),
        log(statistics.mean(volume[-7:]) / statistics.mean(volume[-30:-7])),
        statistics.pstdev([log(b / a) for a, b in zip(closes[-31:-1], closes[-30:], strict=True)]),
        log(closes[-1] / max(float(r[2]) for r in bars[-30:])),
        statistics.mean([(float(r[2]) - float(r[3])) / float(r[4]) for r in bars[-7:]]),
        log(reference[-1] / reference[-31]),
    ]


def manual_score(train: list[dict], indices):
    neighbors = [train[int(i)] for i in indices]
    if any(r["gross_return"] is None for r in neighbors):
        return "ABSTAIN_CENSORED_NEIGHBOR", None
    weeks = defaultdict(list)
    for r in neighbors:
        factor = (1 + r["gross_return"]) * 0.998 ** r.get("sell_legs", 1) / 1.002
        if factor <= 0:
            return "ABSTAIN_TOTAL_LOSS_NEIGHBOR", None
        weeks[r["date"]].append(math.log(factor))
    values = [statistics.mean(v) for v in weeks.values()]
    if len(values) < 20:
        return "ABSTAIN_TOO_FEW_DISTINCT_WEEKS", None
    score = statistics.mean(values) - 1.96 * statistics.stdev(values) / math.sqrt(len(values) // 4)
    return "RESEARCH_CANDIDATE" if score > 0 else "ABSTAIN_NO_POSITIVE_MARGIN", score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    args = parser.parse_args()
    results = json.loads((args.results_dir / "results.json").read_text())
    scores = json.loads(gzip.decompress((args.results_dir / "scores.json.gz").read_bytes()))
    train = [
        s for s in json.loads(gzip.decompress(args.training.read_bytes())) if s["period"] == "train"
    ]
    checked_rows = [scores[int(i)] for i in np.linspace(0, len(scores) - 1, 32, dtype=int)]
    requested = set()
    for row in checked_rows:
        entry_ms = (date.fromisoformat(row["date"]) - EPOCH).days * DAY
        for timestamp in range(entry_ms - 91 * DAY, entry_ms - DAY, DAY):
            requested.add((row["symbol"], timestamp))
            requested.add(("BTCUSDT", timestamp))
    raw_bars = {}
    raw_checks = 0
    retrieval_times = []
    for path in (args.data_dir / "raw").glob("*.json"):
        meta = json.loads(path.read_text())
        body = gzip.decompress(path.with_suffix(".bin.gz").read_bytes())
        assert hashlib.sha256(body).hexdigest() == meta["sha256"]
        raw_checks += 1
        retrieval_times.append(meta["retrieved_at_utc"])
        url = urlparse(meta["url"])
        if url.path != "/api/v3/klines":
            continue
        symbol = parse_qs(url.query)["symbol"][0]
        for candle in json.loads(body):
            key = (symbol, stamp(candle[0]))
            if key in requested:
                if key in raw_bars:
                    assert candle == raw_bars[key]
                raw_bars[key] = candle
    assert requested == set(raw_bars), "required raw feature bars are not fully traced"
    x = np.array([s["features"] for s in train])
    median = np.median(x, axis=0)
    q25, q75 = np.percentile(x, [25, 75], axis=0)
    scale = q75 - q25
    scale[scale == 0] = 1
    transformed = np.clip((x - median) / scale, -5, 5)
    max_feature_error = max_score_error = 0.0
    boundary_ties = 0
    for row in checked_rows:
        entry_ms = (date.fromisoformat(row["date"]) - EPOCH).days * DAY
        stamps = list(range(entry_ms - 91 * DAY, entry_ms - DAY, DAY))
        bars = [raw_bars[(row["symbol"], t)] for t in stamps]
        btc = [raw_bars[("BTCUSDT", t)] for t in stamps]
        for candle in bars + btc:
            assert stamp(candle[6]) == stamp(candle[0]) + DAY - 1
            assert float(candle[5]) > 0 and float(candle[7]) > 0
        features = independent_features(bars, btc)
        error = max(abs(a - b) for a, b in zip(features, row["features"], strict=True))
        assert error < 1e-10
        max_feature_error = max(max_feature_error, error)
        point = np.clip((np.array(row["features"]) - median) / scale, -5, 5)
        distances = np.sum((transformed - point) ** 2, axis=1)
        indices = np.argsort(distances, kind="stable")
        boundary_ties += int(distances[indices[199]] == distances[indices[200]])
        status, score = manual_score(train, indices[:200])
        assert status == row["status"]
        if score is not None:
            delta = abs(score - row["score_log"])
            assert delta < 1e-10
            max_score_error = max(max_score_error, delta)
    decisions = json.loads((args.results_dir / "decisions.json").read_text())
    assert (
        hashlib.sha256((args.results_dir / "decisions.json").read_bytes()).hexdigest()
        == results["decisions_sha256"]
    )
    weeks = json.loads((args.results_dir / "weekly_results.json").read_text())
    decimal_checks = 0
    for slip in (0, 10, 40, 90):
        wealth = Decimal(5000)
        for d, w in zip(decisions, weeks, strict=True):
            assert d["selected"] == w["selected"]
            factor = Decimal(1) - Decimal("0.2") * len(w["holdings"])
            for h in w["holdings"]:
                if h["gross_return"] is None:
                    factor = None
                    break
                leg = Decimal("0.999") * (1 - Decimal(slip) / 10000)
                factor += (
                    Decimal("0.2")
                    * (1 + Decimal(str(h["gross_return"])))
                    * leg ** (1 + h["sell_legs"])
                )
            if factor is None:
                assert w["factors_by_extra_bps"][str(slip)] is None
                wealth = None
            else:
                assert abs(float(factor) - w["factors_by_extra_bps"][str(slip)]) < 1e-12
                if wealth is not None:
                    wealth *= factor
            decimal_checks += 1
        expected = results["overall"]["cost_scenarios"][str(slip)]["ending_5000_usdt"]
        assert expected is None if wealth is None else abs(float(wealth) - expected) < 1e-8
    partial = json.loads((args.data_dir / "close_time_issues.json").read_text())
    audit = {
        "raw_response_hash_checks": raw_checks,
        "raw_retrieval_interval": [min(retrieval_times), max(retrieval_times)],
        "raw_bars_used_in_independent_feature_checks": len(requested),
        "independent_raw_feature_vectors": len(checked_rows),
        "independent_numpy_neighbor_and_stdlib_score_checks": len(checked_rows),
        "neighbor_boundary_ties": boundary_ties,
        "max_feature_difference": max_feature_error,
        "max_score_difference": max_score_error,
        "decimal_weekly_portfolio_checks": decimal_checks,
        "selected_trade_price_return_checks": sum(len(w["holdings"]) for w in weeks),
        "selected_trade_price_check_limitation": "Zero selected trades means there are no executed-position price returns to audit, not evidence of perfect fills.",
        "partial_or_placeholder_candles": len(partial),
        "qualifying_before_minimum_universe": sum(
            w["qualifying_before_minimum_universe"] for w in weeks
        ),
        "positive_neighbor_mean_before_uncertainty_penalty": sum(
            s.get("mean_log_payoff", -1) > 0 for s in scores
        ),
        "software_validation": "Recorded separately in validation.json; this auditor does not run pytest, Ruff or Pyright.",
        "outcome": "SAVED_RESULT_CONFIRMED",
        "formal_attestation": False,
    }
    (args.results_dir / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
