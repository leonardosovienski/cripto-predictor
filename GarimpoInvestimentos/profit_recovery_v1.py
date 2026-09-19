"""Versioned causal opportunity research loop; never authorizes real capital.

This module is deliberately separate from frozen H1-H9 and from
``SHADOW_REFERENCE_CLOSE_ONLY``.  It supports two strictly distinct products:

* an ORACLE diagnostic catalog that may look into the future; and
* a causal candidate ledger whose candidates use information available at ``t``.

Forecasts are expanding-window and use only outcomes that have matured before the
candidate timestamp.  Daily-candle replay cannot certify executable fills, so it
leaves paper execution unavailable unless explicit contemporaneous quotes are
provided to ``paper_execute_v2``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sqlite3
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from statistics import NormalDist, fmean, median, stdev
from typing import Any

from GarimpoInvestimentos.analyzers.opportunity_detector import (
    BULL,
    augment_opportunity_features,
    detect_asset_opportunity,
    should_notify_transition,
)
from GarimpoInvestimentos.durable_io import atomic_write

SCHEMA_VERSION = "profit-recovery/v1"
LEVEL2_SCHEMA_VERSION = "reuse-verify-gap/v1"
CAPITAL_PERMISSION = False
HORIZONS = (1, 3, 7)


class CostEvidence(StrEnum):
    ASSUMED = "ASSUMED"
    ESTIMATED = "ESTIMATED"
    OBSERVED_MARKET = "OBSERVED_MARKET"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    REAL_FILL_CALIBRATED = "REAL_FILL_CALIBRATED"
    STRESSED = "STRESSED"


class Decision(StrEnum):
    TRADE = "TRADE"
    WATCH = "WATCH"
    NO_TRADE = "NO_TRADE"


class Capturability(StrEnum):
    CAPTURABLE_MISSED_OPPORTUNITY = "CAPTURABLE_MISSED_OPPORTUNITY"
    POSSIBLY_CAPTURABLE = "POSSIBLY_CAPTURABLE"
    TOO_LATE = "TOO_LATE"
    NOT_CAUSALLY_PREDICTABLE = "NOT_CAUSALLY_PREDICTABLE"
    NOT_ECONOMIC_AFTER_COSTS = "NOT_ECONOMIC_AFTER_COSTS"
    NOT_VERIFIED = "NOT_VERIFIED"


@dataclass(frozen=True)
class Candle:
    asset: str
    timestamp: datetime
    published_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str = "unknown"

    def __post_init__(self) -> None:
        for stamp in (self.timestamp, self.published_at):
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError("candle timestamps must be timezone-aware")
        for name in ("open", "high", "low", "close", "volume"):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value):
                raise ValueError(f"invalid candle {name}")
        if min(self.open, self.high, self.low, self.close) <= 0 or self.volume < 0:
            raise ValueError("invalid OHLCV")
        if self.high < max(self.open, self.close, self.low) or self.low > min(
            self.open, self.close, self.high
        ):
            raise ValueError("inconsistent OHLC")
        if self.published_at < self.timestamp:
            raise ValueError("published_at cannot predate candle timestamp")

    def normalized(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.astimezone(UTC).isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass(frozen=True)
class CostModelV1:
    venue: str
    instrument: str
    order_type: str
    fee_bps_per_leg: float
    spread_bps_round_trip: float
    slippage_bps_round_trip: float
    latency_bps_round_trip: float
    funding_bps: float = 0.0
    borrow_bps: float = 0.0
    infrastructure_bps: float = 0.0
    evidence: CostEvidence = CostEvidence.ASSUMED
    source_ref: str = "explicit research assumption"

    def __post_init__(self) -> None:
        values = (
            self.fee_bps_per_leg,
            self.spread_bps_round_trip,
            self.slippage_bps_round_trip,
            self.latency_bps_round_trip,
            self.funding_bps,
            self.borrow_bps,
            self.infrastructure_bps,
        )
        if any(isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("cost components must be finite and nonnegative")
        if not all((self.venue.strip(), self.instrument.strip(), self.order_type.strip())):
            raise ValueError("cost identity is required")

    @property
    def round_trip_bps(self) -> float:
        return (
            2 * self.fee_bps_per_leg
            + self.spread_bps_round_trip
            + self.slippage_bps_round_trip
            + self.latency_bps_round_trip
            + self.funding_bps
            + self.borrow_bps
            + self.infrastructure_bps
        )

    @property
    def break_even_edge(self) -> float:
        return self.round_trip_bps / 10_000

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["evidence"] = self.evidence.value
        row["round_trip_bps"] = self.round_trip_bps
        row["break_even_edge"] = self.break_even_edge
        return row


@dataclass(frozen=True)
class Forecast:
    horizon_days: int
    expected_gross_return: float | None
    expected_costs: float
    expected_net_return: float | None
    p_net_positive: float | None
    lower_bound_net_return: float | None
    predictive_uncertainty: float | None
    sample_size: int
    evidence: str


@dataclass(frozen=True)
class EconomicDecision:
    action: Decision
    reason: str
    forecast: Forecast
    signal_valid_until: str
    invalidation_rule: str
    capital_permission: bool = CAPITAL_PERMISSION


@dataclass(frozen=True)
class Quote:
    timestamp: datetime
    bid: float
    ask: float
    bid_qty: float
    ask_qty: float
    evidence: CostEvidence

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("quote timestamp must be timezone-aware")
        values = (self.bid, self.ask, self.bid_qty, self.ask_qty)
        if any(isinstance(v, bool) or not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError("quote values must be positive finite numbers")
        if self.ask < self.bid:
            raise ValueError("crossed quote")


def _iso(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return result.astimezone(UTC)


def _validate_series(candles: list[Candle]) -> None:
    if not candles:
        raise ValueError("empty candle series")
    if len({c.asset.lower() for c in candles}) != 1:
        raise ValueError("one asset per series required")
    for left, right in zip(candles, candles[1:], strict=False):
        if right.timestamp - left.timestamp != timedelta(days=1):
            raise ValueError("daily series must be contiguous")
        if right.timestamp <= left.timestamp or right.published_at <= left.published_at:
            raise ValueError("series timestamps must be strictly increasing")


def load_candles_sqlite(database: Path, *, asset: str, source: str = "binance") -> list[Candle]:
    """Read one immutable daily series.  No migrations or writes are permitted."""

    resolved = database.resolve()
    connection = sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        rows = connection.execute(
            """SELECT symbol, ts, published_at, open, high, low, close, volume, source
               FROM raw_market_data
               WHERE lower(symbol)=lower(?) AND source=? AND interval='1d'
               ORDER BY ts""",
            (asset, source),
        ).fetchall()
    finally:
        connection.close()
    candles = [
        Candle(
            asset=row[0].lower(),
            timestamp=_iso(row[1]),
            published_at=_iso(row[2]),
            open=float(row[3]),
            high=float(row[4]),
            low=float(row[5]),
            close=float(row[6]),
            volume=float(row[7]),
            source=row[8],
        )
        for row in rows
    ]
    _validate_series(candles)
    return candles


def load_candles_reconstructed_gzip(path: Path, *, trailing_rows: int = 200) -> list[Candle]:
    """Load a restored Binance daily export without changing its frozen bytes.

    The returned timestamps preserve event-time ordering, but the dataset remains
    RECONSTRUCTED_HISTORICAL because it was downloaded after the events.
    """

    payload = json.loads(gzip.decompress(path.read_bytes()))
    required = ["open_ms", "open", "high", "low", "close", "volume", "quote_volume", "close_ms"]
    if payload.get("columns") != required:
        raise ValueError("unsupported reconstructed candle schema")
    metadata = payload.get("metadata", {})
    rows = payload.get("rows", [])
    if metadata.get("rows") != len(rows) or metadata.get("missing_internal_days") != 0:
        raise ValueError("reconstructed candle integrity check failed")
    if trailing_rows < 57 or len(rows) < trailing_rows:
        raise ValueError("insufficient reconstructed candle history")
    asset = str(metadata["symbol"]).removesuffix("USDT").lower()
    candles = [
        Candle(
            asset=asset,
            timestamp=datetime.fromtimestamp(float(row[0]) / 1000, UTC),
            published_at=datetime.fromtimestamp(float(row[7]) / 1000, UTC),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
            source="binance",
        )
        for row in rows[-trailing_rows:]
    ]
    _validate_series(candles)
    return candles


def _ema(values: list[float], period: int) -> float:
    if len(values) < period:
        raise ValueError("insufficient EMA history")
    alpha = 2 / (period + 1)
    result = fmean(values[:period])
    for value in values[period:]:
        result = alpha * value + (1 - alpha) * result
    return result


def _rsi(values: list[float], period: int = 14) -> float:
    if len(values) < period + 1:
        raise ValueError("insufficient RSI history")
    diffs = [b - a for a, b in zip(values[-period - 1 : -1], values[-period:], strict=True)]
    gains = fmean(max(change, 0.0) for change in diffs)
    losses = fmean(max(-change, 0.0) for change in diffs)
    if losses == 0:
        return 100.0
    return 100 - 100 / (1 + gains / losses)


def _hard_data(prefix: list[Candle]) -> dict[str, Any]:
    closes = [c.close for c in prefix]
    if len(closes) < 50:
        raise ValueError("at least 50 daily candles required")
    macd = _ema(closes, 12) - _ema(closes, 26)
    previous_macd = _ema(closes[:-1], 12) - _ema(closes[:-1], 26)
    # A causal two-point approximation to the MACD signal is sufficient for the
    # detector's sign check and is explicitly versioned here.
    macd_hist = macd - (previous_macd * (1 - 2 / 10) + macd * 2 / 10)
    sma50 = fmean(closes[-50:])
    previous_20_high = max(c.high for c in prefix[-21:-1])
    previous_20_low = min(c.low for c in prefix[-21:-1])
    raw = {
        "change_24h": (closes[-1] / closes[-2] - 1) * 100,
        "change_7d": (closes[-1] / closes[-8] - 1) * 100,
        "change_30d": (closes[-1] / closes[-31] - 1) * 100,
        "breakout_20d": float(prefix[-1].close > previous_20_high),
        "breakdown_20d": float(prefix[-1].close < previous_20_low),
        "indicadores": {
            "macd_histogram": macd_hist,
            "preco_vs_sma50_pct": (closes[-1] / sma50 - 1) * 100,
            "rsi_14": _rsi(closes),
        },
    }
    return augment_opportunity_features(
        raw, [c.normalized() for c in prefix], source=prefix[-1].source
    )


def _future_outcome(candles: list[Candle], index: int, direction: str, horizon: int) -> dict:
    end = min(index + horizon, len(candles) - 1)
    future = candles[index + 1 : end + 1]
    if len(future) < horizon:
        return {"matured": False}
    sign = 1.0 if direction == BULL else -1.0
    entry = candles[index].close
    signed = sign * (future[-1].close / entry - 1)
    favorable_paths = [
        sign * ((bar.high if direction == BULL else bar.low) / entry - 1) for bar in future
    ]
    adverse_paths = [
        sign * ((bar.low if direction == BULL else bar.high) / entry - 1) for bar in future
    ]
    return {
        "matured": True,
        "future_return": signed,
        "mfe": max(favorable_paths),
        "mae": min(adverse_paths),
        "maximum_adverse_path": min(adverse_paths),
        "exit_timestamp": future[-1].timestamp.isoformat(),
        "exit_price": future[-1].close,
    }


def oracle_opportunity_catalog(
    candles: list[Candle], *, horizon_days: int = 7, move_threshold: float = 0.05
) -> list[dict[str, Any]]:
    """Find future moves with perfect hindsight; never feed candidates or forecasts."""

    _validate_series(candles)
    output: list[dict[str, Any]] = []
    active_direction: str | None = None
    for index in range(len(candles) - horizon_days):
        current = candles[index]
        future = candles[index + 1 : index + horizon_days + 1]
        up = max(bar.high / current.close - 1 for bar in future)
        down = min(bar.low / current.close - 1 for bar in future)
        direction = (
            BULL
            if up >= move_threshold and up >= abs(down)
            else "bear"
            if down <= -move_threshold
            else None
        )
        if direction is None:
            active_direction = None
            continue
        if direction == active_direction:
            continue
        active_direction = direction
        best = up if direction == BULL else -down
        output.append(
            {
                "catalog_type": "ORACLE_DIAGNOSTIC",
                "opportunity_id": f"oracle:{current.asset}:{current.timestamp.date()}:{direction}",
                "asset": current.asset,
                "timestamp": current.timestamp.isoformat(),
                "direction": direction,
                "horizon_days": horizon_days,
                "oracle_mfe": best,
                "oracle_mae": down if direction == BULL else -up,
                "used_for_training": False,
                "capital_permission": False,
            }
        )
    return output


def _forecast(
    history: list[dict[str, Any]],
    *,
    now: datetime,
    opportunity_class: str,
    direction: str,
    horizon_days: int,
    costs: CostModelV1,
) -> Forecast:
    matured = [
        row
        for row in history
        if row["opportunity_class"] == opportunity_class
        and row["direction"] == direction
        and row["horizon_days"] == horizon_days
        and _iso(row["outcome_available_at"]) <= now
        and row["future_return"] is not None
    ]
    values = [float(row["future_return"]) for row in matured]
    cost = costs.break_even_edge
    if not values:
        return Forecast(horizon_days, None, cost, None, None, None, None, 0, "NO_MATURED_SAMPLE")
    mean = fmean(values)
    if len(values) < 2:
        return Forecast(horizon_days, mean, cost, mean - cost, None, None, None, 1, "INSUFFICIENT")
    uncertainty = stdev(values)
    standard_error = uncertainty / math.sqrt(len(values))
    lower = mean - cost - 1.96 * standard_error
    if uncertainty == 0:
        probability = 1.0 if mean > cost else 0.0
    else:
        probability = NormalDist(mean - cost, uncertainty).cdf(0)
        probability = 1 - probability
    evidence = "EXPANDING_WINDOW_DIAGNOSTIC" if len(values) >= 5 else "INSUFFICIENT"
    return Forecast(
        horizon_days,
        mean,
        cost,
        mean - cost,
        probability,
        lower,
        uncertainty,
        len(values),
        evidence,
    )


def economic_decision(
    forecast: Forecast,
    *,
    candidate_time: datetime,
    costs: CostModelV1,
    min_sample: int = 20,
) -> EconomicDecision:
    valid_until = (candidate_time + timedelta(days=1)).isoformat()
    if forecast.expected_net_return is None:
        action, reason = Decision.WATCH, "forecast unavailable: no matured causal sample"
    elif forecast.sample_size < min_sample:
        action, reason = Decision.WATCH, f"sample {forecast.sample_size} below {min_sample}"
    elif costs.evidence in {CostEvidence.ASSUMED, CostEvidence.ESTIMATED, CostEvidence.STRESSED}:
        action, reason = (
            Decision.WATCH,
            f"cost evidence {costs.evidence.value} is not market observed",
        )
    elif forecast.lower_bound_net_return is None or forecast.lower_bound_net_return <= 0:
        action, reason = Decision.NO_TRADE, "conservative net return is not positive"
    elif forecast.p_net_positive is None or forecast.p_net_positive < 0.60:
        action, reason = Decision.NO_TRADE, "P(net>0) below 0.60"
    else:
        action, reason = Decision.TRADE, "conservative post-cost forecast is positive"
    return EconomicDecision(
        action,
        reason,
        forecast,
        valid_until,
        "state_normal_or_direction_reversal_or_24h_expiry",
    )


def causal_opportunity_ledger(
    candles: list[Candle],
    costs: CostModelV1,
    *,
    horizon_days: int = 3,
    min_decision_sample: int = 20,
) -> list[dict[str, Any]]:
    """Generate candidates at t, then append outcomes strictly as evaluation fields."""

    _validate_series(candles)
    rows: list[dict[str, Any]] = []
    forecast_history: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for index in range(50, len(candles)):
        hard_data = _hard_data(candles[: index + 1])
        signal = detect_asset_opportunity(candles[index].asset, hard_data)
        if not should_notify_transition(previous, signal):
            previous = signal.as_dict()
            continue
        now = candles[index].published_at
        forecast = _forecast(
            forecast_history,
            now=now,
            opportunity_class=signal.state,
            direction=signal.direction,
            horizon_days=horizon_days,
            costs=costs,
        )
        decision = economic_decision(
            forecast, candidate_time=now, costs=costs, min_sample=min_decision_sample
        )
        outcome = _future_outcome(candles, index, signal.direction, horizon_days)
        future_return = outcome.get("future_return")
        future_net = None if future_return is None else float(future_return) - costs.break_even_edge
        if future_return is None:
            capturability = Capturability.NOT_VERIFIED
        elif future_net is not None and future_net <= 0:
            capturability = Capturability.NOT_ECONOMIC_AFTER_COSTS
        elif decision.action is Decision.TRADE:
            capturability = Capturability.POSSIBLY_CAPTURABLE
        elif forecast.sample_size == 0:
            capturability = Capturability.NOT_CAUSALLY_PREDICTABLE
        else:
            capturability = Capturability.NOT_VERIFIED
        before = signal.metrics.get("change_7d", signal.metrics.get("change_3d", 0.0)) / 100
        available_features = dict(signal.metrics)
        available_features.update(
            {
                "breakout_20d": hard_data["breakout_20d"],
                "breakdown_20d": hard_data["breakdown_20d"],
            }
        )
        row = {
            "ledger_type": "CAUSAL_OPPORTUNITY_LEDGER",
            "schema_version": SCHEMA_VERSION,
            "opportunity_id": f"causal:{signal.asset}:{candles[index].timestamp.date()}:{signal.direction}",
            "asset": signal.asset,
            "candidate_timestamp": candles[index].timestamp.isoformat(),
            "opportunity_class": signal.state,
            "direction": signal.direction,
            "horizon_days": horizon_days,
            "features_available_at_t": available_features,
            "first_observable_time": candles[index].published_at.isoformat(),
            "first_actionable_time": candles[index].published_at.isoformat(),
            "price_at_signal": candles[index].close,
            "return_before_signal": before,
            "future_return_after_signal": future_return,
            "future_returns_after_signal": {
                "1h": None,
                "4h": None,
                "1d": _future_outcome(candles, index, signal.direction, 1).get("future_return"),
                "3d": _future_outcome(candles, index, signal.direction, 3).get("future_return"),
                "7d": _future_outcome(candles, index, signal.direction, 7).get("future_return"),
            },
            "intraday_outcome_status": "NOT_AVAILABLE_DAILY_DATA_FREQUENCY",
            "estimated_costs": costs.break_even_edge,
            "future_net_return": future_net,
            "MFE": outcome.get("mfe"),
            "MAE": outcome.get("mae"),
            "maximum_adverse_path": outcome.get("maximum_adverse_path"),
            "old_system_detected": False,
            "PR122_detected": True,
            "new_system_detected": True,
            "forecast": asdict(forecast),
            "decision": decision.action.value,
            "decision_reason": decision.reason,
            "paper_result": "NOT_AVAILABLE_MISSING_QUOTES",
            "capturability": capturability.value,
            "evidence": "PIT_CANDIDATE_WITH_RETROSPECTIVE_OUTCOME",
            "outcome_available_at": (
                candles[index + horizon_days].published_at.isoformat()
                if index + horizon_days < len(candles)
                else None
            ),
            "capital_permission": False,
        }
        rows.append(row)
        if outcome.get("matured"):
            forecast_history.append(
                {
                    "opportunity_class": signal.state,
                    "direction": signal.direction,
                    "horizon_days": horizon_days,
                    "future_return": future_return,
                    "outcome_available_at": candles[index + horizon_days].published_at.isoformat(),
                }
            )
        previous = signal.as_dict()
    return rows


def cluster_candidate_episodes(
    causal: list[dict[str, Any]], *, overlap_days: int = 7
) -> list[dict[str, Any]]:
    """Predeclared independence rule: same asset/direction within 7d is one episode."""

    output: list[dict[str, Any]] = []
    last: dict[tuple[str, str], tuple[datetime, str]] = {}
    episode_number = 0
    for original in sorted(causal, key=lambda row: _iso(row["candidate_timestamp"])):
        row = dict(original)
        key = (str(row["asset"]), str(row["direction"]))
        stamp = _iso(row["candidate_timestamp"])
        prior = last.get(key)
        if prior is None or stamp - prior[0] > timedelta(days=overlap_days):
            episode_number += 1
            episode_id = f"episode:{row['asset']}:{episode_number:04d}"
            independent = True
        else:
            episode_id = prior[1]
            independent = False
        row["episode_id"] = episode_id
        row["independent_event"] = independent
        row["episode_rule"] = f"same asset and direction within {overlap_days}d"
        output.append(row)
        last[key] = (stamp, episode_id)
    return output


def paper_execute_v2(
    *,
    opportunity_id: str,
    direction: str,
    requested_notional: float,
    decision_timestamp: datetime,
    entry: Quote,
    exit: Quote,
    fee_bps_per_leg: float,
    latency_seconds: float,
    exit_reason: str = "fixed_horizon",
) -> dict[str, Any]:
    """Explicit quote/depth paper fill.  It never calls a venue or sends an order."""

    if direction not in {BULL, "bear"}:
        raise ValueError("paper direction must be bull or bear")
    if requested_notional <= 0 or fee_bps_per_leg < 0 or latency_seconds < 0:
        raise ValueError("invalid paper terms")
    if entry.timestamp < decision_timestamp or exit.timestamp <= entry.timestamp:
        raise ValueError("paper timestamps violate causality")
    entry_price = entry.ask if direction == BULL else entry.bid
    exit_price = exit.bid if direction == BULL else exit.ask
    qty = requested_notional / entry_price
    available = entry.ask_qty if direction == BULL else entry.bid_qty
    exit_available = exit.bid_qty if direction == BULL else exit.ask_qty
    filled_qty = min(qty, available, exit_available)
    if filled_qty <= 0:
        status = "REJECTED"
    elif filled_qty < qty:
        status = "PARTIAL_FILL"
    else:
        status = "FILLED"
    sign = 1 if direction == BULL else -1
    gross = sign * filled_qty * (exit_price - entry_price)
    fees = filled_qty * (entry_price + exit_price) * fee_bps_per_leg / 10_000
    spread = filled_qty * ((entry.ask - entry.bid) + (exit.ask - exit.bid)) / 2
    return {
        "schema_version": "REALISTIC_PAPER_V2/1",
        "opportunity_id": opportunity_id,
        "decision_timestamp": decision_timestamp.isoformat(),
        "quote_timestamp": entry.timestamp.isoformat(),
        "bid": entry.bid,
        "ask": entry.ask,
        "order_type": "MARKETABLE",
        "requested_size": qty,
        "latency_seconds": latency_seconds,
        "fill_status": status,
        "filled_size": filled_qty,
        "partial_fill": status == "PARTIAL_FILL",
        "rejection": status == "REJECTED",
        "entry_price": entry_price,
        "fee": fees,
        "spread_cost": spread,
        "slippage": 0.0,
        "funding": 0.0,
        "mark_to_market": gross - fees,
        "exit_reason": exit_reason,
        "exit_price": exit_price,
        "gross_pnl": gross,
        "costs": fees,
        "net_pnl": gross - fees,
        "quote_evidence": min(entry.evidence, exit.evidence, key=list(CostEvidence).index).value,
        "capital_permission": False,
    }


def portfolio_summary(paper_trades: Iterable[dict[str, Any]], *, opening_cash: float) -> dict:
    if opening_cash <= 0 or not math.isfinite(opening_cash):
        raise ValueError("opening_cash must be positive")
    equity = opening_cash
    peak = opening_cash
    max_drawdown = 0.0
    gross = costs = turnover = 0.0
    curve = [{"index": 0, "equity": equity}]
    count = 0
    for count, trade in enumerate(paper_trades, 1):
        gross += float(trade["gross_pnl"])
        costs += float(trade["costs"])
        turnover += float(trade["filled_size"]) * (
            float(trade["entry_price"]) + float(trade["exit_price"])
        )
        equity += float(trade["net_pnl"])
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak)
        curve.append({"index": count, "equity": equity})
    return {
        "schema_version": "PAPER_PORTFOLIO_V1/1",
        "cash": equity,
        "open_positions": 0,
        "realized_pnl": equity - opening_cash,
        "unrealized_pnl": 0.0,
        "fees": costs,
        "funding": 0.0,
        "gross_exposure": 0.0,
        "net_exposure": 0.0,
        "equity_curve": curve,
        "turnover": turnover,
        "MaxDD": max_drawdown,
        "gross_pnl": gross,
        "costs": costs,
        "net_pnl": gross - costs,
        "trade_count": count,
        "capital_permission": False,
    }


def money_left_on_table(oracle: list[dict], causal: list[dict], paper: list[dict]) -> dict:
    captured_by_id = {row["opportunity_id"]: max(float(row["net_pnl"]), 0.0) for row in paper}
    capturable = sum(
        max(float(row["future_net_return"]), 0.0)
        for row in causal
        if row.get("future_net_return") is not None and row.get("decision") == Decision.TRADE.value
    )
    captured = sum(captured_by_id.values())
    oracle_value = sum(max(float(row["oracle_mfe"]), 0.0) for row in oracle)
    return {
        "ORACLE_MLTT": oracle_value,
        "ORACLE_MLTT_UNIT": "sum_of_per_event_returns_not_portfolio_value",
        "CAPTURABLE_OPPORTUNITY_VALUE": capturable,
        "CAPTURED_OPPORTUNITY_VALUE": captured,
        "MISSED_OPPORTUNITY_VALUE": max(capturable - captured, 0.0),
        "POLICY_MONEY_LEFT_ON_THE_TABLE": max(capturable - captured, 0.0),
        "policy_note": "causal frozen TRADE decisions only; oracle excluded",
    }


def baseline_report(causal: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare simple rules on the exact same candidate timestamps and costs."""

    strategies: dict[str, list[float]] = {
        name: []
        for name in (
            "always-flat",
            "buy-and-hold",
            "momentum-1d",
            "momentum-7d",
            "momentum-30d",
            "breakout-20d",
            "moving-average-trend",
            "mean-reversion-1d",
            "PR122-direction",
        )
    }
    for row in causal:
        signed = row.get("future_return_after_signal")
        if signed is None:
            continue
        underlying = float(signed) * (1 if row["direction"] == BULL else -1)
        features = row["features_available_at_t"]
        cost = float(row["estimated_costs"])
        directions = {
            "always-flat": 0,
            "buy-and-hold": 1,
            "momentum-1d": 1 if features.get("change_24h", 0) > 0 else -1,
            "momentum-7d": 1 if features.get("change_7d", 0) > 0 else -1,
            "momentum-30d": 1 if features.get("change_30d", 0) > 0 else -1,
            "breakout-20d": (
                1
                if features.get("breakout_20d", 0) > 0
                else -1
                if features.get("breakdown_20d", 0) > 0
                else 0
            ),
            "moving-average-trend": (1 if features.get("preco_vs_sma50_pct", 0) > 0 else -1),
            "mean-reversion-1d": -1 if features.get("change_24h", 0) > 0 else 1,
            "PR122-direction": 1 if row["direction"] == BULL else -1,
        }
        for name, direction in directions.items():
            strategies[name].append(0.0 if direction == 0 else direction * underlying - cost)

    return {
        name: {
            "sample_size": len(values),
            "mean_net_return": fmean(values) if values else None,
            "hit_rate": (sum(value > 0 for value in values) / len(values) if values else None),
            "sum_net_trade_returns_not_portfolio_pnl": sum(values),
        }
        for name, values in strategies.items()
    }


