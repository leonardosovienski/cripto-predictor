"""Official DPL adapters for V3 Binance Futures funding/open-interest data."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from predictor_core.contracts import SignalPoint

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord
from GarimpoInvestimentos.v3.collectors.oi_collector import OIRecord

SOURCE = "binance-futures"
COLLECTOR_VERSION = "funding-oi-v3/1"
SIGNAL_SCHEMA_VERSION = "crypto-signal/2"


def _time(milliseconds: int) -> datetime:
    return datetime.fromtimestamp(milliseconds / 1000, tz=UTC)


def _content_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def funding_signal_points(
    records: list[FundingRecord], *, ingested_at: datetime
) -> list[SignalPoint]:
    points = []
    for record in records:
        event_at = _time(record.funding_time_ms)
        digest = _content_hash(
            {
                "symbol": record.symbol,
                "funding_time_ms": record.funding_time_ms,
                "funding_rate": record.funding_rate,
                "mark_price": record.mark_price,
            }
        )
        points.append(
            SignalPoint(
                name=f"{record.symbol}:funding_rate",
                timestamp=event_at,
                event_at=event_at,
                published_at=event_at,
                ingested_at=ingested_at,
                vintage=ingested_at,
                value=record.funding_rate,
                source=SOURCE,
                instrument=record.symbol,
                metric="funding_rate",
                unit="ratio",
                content_hash=digest,
                collector_version=COLLECTOR_VERSION,
                schema_version=SIGNAL_SCHEMA_VERSION,
                quality_flags=frozenset({"published_at_exchange"}),
            ).require_enriched()
        )
    return points


def oi_signal_points(records: list[OIRecord], *, ingested_at: datetime) -> list[SignalPoint]:
    points = []
    for record in records:
        event_at = _time(record.timestamp_ms)
        published_at = event_at
        digest = _content_hash(
            {
                "symbol": record.symbol,
                "timestamp_ms": record.timestamp_ms,
                "oi_contracts": record.oi_contracts,
                "oi_notional_usd": record.oi_notional_usd,
            }
        )
        for metric, value, unit in (
            ("open_interest_contracts", record.oi_contracts, "contracts"),
            ("open_interest_notional_usd", record.oi_notional_usd, "USD"),
        ):
            points.append(
                SignalPoint(
                    name=f"{record.symbol}:{metric}",
                    timestamp=event_at,
                    event_at=event_at,
                    published_at=published_at,
                    ingested_at=ingested_at,
                    vintage=ingested_at,
                    value=value,
                    source=SOURCE,
                    instrument=record.symbol,
                    metric=metric,
                    unit=unit,
                    content_hash=digest,
                    collector_version=COLLECTOR_VERSION,
                    schema_version=SIGNAL_SCHEMA_VERSION,
                    quality_flags=frozenset({"published_at_exchange_timestamp"}),
                ).require_enriched()
            )
    return points


def persist_v3_derivatives(
    store: FeatureStore,
    *,
    funding: list[FundingRecord],
    open_interest: list[OIRecord],
    ingested_at: datetime,
) -> int:
    points = funding_signal_points(funding, ingested_at=ingested_at)
    points.extend(oi_signal_points(open_interest, ingested_at=ingested_at))
    return store.write_signals(points, require_enriched=True, scientific_state="COLLECTION_ONLY")


__all__ = [
    "COLLECTOR_VERSION",
    "SIGNAL_SCHEMA_VERSION",
    "SOURCE",
    "funding_signal_points",
    "oi_signal_points",
    "persist_v3_derivatives",
]
