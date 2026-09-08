"""Post-result accounting audit; does not refit, rerank or change the protocol.

The two additional scenarios are explicitly post hoc diagnostics, not new OOS
evidence: zero trading costs and flat recovery for every missing holding.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from datetime import date, timedelta
from decimal import Decimal, getcontext
from pathlib import Path
from urllib.parse import parse_qs, urlparse

getcontext().prec = 40
EPOCH = date(1970, 1, 1)
DAY = 86_400_000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--results-dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.results_dir
    result = json.loads((root / "results.json").read_text())
    weeks = json.loads((root / "weekly_portfolios.json").read_text())
    samples = json.loads(gzip.decompress((root / "samples.json.gz").read_bytes()))
    lookup = {(s["date"], s["symbol"]): s for s in samples}
    raw_bars = {}
    n_hashes = 0
    for meta_path in (args.data_dir / "raw").glob("*.json"):
        metadata = json.loads(meta_path.read_text())
        body = gzip.decompress(meta_path.with_suffix(".bin.gz").read_bytes())
        assert hashlib.sha256(body).hexdigest() == metadata["sha256"]
        n_hashes += 1
        url = urlparse(metadata["url"])
        if url.path != "/api/v3/klines":
            continue
        symbol = parse_qs(url.query)["symbol"][0]
        for row in json.loads(body):
            t = int(row[0])
            if t > 100_000_000_000_000:
                t //= 1000
            raw_bars[(symbol, t)] = row
    maximum_return_error = 0.0
    raw_checks = 0
    for sample in samples:
        if sample["period"] == "current" or sample["missing_outcome"]:
            continue
        entered = date.fromisoformat(sample["date"])
        entry_time = (entered - EPOCH).days * DAY
        exit_time = (entered + timedelta(days=6) - EPOCH).days * DAY
        first = raw_bars[(sample["symbol"], entry_time)]
        last = raw_bars[(sample["symbol"], exit_time)]
        raw_return = Decimal(last[4]) / Decimal(first[1]) - 1
        error = abs(float(raw_return) - sample["gross_return"])
        assert error < 1e-10
        maximum_return_error = max(maximum_return_error, error)
        raw_checks += 1
    diagnostics = {}
    for segment in ("evaluation_1", "evaluation_2"):
        segment_weeks = [w for w in weeks if w["period"] == segment]
        diagnostics[segment] = {}
        for method in ("analogs", "equal_basket", "momentum"):
            original, flat, zero_cost, combined = [Decimal(1) for _ in range(4)]
            missing = []
            weekly_factors = {k: [] for k in ("original", "flat", "zero_cost", "combined")}
            for week in segment_weeks:
                holdings = [lookup[(week["date"], s)] for s in week["selections"][method]]
                if not holdings:
                    for values in weekly_factors.values():
                        values.append(1.0)
                    continue
                factors: list[Decimal] = []
                flat_factors: list[Decimal] = []
                free_factors: list[Decimal] = []
                both_factors: list[Decimal] = []
                for sample in holdings:
                    gross = Decimal(str(sample["gross_return"]))
                    factor = (1 + gross) * Decimal("0.998") / Decimal("1.002")
                    factors.append(factor)
                    free_factors.append(1 + gross)
                    flat_factors.append(Decimal(1) if sample["missing_outcome"] else factor)
                    both_factors.append(Decimal(1) if sample["missing_outcome"] else 1 + gross)
                    if sample["missing_outcome"]:
                        missing.append(
                            {
                                "date": sample["date"],
                                "symbol": sample["symbol"],
                                "reason": sample["missing_outcome"],
                            }
                        )
                f = sum(factors, Decimal(0)) / len(factors)
                ff = sum(flat_factors, Decimal(0)) / len(factors)
                zf = sum(free_factors, Decimal(0)) / len(factors)
                bf = sum(both_factors, Decimal(0)) / len(factors)
                original *= f
                flat *= ff
                zero_cost *= zf
                combined *= bf
                for key, value in zip(weekly_factors, (f, ff, zf, bf), strict=True):
                    weekly_factors[key].append(float(value))
            published = result["evaluation"][segment]["cost_scenarios"]["20"]["methods"][method][
                "compounded_return"
            ]
            assert abs(float(original - 1) - published) < 1e-10
            diagnostics[segment][method] = {
                "decimal_reconstruction_net_return": float(original - 1),
                "post_hoc_missing_holdings_flat_return": float(flat - 1),
                "post_hoc_zero_cost_return": float(zero_cost - 1),
                "post_hoc_missing_flat_and_zero_cost_return": float(combined - 1),
                "missing_holdings": missing,
                "weekly_factors": weekly_factors,
            }
        for scenario in ("original", "flat", "zero_cost", "combined"):
            a = diagnostics[segment]["analogs"]["weekly_factors"][scenario]
            b = diagnostics[segment]["equal_basket"]["weekly_factors"][scenario]
            diagnostics[segment]["analogs"][f"{scenario}_paired_log_mean_vs_basket"] = sum(
                math.log(x) - math.log(y) for x, y in zip(a, b, strict=True)
            ) / len(a)
    audit = {
        "audit_type": "POST_RESULT_ACCOUNTING_AND_FIDELITY_DIAGNOSTIC",
        "original_screen_decision_preserved": result["decision"],
        "research_priority_decision": "DO_NOT_PROMOTE_THIS_SELECTOR",
        "scientific_verdict": "INCONCLUSIVE_DATA_FIDELITY_FOR_EXECUTABLE_PNL",
        "interpretation": "The fixed stress specification failed. It is not evidence of universally absent pre-rally predictability or a measurement of executable loss. Missing candles include documented token migrations, so assigning zero recovery is only a stress scenario. Flat-recovery and zero-cost diagnostics retain the poor result, without refitting or selection changes; neither scenario is a universal bound on actual migration value.",
        "raw_response_hash_checks": n_hashes,
        "independent_raw_decimal_return_checks": raw_checks,
        "maximum_raw_return_difference": maximum_return_error,
        "independent_decimal_portfolio_checks": 6,
        "diagnostics": diagnostics,
        "coverage_caveat": "The frozen textual suffix filter also excludes JUPUSDT and SYRUPUSDT, legitimate token names ending in UP. This is a recorded sample-coverage limitation; the sample and results are not silently replaced after seeing outcomes.",
        "verified_migrations": [
            {
                "old": "FTM",
                "new": "S",
                "ratio": "1:1",
                "source": "https://www.binance.com/en/support/announcement/detail/aec6fcbc84b749eeab6690e6bcac2f3d",
            },
            {
                "old": "BNX",
                "new": "FORM",
                "ratio": "1:1",
                "source": "https://www.binance.com/en/support/announcement/detail/7d5accdcf8f446f3ba3d79f8747a28e2",
            },
        ],
        "source_access_date": "2026-09-07",
        "future_research_condition": "Before another selection trial: point-in-time token identity/migration handling, validated labels and investable universe; then new preregistration and genuinely new evaluation. Any objective redesign from rally frequency to expected net payoff is an adaptive new hypothesis, never a repair presented as untouched evidence.",
    }
    (root / "audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in audit.items() if k != "diagnostics"}, indent=2))
    print(
        json.dumps(
            {
                segment: {
                    m: {
                        k: v
                        for k, v in d.items()
                        if k not in ("weekly_factors", "missing_holdings")
                    }
                    for m, d in methods.items()
                }
                for segment, methods in diagnostics.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