STRATEGY_NAMES = (
    "always-flat",
    "buy-and-hold",
    "momentum-1d",
    "momentum-7d",
    "momentum-30d",
    "breakout-20d",
    "moving-average-trend",
    "mean-reversion-1d",
    "PR122-direction",
)


def _strategy_gross_returns(row: dict[str, Any]) -> dict[str, float] | None:
    signed = row.get("future_return_after_signal")
    if signed is None:
        return None
    underlying = float(signed) * (1 if row["direction"] == BULL else -1)
    features = row["features_available_at_t"]
    directions = {
        "always-flat": 0,
        "buy-and-hold": 1,
        "momentum-1d": 1 if features.get("change_24h", 0) > 0 else -1,
        "momentum-7d": 1 if features.get("change_7d", 0) > 0 else -1,
        "momentum-30d": 1 if features.get("change_30d", 0) > 0 else -1,
        "breakout-20d": (
            1
            if features.get("breakout_20d", 0) > 0
            else -1
            if features.get("breakdown_20d", 0) > 0
            else 0
        ),
        "moving-average-trend": 1 if features.get("preco_vs_sma50_pct", 0) > 0 else -1,
        "mean-reversion-1d": -1 if features.get("change_24h", 0) > 0 else 1,
        "PR122-direction": 1 if row["direction"] == BULL else -1,
    }
    return {name: direction * underlying for name, direction in directions.items()}


