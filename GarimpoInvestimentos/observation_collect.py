"""Minimal Binance derivatives collection for a closed UTC observation day."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.dpl.derivatives import persist_v3_derivatives
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.observation_quality import DEFAULT_AUDIT_LOG, run_daily
from GarimpoInvestimentos.v3.circuit_breaker import CircuitBreaker
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingCollector
from GarimpoInvestimentos.v3.collectors.oi_collector import OICollector


async def collect_day(
    *,
    day: date,
    db_path: Path = FEATURE_STORE_DB,
    audit_path: Path = DEFAULT_AUDIT_LOG,
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT"),
) -> list[dict]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    start_ms, end_ms = int(start.timestamp() * 1000), int(end.timestamp() * 1000) - 1
    funding = []
    open_interest = []
    for symbol in symbols:
        funding.extend(
            await FundingCollector(symbol, CircuitBreaker(f"funding_{symbol}")).fetch_range(
                start_ms, end_ms
            )
        )
        open_interest.extend(
            await OICollector(symbol, CircuitBreaker(f"oi_{symbol}")).fetch_range(start_ms, end_ms)
        )
    with FeatureStore(db_path) as store:
        persist_v3_derivatives(
            store,
            funding=funding,
            open_interest=open_interest,
            ingested_at=datetime.now(UTC),
        )
    return run_daily(db_path=db_path, day=day, audit_path=audit_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect one closed UTC day in COLLECTION_ONLY")
    parser.add_argument(
        "--date", type=date.fromisoformat, default=(datetime.now(UTC) - timedelta(days=1)).date()
    )
    parser.add_argument("--db", type=Path, default=FEATURE_STORE_DB)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args(argv)
    asyncio.run(collect_day(day=args.date, db_path=args.db, audit_path=args.audit_log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["collect_day"]
