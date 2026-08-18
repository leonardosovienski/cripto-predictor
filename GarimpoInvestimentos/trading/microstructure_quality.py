"""Watchdog and daily scorecards for prospective Spot microstructure."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from GarimpoInvestimentos.trading.store import SCIENTIFIC_STATE, TradingStore


@dataclass(frozen=True)
class WatchdogFinding:
    severity: str
    symbol: str
    stream: str
    reason: str


def watchdog(
    store: TradingStore, *, now: datetime | None = None, stale_seconds: float = 30.0
) -> list[WatchdogFinding]:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    latest = {(row["symbol"], row["kind"]): row for row in store.latest_microstructure()}
    findings: list[WatchdogFinding] = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for kind in ("trade", "bbo", "depth", "snapshot"):
            row = latest.get((symbol, kind))
            if row is None:
                findings.append(WatchdogFinding("critical", symbol, kind, "missing"))
                continue
            age = (now - datetime.fromisoformat(row["received_at"]).astimezone(UTC)).total_seconds()
            if age > stale_seconds:
                findings.append(WatchdogFinding("critical", symbol, kind, f"stale:{age:.3f}s"))
            if row["scientific_state"] != SCIENTIFIC_STATE:
                findings.append(WatchdogFinding("critical", symbol, kind, "scientific_state"))
            payload = json.loads(row["payload_json"])
            if kind == "bbo" and payload["bid_price"] >= payload["ask_price"]:
                findings.append(WatchdogFinding("critical", symbol, kind, "crossed_book"))
            if kind == "snapshot":
                if not payload["bids"] or not payload["asks"]:
                    findings.append(WatchdogFinding("critical", symbol, kind, "empty_book"))
                elif payload["bids"][0][0] >= payload["asks"][0][0]:
                    findings.append(WatchdogFinding("critical", symbol, kind, "crossed_book"))
    return findings


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil((len(ordered) - 1) * quantile)]


def daily_scorecards(store: TradingStore, day: date) -> list[dict[str, Any]]:
    start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
    rows = store.quality_rows(start, start + timedelta(days=1))
    result: list[dict[str, Any]] = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for kind in ("trade", "bbo", "depth", "snapshot"):
            selected = [r for r in rows if r["symbol"] == symbol and r["kind"] == kind]
            latencies = []
            ingest_latencies = []
            hashes: dict[str, str] = {}
            duplicates = conflicts = temporal = crossed = gaps = 0
            previous_sequence: int | None = None
            for row in selected:
                received = datetime.fromisoformat(row["received_at"])
                ingested = datetime.fromisoformat(row["ingested_at"])
                ingest_latencies.append((ingested - received).total_seconds() * 1000)
                if row["event_at"]:
                    event = datetime.fromisoformat(row["event_at"])
                    latencies.append((received - event).total_seconds() * 1000)
                    temporal += int(event > received)
                key = row["observation_id"]
                if key in hashes:
                    duplicates += 1
                    conflicts += int(hashes[key] != row["payload_hash"])
                hashes[key] = row["payload_hash"]
                sequence = row["sequence_id"]
                if (
                    kind == "depth"
                    and previous_sequence is not None
                    and sequence <= previous_sequence
                ):
                    gaps += 1
                previous_sequence = sequence
                payload = json.loads(row["payload_json"])
                if kind == "bbo":
                    crossed += int(payload["bid_price"] >= payload["ask_price"])
            degraded = not selected or gaps > 0 or conflicts > 0 or temporal > 0 or crossed > 0
            result.append(
                {
                    "day": day.isoformat(),
                    "venue": "binance_spot",
                    "symbol": symbol,
                    "stream": kind,
                    "scientific_state": SCIENTIFIC_STATE,
                    "status": "DEGRADED" if degraded else "OBSERVED_NOT_PROMOTED",
                    "observations": len(selected),
                    "coverage": int(bool(selected)),
                    "availability": int(bool(selected)),
                    "gaps": gaps,
                    "duplicates": duplicates,
                    "hash_conflicts": conflicts,
                    "temporal_integrity_failures": temporal,
                    "crossed_books": crossed,
                    "latency_event_received_ms": {
                        "p50": _percentile(latencies, 0.5),
                        "p95": _percentile(latencies, 0.95),
                        "p99": _percentile(latencies, 0.99),
                    },
                    "latency_received_ingested_ms": {
                        "p50": _percentile(ingest_latencies, 0.5),
                        "p95": _percentile(ingest_latencies, 0.95),
                        "p99": _percentile(ingest_latencies, 0.99),
                    },
                    "resynchronizations": 0,
                    "degraded_periods": int(degraded),
                }
            )
    return result