def _return_metrics(gross: list[float], *, cost_rate: float, horizon_days: int = 3) -> dict:
    if not gross:
        return {
            "sample_size": 0,
            "gross_expectancy": None,
            "cost_expectancy": None,
            "net_expectancy": None,
            "median_net_return": None,
            "lower95_net_expectancy": None,
            "upper95_net_expectancy": None,
            "hit_rate": None,
            "profit_factor": None,
            "Sharpe_per_event_not_annualized": None,
            "Sortino_per_event_not_annualized": None,
            "MaxDD_compounded_event_sequence": None,
            "turnover_round_trips": 0,
            "time_in_market_event_days": 0,
        }
    active = [value != 0 for value in gross]
    net = [value - cost_rate if is_active else 0.0 for value, is_active in zip(gross, active)]
    mean = fmean(net)
    sigma = stdev(net) if len(net) > 1 else None
    standard_error = None if sigma is None else sigma / math.sqrt(len(net))
    losses = [value for value in net if value < 0]
    downside = math.sqrt(fmean(value**2 for value in losses)) if losses else None
    gains_sum = sum(value for value in net if value > 0)
    loss_sum = -sum(value for value in net if value < 0)
    equity = peak = 1.0
    max_drawdown = 0.0
    for value in net:
        equity *= max(1 + value, 0.0)
        peak = max(peak, equity)
        if peak:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return {
        "sample_size": len(net),
        "active_events": sum(active),
        "gross_expectancy": fmean(gross),
        "cost_expectancy": cost_rate * sum(active) / len(active),
        "net_expectancy": mean,
        "median_net_return": median(net),
        "minimum_net_return": min(net),
        "maximum_net_return": max(net),
        "lower95_net_expectancy": (
            None if standard_error is None else mean - 1.96 * standard_error
        ),
        "upper95_net_expectancy": (
            None if standard_error is None else mean + 1.96 * standard_error
        ),
        "hit_rate": sum(value > 0 for value in net) / len(net),
        "profit_factor": None if loss_sum == 0 else gains_sum / loss_sum,
        "Sharpe_per_event_not_annualized": (
            None if sigma is None or sigma == 0.0 else mean / sigma
        ),
        "Sortino_per_event_not_annualized": (
            None if downside is None or downside == 0.0 else mean / downside
        ),
        "MaxDD_compounded_event_sequence": max_drawdown,
        "turnover_round_trips": sum(active),
        "time_in_market_event_days": sum(active) * horizon_days,
    }


