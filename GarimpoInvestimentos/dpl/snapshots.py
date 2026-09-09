"""Exact normalized inputs for new diagnostics; no claim of historical HTTP vintages."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from GarimpoInvestimentos.dpl.feature_engineering import DAILY_FEATURE_VERSION

EVALUATION_CONTRACT = "future-daily-close-v1"


def _clean(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return [_clean(v) for v in sorted(value)]
    if isinstance(value, (tuple, list)):
        return [_clean(v) for v in value]
    return value


def encode(payload: dict) -> tuple[str, str]:
    text = json.dumps(
        _clean(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(text.encode()).hexdigest(), text


def decode(digest: str, text: str) -> dict:
    if hashlib.sha256(text.encode()).hexdigest() != digest:
        raise ValueError("input snapshot hash mismatch")
    return json.loads(text)


def market_payload(points, aligned, signals, *, collected_at=None) -> dict:
    if not points or not aligned:
        raise ValueError("empty market snapshot")
    ordered = sorted(points, key=lambda p: p.timestamp)
    last = ordered[-1]
    if len({(p.symbol, p.source, p.interval) for p in ordered}) != 1:
        raise ValueError("mixed identity/source/interval in market snapshot")
    return _clean(
        {
            "schema": "market-snapshot/1",
            "feature_version": DAILY_FEATURE_VERSION,
            "symbol": last.symbol,
            "source": last.source,
            "interval": last.interval,
            "collected_at": collected_at or datetime.now(UTC),
            "candle_open": last.timestamp,
            "available_at": last.published_at,
            "features": aligned[-1],
            "normalized_candles": [asdict(p) for p in ordered],
            "signals": {name: [asdict(s) for s in series] for name, series in signals.items()},
            "raw_http_response_preserved": False,
        }
    )


def serving_context(store, symbol: str, *, now: datetime | None = None) -> dict:
    """Only the current feature contract and a closed, recent, identified snapshot."""
    snapshot = store.latest_market_snapshot(symbol, "1d", DAILY_FEATURE_VERSION)
    if snapshot is None:
        raise ValueError("no current market snapshot; run --ingest")
    now = now or datetime.now(UTC)
    available = datetime.fromisoformat(snapshot["available_at"])
    collected = datetime.fromisoformat(snapshot["collected_at"])
    candle_open = datetime.fromisoformat(snapshot["candle_open"])
    if any(t.tzinfo is None for t in (available, collected, candle_open, now)):
        raise ValueError("market snapshot requires timezone-aware timestamps")
    if (
        snapshot["symbol"] != symbol
        or snapshot["interval"] != "1d"
        or not snapshot["source"]
        or available < candle_open + timedelta(days=1)
        or collected < available
    ):
        raise ValueError("market snapshot identity or daily closure is invalid")
    # One daily publication plus a small source-publication allowance. This
    # freshness gate does not make the old close an executable decision price.
    if available > now or collected > now or now - available > timedelta(hours=26):
        raise ValueError("market snapshot stale or not yet available; run --ingest")
    price = snapshot["features"].get("price_usd")
    if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
        raise ValueError("market snapshot has no valid positive price")
    return snapshot


def prediction_payload(
    snapshot, *, hard_data, news_result, prompt, analysis, judge, policy, started_at, completed_at
):
    return _clean(
        {
            "schema": "prediction-inputs/1",
            "evaluation_contract": EVALUATION_CONTRACT,
            "market_snapshot_id": snapshot["snapshot_id"],
            "market_source": snapshot["source"],
            "market_available_at": snapshot["available_at"],
            "market_candle_open": snapshot["candle_open"],
            "feature_version": snapshot["feature_version"],
            "hard_data": hard_data,
            "news_titles": list(news_result.titles),
            "news_provider": news_result.provider,
            "news_degraded_reason": news_result.degraded_reason,
            "news_received_at": news_result.received_at,
            "news_publication_times_verified": False,
            "prompt": prompt,
            "analysis": analysis,
            "judge": judge,
            "policy": policy,
            "analysis_started_at": started_at,
            "analysis_completed_at": completed_at,
            "interpretation": "Experimental score, not calibrated probability; future daily closes are gross price proxies, not fills.",
        }
    )
