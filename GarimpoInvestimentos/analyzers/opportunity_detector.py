"""Deterministic market-opportunity detector.

This module is deliberately independent from LLM scores, scientific-family GO/NO-GO
states and capital authorization. Its job is narrower: detect material market moves
from point-in-time features so a human can review them while they are happening.

The detector does NOT authorize trades. It only emits an informational state.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

NORMAL = "NORMAL"
WATCH = "WATCH"
PERSISTENT = "PERSISTENT"
STRONG_MOVE = "STRONG_MOVE"

BULL = "bull"
BEAR = "bear"
NEUTRAL = "neutral"

_STATE_RANK = {NORMAL: 0, WATCH: 1, PERSISTENT: 2, STRONG_MOVE: 3}


@dataclass(frozen=True)
class OpportunitySignal:
    asset: str
    state: str
    direction: str
    reasons: tuple[str, ...]
    extension_risk: bool
    metrics: dict[str, float]

    @property
    def active(self) -> bool:
        return self.state != NORMAL

    @property
    def rank(self) -> int:
        return _STATE_RANK[self.state]

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BreadthSignal:
    active: bool
    direction: str
    count: int
    assets: tuple[str, ...]
    daily_move_threshold_pct: float

    def as_dict(self) -> dict:
        return asdict(self)


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _metric(hard_data: dict, key: str) -> float | None:
    return _number(hard_data.get(key))


def _indicator(hard_data: dict, key: str) -> float | None:
    indicators = hard_data.get("indicadores")
    if not isinstance(indicators, dict):
        return None
    return _number(indicators.get(key))


def augment_opportunity_features(
    hard_data: dict,
    normalized_candles: list[dict],
    *,
    source: str,
) -> dict:
    """Add detector-only features without changing the scientific/LLM feature contract.

    The LLM trial keeps receiving the exact existing hard_data. This function works on
    a copy and derives only point-in-time fields needed by the alert path.
    """

    out = dict(hard_data)
    if not normalized_candles:
        return out

    ordered = sorted(normalized_candles, key=lambda row: str(row.get("timestamp") or ""))
    closes = [_number(row.get("close")) for row in ordered]
    if all(value is not None for value in closes):
        clean_closes = [float(value) for value in closes if value is not None]
        if len(clean_closes) > 3 and clean_closes[-4] != 0:
            out["change_3d"] = round((clean_closes[-1] / clean_closes[-4] - 1) * 100, 2)

    if len(ordered) >= 21:
        quote_volumes: list[float] = []
        for row in ordered[-21:]:
            volume = _number(row.get("volume"))
            close = _number(row.get("close"))
            if volume is None or close is None or volume < 0 or close <= 0:
                quote_volumes = []
                break
            if source in {"binance", "kraken", "consensus_mean", "consensus_median"}:
                quote_volumes.append(volume * close)
            else:
                quote_volumes.append(volume)
        if len(quote_volumes) == 21:
            baseline = sum(quote_volumes[:-1]) / 20
            if baseline > 0:
                out["volume_ratio_20d"] = round(quote_volumes[-1] / baseline, 4)

    return out


def detect_asset_opportunity(asset: str, hard_data: dict) -> OpportunitySignal:
    """Detect a material directional move using only already-observed features.

    The three independent lenses intentionally answer different questions:

    * acceleration: is price moving unusually fast now?
    * trend: is the 7-day move confirmed by momentum?
    * persistence: did a large 30-day move survive short-term cooling?

    RSI is risk metadata, not a vote against the existence of a trend. An
    overbought market may be late/risky, but calling it "no trend" would hide
    exactly the kind of move this detector exists to surface.
    """

    ch1 = _metric(hard_data, "change_24h")
    ch3 = _metric(hard_data, "change_3d")
    ch7 = _metric(hard_data, "change_7d")
    ch30 = _metric(hard_data, "change_30d")
    volume_ratio = _metric(hard_data, "volume_ratio_20d")
    macd_hist = _indicator(hard_data, "macd_histogram")
    vs_sma50 = _indicator(hard_data, "preco_vs_sma50_pct")
    rsi = _indicator(hard_data, "rsi_14")

    bull_reasons: list[str] = []
    bear_reasons: list[str] = []

    bull_acceleration = False
    bear_acceleration = False

    if ch1 is not None and volume_ratio is not None:
        if ch1 >= 5.0 and volume_ratio >= 1.5:
            bull_acceleration = True
            bull_reasons.append("1d>=5% with volume_ratio_20d>=1.5")
        if ch1 <= -5.0 and volume_ratio >= 1.5:
            bear_acceleration = True
            bear_reasons.append("1d<=-5% with volume_ratio_20d>=1.5")

    if ch3 is not None:
        if ch3 >= 8.0:
            bull_acceleration = True
            bull_reasons.append("3d>=8%")
        if ch3 <= -8.0:
            bear_acceleration = True
            bear_reasons.append("3d<=-8%")

    if ch7 is not None:
        if ch7 >= 10.0:
            bull_acceleration = True
            bull_reasons.append("7d>=10%")
        if ch7 <= -10.0:
            bear_acceleration = True
            bear_reasons.append("7d<=-10%")

    bull_trend = ch7 is not None and ch7 >= 5.0 and macd_hist is not None and macd_hist > 0
    bear_trend = ch7 is not None and ch7 <= -5.0 and macd_hist is not None and macd_hist < 0
    if bull_trend:
        bull_reasons.append("7d>=5% with positive MACD histogram")
    if bear_trend:
        bear_reasons.append("7d<=-5% with negative MACD histogram")

    bull_persistent = ch30 is not None and ch30 >= 15.0 and vs_sma50 is not None and vs_sma50 > 0
    bear_persistent = ch30 is not None and ch30 <= -15.0 and vs_sma50 is not None and vs_sma50 < 0
    if bull_persistent:
        bull_reasons.append("30d>=15% and price above SMA50")
    if bear_persistent:
        bear_reasons.append("30d<=-15% and price below SMA50")

    bull_rank = 3 if bull_acceleration else 2 if bull_persistent else 1 if bull_trend else 0
    bear_rank = 3 if bear_acceleration else 2 if bear_persistent else 1 if bear_trend else 0

    if bull_rank == bear_rank:
        selected_rank = 0
        direction = NEUTRAL
        reasons: tuple[str, ...] = ()
    elif bull_rank > bear_rank:
        selected_rank = bull_rank
        direction = BULL
        reasons = tuple(bull_reasons)
    else:
        selected_rank = bear_rank
        direction = BEAR
        reasons = tuple(bear_reasons)

    state = {0: NORMAL, 1: WATCH, 2: PERSISTENT, 3: STRONG_MOVE}[selected_rank]
    extension_risk = bool(
        (direction == BULL and rsi is not None and rsi >= 70.0)
        or (direction == BEAR and rsi is not None and rsi <= 30.0)
    )

    metrics = {
        key: value
        for key, value in {
            "change_24h": ch1,
            "change_3d": ch3,
            "change_7d": ch7,
            "change_30d": ch30,
            "volume_ratio_20d": volume_ratio,
            "macd_histogram": macd_hist,
            "preco_vs_sma50_pct": vs_sma50,
            "rsi_14": rsi,
        }.items()
        if value is not None
    }

    return OpportunitySignal(
        asset=asset.lower(),
        state=state,
        direction=direction,
        reasons=reasons,
        extension_risk=extension_risk,
        metrics=metrics,
    )


def detect_market_breadth(
    signals: list[OpportunitySignal],
    *,
    min_assets: int = 2,
    daily_move_threshold_pct: float = 5.0,
) -> BreadthSignal:
    """Detect a market-wide one-day move across independently-scanned assets."""

    if min_assets < 1 or daily_move_threshold_pct <= 0:
        raise ValueError("breadth thresholds must be positive")

    bull_assets = tuple(
        sorted(
            s.asset for s in signals if s.metrics.get("change_24h", 0.0) >= daily_move_threshold_pct
        )
    )
    bear_assets = tuple(
        sorted(
            s.asset for s in signals if s.metrics.get("change_24h", 0.0) <= -daily_move_threshold_pct
        )
    )

    if len(bull_assets) >= min_assets and len(bull_assets) > len(bear_assets):
        return BreadthSignal(True, BULL, len(bull_assets), bull_assets, daily_move_threshold_pct)
    if len(bear_assets) >= min_assets and len(bear_assets) > len(bull_assets):
        return BreadthSignal(True, BEAR, len(bear_assets), bear_assets, daily_move_threshold_pct)
    return BreadthSignal(False, NEUTRAL, 0, (), daily_move_threshold_pct)


def should_notify_transition(previous: dict | None, current: OpportunitySignal) -> bool:
    """Notify on first active state, escalation or direction reversal.

    De-escalation from STRONG_MOVE to PERSISTENT is stored but intentionally quiet,
    preventing a daily alert stream while preserving the trend state.
    """

    if not current.active:
        return False
    if not previous:
        return True
    previous_direction = str(previous.get("direction") or NEUTRAL)
    previous_state = str(previous.get("state") or NORMAL)
    if previous_direction != current.direction:
        return True
    return current.rank > _STATE_RANK.get(previous_state, 0)