def strategy_economic_report(
    causal: list[dict[str, Any]], *, round_trip_bps: float
) -> dict[str, Any]:
    """Equal-cohort, equal-cost strategy comparison using independent episodes."""

    clustered = cluster_candidate_episodes(causal)
    independent = [row for row in clustered if row["independent_event"]]
    series: dict[str, list[float]] = {name: [] for name in STRATEGY_NAMES}
    for row in independent:
        returns = _strategy_gross_returns(row)
        if returns is None:
            continue
        for name, value in returns.items():
            series[name].append(value)
    metrics = {
        name: _return_metrics(values, cost_rate=round_trip_bps / 10_000)
        for name, values in series.items()
    }
    comparable = [name for name in STRATEGY_NAMES if name not in {"always-flat", "PR122-direction"}]
    available = [name for name in comparable if metrics[name]["net_expectancy"] is not None]
    best = max(available, key=lambda name: metrics[name]["net_expectancy"]) if available else None
    pr_values = series["PR122-direction"]
    best_values = series[best] if best else []
    cost_rate = round_trip_bps / 10_000
    paired = [
        (left - cost_rate if left != 0 else 0.0)
        - (right - cost_rate if right != 0 else 0.0)
        for left, right in zip(pr_values, best_values, strict=True)
    ]
    paired_mean = fmean(paired) if paired else None
    paired_se = stdev(paired) / math.sqrt(len(paired)) if len(paired) > 1 else None
    paired_lower = (
        None if paired_se is None or paired_mean is None else paired_mean - 1.96 * paired_se
    )
    paired_upper = (
        None if paired_se is None or paired_mean is None else paired_mean + 1.96 * paired_se
    )
    return {
        "signal_count": len(causal),
        "matured_signal_count": sum(row.get("future_return_after_signal") is not None for row in causal),
        "episode_count": len({row["episode_id"] for row in clustered}),
        "effective_independent_count": len(independent),
        "episode_rule": "same asset and direction within 7d; first candidate is effective event",
        "round_trip_bps": round_trip_bps,
        "strategies": metrics,
        "best_simple_baseline": best,
        "PR122_incremental_vs_best": {
            "mean": paired_mean,
            "lower95": paired_lower,
            "upper95": paired_upper,
            "paired_event_count": len(paired),
        },
    }


