"""Classify recorded daily gaps against sourced spot-market event intervals.

This is a retrospective audit annotation, never an OHLCV repair or a historical
signal. Raw observations and the frozen research universe remain unchanged.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.research_io import encoded, integer, sha, strict_json

REGISTRY = (
    Path(__file__).resolve().parents[1] / "docs/manual_dependencies_20260910/market_events.json"
)
DAY_MS = 86_400_000


def utc(value):
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
        raise ValueError("Event timestamps must be explicit UTC")
    return instant


def classify(gaps, registry):
    events = {}
    for event in registry["events"]:
        symbol = event["symbol"]
        if symbol in events or not event["sources"]:
            raise ValueError("Duplicate event or missing source")
        if utc(event["halt_utc"]) >= utc(event["resume_utc"]):
            raise ValueError("Invalid event interval")
        events[symbol] = event
    results, seen = [], set()
    for gap in gaps["results"]:
        symbol = gap["symbol"]
        first, last = integer(gap["start_ms"]), integer(gap["end_ms"])
        count = integer(gap["expected_days"], 1)
        if first % DAY_MS or last % DAY_MS or last < first:
            raise ValueError("Invalid daily gap grid")
        if count != (last - first) // DAY_MS + 1:
            raise ValueError("Inconsistent gap count")
        days = {(symbol, ms) for ms in range(first, last + 1, DAY_MS)}
        if days & seen:
            raise ValueError("Overlapping gaps")
        seen.update(days)
        event = events.get(symbol)
        structural = []
        for _, ms in sorted(days):
            start = datetime.fromtimestamp(ms / 1000, UTC)
            if (
                event
                and utc(event["halt_utc"]) <= start
                and start + timedelta(days=1) <= utc(event["resume_utc"])
            ):
                structural.append(start.date().isoformat())
        results.append(
            {
                "symbol": symbol,
                "missing_days": count,
                "explained_nontrading_days": structural,
                "unexplained_days": count - len(structural),
                "event": event,
                "action": "Keep gap; prohibit returns/windows bridging instrument episodes",
            }
        )
    total = sum(row["missing_days"] for row in results)
    if integer(gaps["missing_days_total"]) != total:
        raise ValueError("Inconsistent total")
    explained = sum(len(row["explained_nontrading_days"]) for row in results)
    return {
        "missing_days": total,
        "explained_nontrading_days": explained,
        "unexplained_days": total - explained,
        "candles_created": 0,
        "historical_signal_eligible": False,
        "universal_coverage_certified": False,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gaps", type=Path, required=True)
    parser.add_argument("--events", type=Path, default=REGISTRY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gaps, events = args.gaps.read_bytes(), args.events.read_bytes()
    result = classify(strict_json(gaps), strict_json(events))
    result.update(gaps_sha256=sha(gaps), events_sha256=sha(events))
    with args.output.open("xb") as stream:
        stream.write(encoded(result) + b"\n")
    print(encoded({k: v for k, v in result.items() if k != "results"}).decode())


if __name__ == "__main__":
    main()
