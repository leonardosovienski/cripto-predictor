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
import hashlib
import json
import math
import sqlite3
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from statistics import NormalDist, fmean, stdev
from typing import Any

from GarimpoInvestimentos.analyzers.opportunity_detector import (
    BULL,
    augment_opportunity_features,
    detect_asset_opportunity,
    should_notify_transition,
)
from GarimpoInvestimentos.durable_io import atomic_write

SCHEMA_VERSION = "profit-recovery/v1"
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
    else:
        control_result = synthetic_control()
        write_json_artifact(args.output, control_result)
        print(json.dumps({"output": str(args.output), "capital_permission": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