def _level2_verdict(base_report: dict[str, Any], stress_report: dict[str, Any]) -> str:
    pr = base_report["strategies"]["PR122-direction"]
    incremental = base_report["PR122_incremental_vs_best"]
    stress = stress_report["strategies"]["PR122-direction"]
    if base_report["effective_independent_count"] < 20:
        return "INCONCLUSIVE"
    if pr["upper95_net_expectancy"] is not None and pr["upper95_net_expectancy"] <= 0:
        return "NEGATIVE"
    if incremental["upper95"] is not None and incremental["upper95"] <= 0:
        return "NEGATIVE"
    if (
        pr["lower95_net_expectancy"] is not None
        and pr["lower95_net_expectancy"] > 0
        and incremental["lower95"] is not None
        and incremental["lower95"] > 0
        and stress["net_expectancy"] is not None
        and stress["net_expectancy"] > 0
    ):
        return "POSITIVE"
    return "INCONCLUSIVE"


def _split_cohorts(candles: list[Candle], causal: list[dict[str, Any]]) -> dict[str, list[dict]]:
    """Frozen 60/20/20 chronological rule; final is deliberately not evaluated."""

    development_end = candles[int(len(candles) * 0.60) - 1].timestamp
    validation_end = candles[int(len(candles) * 0.80) - 1].timestamp
    result: dict[str, list[dict]] = {"development": [], "validation": [], "reserved_final": []}
    for row in causal:
        stamp = _iso(row["candidate_timestamp"])
        bucket = (
            "development"
            if stamp <= development_end
            else "validation"
            if stamp <= validation_end
            else "reserved_final"
        )
        result[bucket].append(row)
    return result


