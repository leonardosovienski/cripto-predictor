"""Repair outcome identities and prepare one net-payoff/abstention prototype.

This is preparation plus a dry run, not a new historical performance trial.
Original samples, models, results, production and frozen files are immutable.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

from scripts.collect_altcoin_analogs import Acquisition, time_ms
from scripts.research_altcoin_analogs import AnalogModel

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/altcoin_payoff_20260907"
EPOCH = date(1970, 1, 1)
DAY = 86_400_000
LEVERAGED_BASES = {
    "1INCH",
    "AAVE",
    "ADA",
    "BCH",
    "BNB",
    "BTC",
    "DOT",
    "EOS",
    "ETH",
    "FIL",
    "LINK",
    "LTC",
    "SUSHI",
    "SXP",
    "TRX",
    "UNI",
    "XLM",
    "XRP",
    "XTZ",
    "YFI",
}


def is_known_leveraged_symbol(symbol: str) -> bool:
    """Explicit legacy product families; a name merely ending in UP is insufficient."""
    if not symbol.endswith("USDT"):
        return False
    base = symbol[:-4]
    if base in {"BULL", "BEAR"}:
        return True
    return any(
        base == asset + suffix
        for asset in LEVERAGED_BASES
        for suffix in ("UP", "DOWN", "BULL", "BEAR")
    )


def raw_entries(raw_dir: Path, requested: set[tuple[str, int]]) -> dict:
    result = {}
    for metadata_path in raw_dir.glob("*.json"):
        metadata = json.loads(metadata_path.read_text())
        url = urlparse(metadata["url"])
        if url.path != "/api/v3/klines":
            continue
        symbol = parse_qs(url.query)["symbol"][0]
        if not any(key[0] == symbol for key in requested):
            continue
        body = gzip.decompress(metadata_path.with_suffix(".bin.gz").read_bytes())
        assert hashlib.sha256(body).hexdigest() == metadata["sha256"]
        for row in json.loads(body):
            key = (symbol, time_ms(row[0]))
            if key in requested:
                result[key] = {
                    "open": row[1],
                    "source": metadata["url"],
                    "known_at": metadata["retrieved_at_utc"],
                }
    if set(result) != requested:
        raise ValueError("Original entry prices are not fully traceable")
    return result


def exact_close(rows: list, on_day: date) -> str | None:
    start = (on_day - EPOCH).days * DAY
    end = start + DAY
    matches = [
        row
        for row in rows
        if time_ms(row[0]) == start
        and time_ms(row[6]) < end
        and Decimal(row[4]) > 0
        and Decimal(row[5]) > 0
    ]
    if len(matches) > 1:
        raise ValueError("duplicate exact-day price")
    return matches[0][4] if matches else None


def adjusted_gross(entry_price: str, close: str, ratio: str, quote_close: str = "1") -> float:
    values = [Decimal(x) for x in (entry_price, close, ratio, quote_close)]
    if any(x <= 0 for x in values):
        raise ValueError("nonpositive price/conversion ratio")
    entry, price, units, quote = values
    return float(price * units * quote / entry - 1)


def net_factor(gross: float, sell_legs: int = 1, side_bps: float = 20) -> float:
    if not math.isfinite(gross) or gross < -1 or sell_legs < 1:
        raise ValueError("invalid payoff or exit route")
    cost = side_bps / 10000
    return (1 + gross) * (1 - cost) ** sell_legs / (1 + cost)


def payoff_summary(neighbors: list[dict]) -> dict:
    unresolved = sum(s["gross_return"] is None for s in neighbors)
    if unresolved:
        return {
            "status": "ABSTAIN_CENSORED_NEIGHBOR",
            "unresolved_neighbors": unresolved,
            "score_log": None,
            "qualified": False,
        }
    by_week = defaultdict(list)
    for sample in neighbors:
        factor = net_factor(sample["gross_return"], sample.get("sell_legs", 1))
        if factor <= 0:
            return {"status": "ABSTAIN_TOTAL_LOSS_NEIGHBOR", "score_log": None, "qualified": False}
        by_week[sample["date"]].append(math.log(factor))
    values = np.array([np.mean(v) for v in by_week.values()])
    if len(values) < 20:
        return {
            "status": "ABSTAIN_TOO_FEW_DISTINCT_WEEKS",
            "distinct_weeks": len(values),
            "score_log": None,
            "qualified": False,
        }
    effective = len(values) // 4
    mean = float(values.mean())
    penalty = float(1.96 * values.std(ddof=1) / np.sqrt(effective))
    score = mean - penalty
    return {
        "status": "RESEARCH_CANDIDATE" if score > 0 else "ABSTAIN_NO_POSITIVE_MARGIN",
        "qualified": score > 0,
        "distinct_weeks": len(values),
        "effective_n_heuristic": effective,
        "mean_log_payoff": mean,
        "geometric_payoff_proxy": math.expm1(mean),
        "uncertainty_penalty_log": penalty,
        "score_log": score,
        "score_return_equivalent": math.expm1(score),
        "confidence_claim": "heuristic penalty, not a calibrated confidence interval",
    }


def repair_samples(samples: list[dict], resolutions: list[dict]) -> list[dict]:
    lookup = {(x["symbol"], x["entry"]): x for x in resolutions}
    expected = {(x["symbol"], x["date"]) for x in samples if x["missing_outcome"]}
    if set(lookup) != expected:
        raise ValueError("resolution register does not cover exactly the original missing outcomes")
    enriched = []
    for original in samples:
        sample = dict(original)
        sample["gross_return_original_stress"] = original["gross_return"]
        sample["target_original_stress"] = original["target"]
        sample["sell_legs"] = 1
        sample["outcome_status"] = (
            "PENDING" if original["period"] == "current" else "DIRECT_DAILY_PRICE_PROXY"
        )
        resolution = lookup.get((original["symbol"], original["date"]))
        if resolution:
            sample["gross_return"] = resolution["gross_return"]
            sample["outcome_status"] = resolution["status"]
            sample["sell_legs"] = resolution["sell_legs"]
            sample["target"] = (
                None
                if resolution["gross_return"] is None
                else int(
                    resolution["gross_return"] >= 0.2
                    and resolution["gross_return"] - original["btc_gross_return"] >= 0.1
                )
            )
        enriched.append(sample)
    return enriched


def fixed_selection_sensitivity(samples: list[dict], weeks: list[dict]) -> dict:
    lookup = {(s["date"], s["symbol"]): s for s in samples}
    reports = {}
    for period in ("evaluation_1", "evaluation_2"):
        reports[period] = {}
        for method in ("analogs", "equal_basket", "momentum"):
            streams = {"unresolved_total_loss_stress": [], "unresolved_flat_recovery_scenario": []}
            unknown = []
            for week in (w for w in weeks if w["period"] == period):
                holdings = [lookup[(week["date"], symbol)] for symbol in week["selections"][method]]
                if not holdings:
                    for values in streams.values():
                        values.append(1.0)
                    continue
                factors = []
                for sample in holdings:
                    if sample["gross_return"] is None:
                        factors.append(None)
                        unknown.append({"date": sample["date"], "symbol": sample["symbol"]})
                    else:
                        factors.append(net_factor(sample["gross_return"], sample["sell_legs"]))
                streams["unresolved_total_loss_stress"].append(
                    float(np.mean([0 if x is None else x for x in factors]))
                )
                streams["unresolved_flat_recovery_scenario"].append(
                    float(np.mean([1 if x is None else x for x in factors]))
                )
            reports[period][method] = {
                "exact_executable_return": None,
                "unresolved_holdings": unknown,
                "scenario_compounded_returns": {
                    key: float(np.prod(values) - 1) for key, values in streams.items()
                },
                "meaning": "Fixed v1 selections, corrected known quantity/quote marks. Scenarios for residual censoring, not executable P&L or universal recovery bounds.",
            }
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-data-dir", required=True, type=Path)
    parser.add_argument("--base-results-dir", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Require every price request in the recorded cache; never contact the provider",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    events = json.loads((EVIDENCE / "identity_events.json").read_text())["events"]
    protocol = json.loads((EVIDENCE / "protocol.json").read_text())
    requested = {(e["symbol"], (date.fromisoformat(e["entry"]) - EPOCH).days * DAY) for e in events}
    entries = raw_entries(args.base_data_dir / "raw", requested)
    acquisition = Acquisition(args.data_dir)

    def close_for(symbol: str, day: date):
        start = (day - EPOCH).days * DAY
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": "1d",
            "startTime": start,
            "endTime": start + DAY - 1,
            "limit": 2,
        }
        if args.offline:
            request = acquisition.client.build_request("GET", url, params=params)
            key = hashlib.sha256(str(request.url).encode()).hexdigest()
            metadata = json.loads((args.data_dir / "raw" / f"{key}.json").read_text())
            body = gzip.decompress((args.data_dir / "raw" / f"{key}.bin.gz").read_bytes())
            if hashlib.sha256(body).hexdigest() != metadata["sha256"]:
                raise ValueError("offline cached price hash mismatch")
        else:
            body = acquisition.get(url, params)
        return exact_close(json.loads(body), day)

    resolutions = []
    for event in events:
        entered = date.fromisoformat(event["entry"])
        exit_day = entered + timedelta(days=6)
        entry = entries[(event["symbol"], (entered - EPOCH).days * DAY)]
        row = dict(
            event,
            entry_price=entry["open"],
            entry_raw_source=entry,
            exit_day=exit_day.isoformat(),
            gross_return=None,
            sell_legs=1,
        )
        if event["kind"] == "DELISTING_UNRESOLVED":
            row["status"] = "CENSORED_NO_VERIFIED_EXIT"
        else:
            price = close_for(event["exit_pair"], exit_day)
            quote = (
                close_for(event["quote_conversion_pair"], exit_day)
                if event.get("quote_conversion_pair")
                else "1"
            )
            row.update(
                {
                    "successor_close": price,
                    "quote_usdt_close": quote,
                    "sell_legs": 2 if event.get("quote_conversion_pair") else 1,
                }
            )
            if price is None or quote is None:
                row["status"] = "CENSORED_NO_PRICE_AT_ORIGINAL_HORIZON"
            else:
                row["gross_return"] = adjusted_gross(
                    entry["open"], price, event["new_units_per_old"], quote
                )
                row["status"] = (
                    "QUANTITY_ADJUSTED_DAILY_MARK"
                    if event["kind"] == "TOKEN_MIGRATION"
                    else "CROSS_QUOTE_DAILY_MARK"
                )
        resolutions.append(row)
    raw_metadata = [
        json.loads(p.read_text()) for p in sorted((args.data_dir / "raw").glob("*.json"))
    ]
    samples = json.loads(gzip.decompress((args.base_results_dir / "samples.json.gz").read_bytes()))
    enriched = repair_samples(samples, resolutions)
    train = [s for s in enriched if s["period"] == "train"]
    current = [s for s in enriched if s["period"] == "current"]
    # Only the v1 neighbor geometry is reused. Dummy labels are not return imputations:
    # they are never scored; the complete/censored payoffs are handled separately.
    geometry = AnalogModel().fit(np.array([s["features"] for s in train]), np.zeros(len(train)))
    _, _, indices = geometry.predict(np.array([s["features"] for s in current]))
    snapshot = []
    for sample, neighbors in zip(current, indices, strict=True):
        summary = payoff_summary([train[int(i)] for i in neighbors])
        snapshot.append({"symbol": sample["symbol"], "neighbor_count": 200, **summary})
    snapshot.sort(
        key=lambda s: (
            s["score_log"] is None,
            -(s["score_log"] if s["score_log"] is not None else 0),
            s["symbol"],
        )
    )
    selected = [s["symbol"] for s in snapshot if s["qualified"]][:5]
    weeks = json.loads((args.base_results_dir / "weekly_portfolios.json").read_text())
    output = {
        "id": protocol["id"],
        "status": "IMPLEMENTED_DRY_RUN_ONLY_NOT_PROMOTED",
        "protocol_sha256": hashlib.sha256((EVIDENCE / "protocol.json").read_bytes()).hexdigest(),
        "identity_resolutions": resolutions,
        "counts": {
            "original_censored": len(resolutions),
            "resolved_price_proxies": sum(r["gross_return"] is not None for r in resolutions),
            "still_censored": sum(r["gross_return"] is None for r in resolutions),
            "training_samples_preserved": len(train),
            "training_still_censored": sum(s["gross_return"] is None for s in train),
        },
        "fixed_v1_selection_accounting": fixed_selection_sensitivity(enriched, weeks),
        "payoff_snapshot": {
            "input_date": "2026-09-07",
            "prospective": False,
            "performance_claim": False,
            "ranked": snapshot,
            "candidate_symbols": selected,
            "research_weight_each": 0.2,
            "cash_weight": 1 - 0.2 * len(selected),
            "status_counts": dict(Counter(s["status"] for s in snapshot)),
        },
        "new_historical_performance_trials": 0,
        "raw_requests": raw_metadata,
        "activation": {"capital": False, "orders": False, "scheduler": False, "prospective": False},
        "remaining": protocol["new_evidence"]["before_prospective_activation"],
    }
    (args.output_dir / "results.json").write_text(
        json.dumps(output, indent=2, allow_nan=False), encoding="utf-8"
    )
    (args.output_dir / "samples_identity_corrected.json.gz").write_bytes(
        gzip.compress(json.dumps(enriched, allow_nan=False).encode(), mtime=0)
    )
    print(
        json.dumps(
            {
                "counts": output["counts"],
                "resolutions": [
                    {k: row.get(k) for k in ("symbol", "entry", "status", "gross_return")}
                    for row in resolutions
                ],
                "snapshot": output["payoff_snapshot"],
                "fixed_accounting": output["fixed_v1_selection_accounting"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