def opportunity_metrics(oracle: list[dict], causal: list[dict]) -> dict[str, Any]:
    """Oracle-relative coverage diagnostics; explicitly not predictive evidence."""

    matches: list[tuple[dict, dict]] = []
    for event in oracle:
        oracle_time = _iso(event["timestamp"])
        candidates = [
            row
            for row in causal
            if row["asset"] == event["asset"]
            and row["direction"] == event["direction"]
            and oracle_time
            <= _iso(row["candidate_timestamp"])
            <= oracle_time + timedelta(days=int(event["horizon_days"]))
        ]
        if candidates:
            matches.append(
                (event, min(candidates, key=lambda row: _iso(row["candidate_timestamp"])))
            )
    latencies = [
        (_iso(candidate["first_observable_time"]) - _iso(event["timestamp"])).total_seconds() / 3600
        for event, candidate in matches
    ]
    economic = [row for row in causal if row.get("future_net_return") is not None]
    positive = [row for row in economic if float(row["future_net_return"]) > 0]
    return {
        "metric_scope": "RETROSPECTIVE_ORACLE_DIAGNOSTIC_NOT_PREDICTIVE_EVIDENCE",
        "oracle_events": len(oracle),
        "causal_candidates": len(causal),
        "matched_oracle_events": len(matches),
        "Opportunity_Miss_Rate": 1 - len(matches) / len(oracle) if oracle else None,
        "Detection_Latency_hours_mean": fmean(latencies) if latencies else None,
        "False_Opportunity_Rate_after_assumed_costs": (
            1 - len(positive) / len(economic) if economic else None
        ),
        "Economic_Alert_Precision_after_assumed_costs": (
            len(positive) / len(economic) if economic else None
        ),
        "Alert_Delivery_Rate": None,
        "Opportunity_Capture_Rate": None,
    }


def prepare_trial(spec: dict[str, Any], *, blockers: Iterable[str] = ()) -> dict[str, Any]:
    required = {
        "universe",
        "frequency",
        "opportunity_classes",
        "features",
        "target",
        "model_rule",
        "thresholds",
        "baseline",
        "entry",
        "exit",
        "cost_model",
        "sizing",
        "risk",
        "minimum_observations",
        "minimum_duration",
        "GO",
        "NO_GO",
        "INCONCLUSIVE",
        "version",
        "freeze_policy",
    }
    missing = sorted(required - spec.keys())
    if missing:
        raise ValueError("trial missing fields: " + ", ".join(missing))
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"), allow_nan=False)
    unresolved = sorted(set(blockers))
    return {
        "schema_version": "PROSPECTIVE_TRIAL_V1/1",
        "state": "NOT_READY" if unresolved else "READY_FROZEN",
        "spec": spec,
        "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "blockers": unresolved,
        "capital_permission": False,
    }


def freeze_trial(spec: dict[str, Any]) -> dict[str, Any]:
    return prepare_trial(spec)


def default_trial() -> dict[str, Any]:
    spec = {
        "universe": ["BTC", "ETH", "SOL"],
        "frequency": "1d candidate scan; event-time market quotes",
        "opportunity_classes": ["STRONG_MOVE", "PERSISTENT", "WATCH"],
        "features": [
            "returns",
            "momentum",
            "acceleration",
            "relative_volume",
            "volatility",
            "MACD",
            "RSI",
            "SMA_distance",
            "breadth",
            "cross_asset_confirmation",
        ],
        "target": "future_net_return_72h_from_first_executable_quote",
        "model_rule": "expanding-window-v1; outcomes available before candidate only",
        "thresholds": "PR122 frozen at 1b2bee85f552667ed74a17e5da3526b62541d2d2",
        "baseline": [
            "always-flat",
            "buy-and-hold",
            "momentum-1d",
            "momentum-7d",
            "momentum-30d",
            "breakout-20d",
            "moving-average-trend",
            "mean-reversion-1d",
        ],
        "entry": "first marketable observed quote no later than 5m after decision",
        "exit": "fixed 72h marketable observed quote; no oracle exit",
        "cost_model": "observed fee, spread, depth, slippage and latency; +50% stress",
        "sizing": "fixed 1 percent opening equity per independent event",
        "risk": "max 3 percent gross exposure; 15 percent MaxDD halt",
        "minimum_observations": 60,
        "minimum_duration": "180 calendar days; maximum 365 days",
        "GO": "lower95 net and incremental vs best baseline >0; PF>1.10; MaxDD<=15%; coverage and delivery>=99%; survives +50% cost stress",
        "NO_GO": "upper95 net or incremental <=0, or stressed upper95 <=0",
        "INCONCLUSIVE": "all other outcomes or fewer than 60 independent events by day 365",
        "version": "profit-recovery-prospective-v1",
        "freeze_policy": "any material change creates NEW_TRIAL_VERSION",
    }
    return prepare_trial(
        spec,
        blockers=(
            "MULTI_ASSET_PIT_DATA_NOT_CURRENT",
            "OBSERVED_MARKET_COSTS_NOT_AVAILABLE",
            "AUTOMATIC_SCHEDULER_NOT_ENABLED",
            "DELIVERY_ACK_NOT_OBSERVED",
        ),
    )


def operational_status(
    *,
    opportunity_state: Path,
    heartbeat: Path,
    now: datetime | None = None,
    expected_cadence_hours: float = 24.0,
) -> dict[str, Any]:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    state = (
        json.loads(opportunity_state.read_text(encoding="utf-8"))
        if opportunity_state.exists()
        else {}
    )
    beat = json.loads(heartbeat.read_text(encoding="utf-8")) if heartbeat.exists() else {}
    updated = _iso(state["updated_at"]) if state.get("updated_at") else None
    finished = _iso(beat["finished_at"]) if beat.get("finished_at") else None
    latest = max((stamp for stamp in (updated, finished) if stamp is not None), default=None)
    blind = None if latest is None else (now - latest).total_seconds() / 3600
    fresh = bool(blind is not None and blind <= expected_cadence_hours * 1.5)
    return {
        "SCHEDULE_CONFIGURED": bool(beat),
        "SCHEDULER_ENABLED": "NOT_VERIFIED",
        "HEARTBEAT_OBSERVED": bool(finished),
        "LIVE_SCAN_OBSERVED": bool(updated),
        "FRESH_DATA_OBSERVED": fresh,
        "ALERT_CREATED_OBSERVED": bool(state.get("assets")),
        "ALERT_DELIVERY_OBSERVED": bool(state and not state.get("delivery_pending", True)),
        "BLIND_TIME_MEASURABLE": latest is not None,
        "blind_time_hours": blind,
        "missed_cycles_lower_bound": (
            None if blind is None else max(math.floor(blind / expected_cadence_hours) - 1, 0)
        ),
        "capital_permission": False,
    }


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(
        path, (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    )


def synthetic_control() -> dict[str, Any]:
    """Deterministic integration control; never market evidence or a profit claim."""

    decision_time = datetime(2026, 1, 1, tzinfo=UTC)
    entry = Quote(
        decision_time + timedelta(seconds=2),
        bid=99,
        ask=100,
        bid_qty=20,
        ask_qty=20,
        evidence=CostEvidence.ESTIMATED,
    )
    exit_quote = Quote(
        decision_time + timedelta(days=3),
        bid=110,
        ask=111,
        bid_qty=20,
        ask_qty=20,
        evidence=CostEvidence.ESTIMATED,
    )
    paper = paper_execute_v2(
        opportunity_id="SYNTHETIC_CONTROL_ONLY",
        direction=BULL,
        requested_notional=1000,
        decision_timestamp=decision_time,
        entry=entry,
        exit=exit_quote,
        fee_bps_per_leg=10,
        latency_seconds=2,
    )
    return {
        "artifact_type": "SYNTHETIC_ENGINEERING_CONTROL_NOT_MARKET_EVIDENCE",
        "paper_trade": paper,
        "portfolio": portfolio_summary([paper], opening_cash=5000),
        "capital_permission": False,
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _asset_level2_result(
    candles: list[Candle], *, provenance: dict[str, Any], output: Path
) -> dict[str, Any]:
    base_cost = CostModelV1(
        venue="binance",
        instrument=f"{candles[0].asset.upper()}USDT spot proxy",
        order_type="marketable",
        fee_bps_per_leg=10,
        spread_bps_round_trip=5,
        slippage_bps_round_trip=10,
        latency_bps_round_trip=0,
        evidence=CostEvidence.ASSUMED,
        source_ref="frozen scenario assumption; no historical book/fill evidence",
    )
    causal = cluster_candidate_episodes(causal_opportunity_ledger(candles, base_cost))
    cohorts = _split_cohorts(candles, causal)
    scenario_bps = {
        "optimistic": 10.0,
        "base": 35.0,
        "conservative": 70.0,
        "stress": 105.0,
    }
    development = {
        name: strategy_economic_report(cohorts["development"], round_trip_bps=bps)
        for name, bps in scenario_bps.items()
    }
    validation = {
        name: strategy_economic_report(cohorts["validation"], round_trip_bps=bps)
        for name, bps in scenario_bps.items()
    }
    verdict = _level2_verdict(validation["base"], validation["stress"])
    write_json_artifact(
        output,
        {
            "schema_version": "CAUSAL_OPPORTUNITY_LEDGER/2",
            "asset": candles[0].asset,
            "data_classification": "RECONSTRUCTED_HISTORICAL",
            "rows": causal,
            "capital_permission": False,
        },
    )
    return {
        "asset": candles[0].asset,
        "coverage": {
            "rows": len(candles),
            "first_timestamp": candles[0].timestamp.isoformat(),
            "last_timestamp": candles[-1].timestamp.isoformat(),
        },
        "provenance": provenance,
        "data_classification": "RECONSTRUCTED_HISTORICAL",
        "data_classification_reason": (
            "event-time candles were downloaded/restored after events; no immutable "
            "received_at vintage proves what the system possessed at each t"
        ),
        "split_rule": "chronological 60/20/20 on trailing 200 daily rows",
        "cohort_candidate_counts": {name: len(rows) for name, rows in cohorts.items()},
        "development_diagnostic": development,
        "validation_diagnostic": validation,
        "reserved_final": {
            "status": "RESERVED_FINAL_INSUFFICIENT",
            "candidate_count_withheld": len(cohorts["reserved_final"]),
            "metrics_computed": False,
            "reason": (
                "the available history predates this freeze and the BTC history/PR122 "
                "threshold context was already inspected; it cannot honestly certify a final test"
            ),
        },
        "LEVEL_2_VERDICT": verdict,
        "ledger_path": str(output.resolve()),
    }


def run_level2_audit(
    *,
    btc_database: Path,
    eth_gzip: Path,
    sol_gzip: Path,
    output_directory: Path,
) -> dict[str, Any]:
    """Freeze BASELINE_V1, then run fixed-config BTC and ETH/SOL diagnostics."""

    output_directory.mkdir(parents=True, exist_ok=True)
    module_path = Path(__file__).resolve()
    detector_path = module_path.parent / "analyzers" / "opportunity_detector.py"
    previous_reports = {
        "AUDITORIA_ECONOMICA_SEQUENCIAL_20260919.md": Path(
            r"C:\Cripto\operacao\relatorios\AUDITORIA_ECONOMICA_SEQUENCIAL_20260919.md"
        ),
        "PROFIT_RECOVERY_EXECUTION.md": Path(
            r"C:\Cripto\operacao\relatorios\PROFIT_RECOVERY_EXECUTION.md"
        ),
    }
    baseline = {
        "schema_version": "BASELINE_V1/1",
        "frozen_at": datetime.now(UTC).isoformat(),
        "economic_baseline_commit": "1b2bee85f552667ed74a17e5da3526b62541d2d2",
        "implementation_commit_before_level2": "854854b6e7de41a95383aa881eccb4a4360d98a6",
        "measurement_module_sha256": _sha256_file(module_path),
        "detector_sha256": _sha256_file(detector_path),
        "detector_thresholds": {
            "acceleration": "1d abs>=5% and volume ratio>=1.5; or 3d abs>=8%; or 7d abs>=10%",
            "trend": "7d abs>=5% with direction-confirming MACD histogram",
            "persistence": "30d abs>=15% with direction-confirming SMA50 distance",
        },
        "features": [
            "change_24h",
            "change_3d",
            "change_7d",
            "change_30d",
            "volume_ratio_20d",
            "MACD_histogram",
            "SMA50_distance",
            "RSI14_risk_metadata",
        ],
        "candidate_horizon": "3d fixed close-to-close diagnostic",
        "outcome_horizons": {
            "1h": "NOT_AVAILABLE_DAILY_DATA_FREQUENCY",
            "4h": "NOT_AVAILABLE_DAILY_DATA_FREQUENCY",
            "1d": "available retrospective",
            "3d": "available retrospective",
            "7d": "available retrospective",
        },
        "episode_rule": "same asset and direction within 7d; first candidate is effective event",
        "split_rule": "trailing 200 contiguous daily rows; chronological 60/20/20",
        "reserved_final_status": "RESERVED_FINAL_INSUFFICIENT",
        "cost_scenarios_round_trip_bps": {
            "optimistic": 10.0,
            "base": 35.0,
            "conservative": 70.0,
            "stress": 105.0,
        },
        "cost_evidence": "ASSUMED",
        "changes_allowed": "measurement, provenance labels, integrity checks, and reports only",
        "economic_logic_changed": False,
        "capital_permission": False,
        "previous_report_hashes": {
            name: (_sha256_file(path) if path.exists() else "MISSING")
            for name, path in previous_reports.items()
        },
    }
    baseline_path = output_directory / "BASELINE_V1.json"
    write_json_artifact(baseline_path, baseline)

    btc = load_candles_sqlite(btc_database, asset="bitcoin", source="binance")[-200:]
    _validate_series(btc)
    eth = load_candles_reconstructed_gzip(eth_gzip, trailing_rows=200)
    sol = load_candles_reconstructed_gzip(sol_gzip, trailing_rows=200)
    inputs = {
        "btc": {
            "path": str(btc_database.resolve()),
            "sha256": _sha256_file(btc_database),
            "acquisition": "feature-store restored/current database; immutable read",
        },
        "eth": {
            "path": str(eth_gzip.resolve()),
            "sha256": _sha256_file(eth_gzip),
            "acquisition": "restored Binance REST reconstruction finalized 2026-09-07",
        },
        "sol": {
            "path": str(sol_gzip.resolve()),
            "sha256": _sha256_file(sol_gzip),
            "acquisition": "restored Binance REST reconstruction finalized 2026-09-07",
        },
    }
    assets = {
        "btc": _asset_level2_result(
            btc, provenance=inputs["btc"], output=output_directory / "BTC_CAUSAL_LEDGER_V2.json"
        ),
        "eth": _asset_level2_result(
            eth, provenance=inputs["eth"], output=output_directory / "ETH_CAUSAL_LEDGER_V2.json"
        ),
        "sol": _asset_level2_result(
            sol, provenance=inputs["sol"], output=output_directory / "SOL_CAUSAL_LEDGER_V2.json"
        ),
    }
    round_a = assets["btc"]["LEVEL_2_VERDICT"]
    round_b_values = [assets[name]["LEVEL_2_VERDICT"] for name in ("eth", "sol")]
    overall = (
        "NEGATIVE"
        if "NEGATIVE" in [round_a, *round_b_values]
        else "POSITIVE"
        if round_a == "POSITIVE" and all(value == "POSITIVE" for value in round_b_values)
        else "INCONCLUSIVE"
    )
    gaps = [
        {
            "gap": "NO_TRUE_PIT_RESERVED_FINAL",
            "proof": "all three inputs were already acquired/inspected before this freeze",
            "minimal_next_increment": "collect new append-only observations after BASELINE_V1",
        },
        {
            "gap": "NO_OBSERVED_EXECUTION_COSTS_OR_QUOTES",
            "proof": "historical inputs contain daily OHLCV only",
            "minimal_next_increment": "capture event-time bid/ask/depth and paper-fill acknowledgements",
        },
        {
            "gap": "NO_INTRADAY_OUTCOMES",
            "proof": "1h and 4h fields are unavailable at daily frequency",
            "minimal_next_increment": "append immutable hourly data prospectively; do not backfill as PIT",
        },
        {
            "gap": "NO_AUTOMATIC_DELIVERY_EVIDENCE",
            "proof": "configuration/heartbeat is not proof of user receipt",
            "minimal_next_increment": "record delivery acknowledgement in the prospective trial",
        },
    ]
    result = {
        "schema_version": LEVEL2_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "baseline_path": str(baseline_path.resolve()),
        "baseline_sha256": _sha256_file(baseline_path),
        "execution_order": [
            "freeze BASELINE_V1",
            "Round A BTC",
            "Round B ETH/SOL same configuration",
            "formal gap identification",
        ],
        "inputs": inputs,
        "assets": assets,
        "ROUND_A_BTC_VERDICT": round_a,
        "ROUND_B_ETH_SOL_VERDICT": (
            "NEGATIVE"
            if "NEGATIVE" in round_b_values
            else "POSITIVE"
            if all(value == "POSITIVE" for value in round_b_values)
            else "INCONCLUSIVE"
        ),
        "LEVEL_2_VERDICT": overall,
        "OPERATIONAL_VERDICT": "RESEARCH_ONLY",
        "PAPER_TRADING_READINESS": "NOT_READY",
        "MICROCAPITAL_READINESS": "NOT_READY",
        "gaps": gaps,
        "new_complexity_authorized": False,
        "prospective_trial": default_trial(),
        "capital_permission": False,
    }
    write_json_artifact(output_directory / "LEVEL2_EXECUTION.json", result)
    return result


def run_replay(database: Path, output: Path, *, asset: str, source: str) -> dict[str, Any]:
    candles = load_candles_sqlite(database, asset=asset, source=source)
    costs = CostModelV1(
        venue=source,
        instrument=f"{asset}/USDT spot proxy",
        order_type="marketable",
        fee_bps_per_leg=10,
        spread_bps_round_trip=5,
        slippage_bps_round_trip=10,
        latency_bps_round_trip=0,
        evidence=CostEvidence.ASSUMED,
        source_ref="research stress assumption; no historical book/fill evidence",
    )
    oracle = oracle_opportunity_catalog(candles)
    causal = causal_opportunity_ledger(candles, costs)
    result = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "source_database": str(database.resolve()),
        "source_database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        "asset": asset.lower(),
        "source": source,
        "coverage": {
            "rows": len(candles),
            "first_timestamp": candles[0].timestamp.isoformat(),
            "last_timestamp": candles[-1].timestamp.isoformat(),
            "last_published_at": candles[-1].published_at.isoformat(),
        },
        "cost_model": costs.as_dict(),
        "ORACLE_OPPORTUNITY_CATALOG": oracle,
        "CAUSAL_OPPORTUNITY_LEDGER": causal,
        "baselines": baseline_report(causal),
        "opportunity_metrics": opportunity_metrics(oracle, causal),
        "money_left_on_table": money_left_on_table(oracle, causal, []),
        "paper_execution": "NOT_AVAILABLE_MISSING_QUOTES",
        "prospective_edge": "NOT_VERIFIED",
        "prospective_trial": default_trial(),
        "capital_permission": False,
    }
    write_json_artifact(output, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    replay = sub.add_parser("replay-db")
    replay.add_argument("--database", type=Path, required=True)
    replay.add_argument("--output", type=Path, required=True)
    replay.add_argument("--asset", default="bitcoin")
    replay.add_argument("--source", default="binance")
    status = sub.add_parser("radar-status")
    status.add_argument("--state", type=Path, required=True)
    status.add_argument("--heartbeat", type=Path, required=True)
    status.add_argument("--output", type=Path)
    trial = sub.add_parser("prepare-trial")
    trial.add_argument("--output", type=Path, required=True)
    control = sub.add_parser("synthetic-control")
    control.add_argument("--output", type=Path, required=True)
    level2 = sub.add_parser("level2-audit")
    level2.add_argument("--btc-database", type=Path, required=True)
    level2.add_argument("--eth-gzip", type=Path, required=True)
    level2.add_argument("--sol-gzip", type=Path, required=True)
    level2.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "replay-db":
        result = run_replay(args.database, args.output, asset=args.asset, source=args.source)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "candidates": len(result["CAUSAL_OPPORTUNITY_LEDGER"]),
                    "capital_permission": False,
                }
            )
        )
    elif args.command == "radar-status":
        status_result = operational_status(opportunity_state=args.state, heartbeat=args.heartbeat)
        if args.output:
            write_json_artifact(args.output, status_result)
        print(json.dumps(status_result, indent=2))
    elif args.command == "prepare-trial":
        trial_result = default_trial()
        write_json_artifact(args.output, trial_result)
        print(json.dumps({"output": str(args.output), "state": trial_result["state"]}))
    elif args.command == "synthetic-control":
        control_result = synthetic_control()
        write_json_artifact(args.output, control_result)
        print(json.dumps({"output": str(args.output), "capital_permission": False}))
    else:
        level2_result = run_level2_audit(
            btc_database=args.btc_database,
            eth_gzip=args.eth_gzip,
            sol_gzip=args.sol_gzip,
            output_directory=args.output_directory,
        )
        print(
            json.dumps(
                {
                    "output": str(args.output_directory / "LEVEL2_EXECUTION.json"),
                    "LEVEL_2_VERDICT": level2_result["LEVEL_2_VERDICT"],
                    "capital_permission": False,
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
