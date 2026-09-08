"""Cost-aware abstention gate for V3 signals.

Signal ``strength`` is a regime/funding intensity score, not a forecast return.
This module estimates signed returns on matured in-sample signals and allows an
OOS trade only when the conservative estimate remains positive after the cost
model and currently observable funding.
"""

from __future__ import annotations

import math
import statistics as st
from dataclasses import dataclass

from GarimpoInvestimentos.v3.costs import CostModel


@dataclass(frozen=True)
class EdgeEstimate:
    expected_signed_return: float
    lower_signed_return: float
    upper_signed_return: float
    standard_error: float
    sample_size: int


@dataclass(frozen=True)
class EconomicDecision:
    action: str
    expected_net_return: float | None
    conservative_net_return: float | None
    required_net_edge: float
    estimated_round_trip_friction: float
    estimated_funding_pnl: float
    calibration_sample_size: int
    reason: str
    capital_enabled: bool = False


def estimate_edge(
    signed_returns: list[float],
    *,
    minimum_sample: int = 20,
    z_score: float = 1.96,
) -> EdgeEstimate | None:
    """Estimate mean signed return without looking at the evaluation period."""
    values = [float(value) for value in signed_returns if math.isfinite(float(value))]
    if minimum_sample < 2 or z_score <= 0:
        raise ValueError("invalid edge-estimation policy")
    if len(values) < minimum_sample:
        return None
    mean = st.mean(values)
    standard_error = st.stdev(values) / math.sqrt(len(values))
    return EdgeEstimate(
        expected_signed_return=mean,
        lower_signed_return=mean - z_score * standard_error,
        upper_signed_return=mean + z_score * standard_error,
        standard_error=standard_error,
        sample_size=len(values),
    )


def decide_cost_aware(
    estimate: EdgeEstimate | None,
    *,
    direction: int,
    funding_rate: float,
    horizon_hours: float,
    costs: CostModel,
    minimum_net_edge: float = 0.0,
) -> EconomicDecision:
    """Return TRADE only if conservative post-cost return clears the hurdle."""
    if (
        direction not in {-1, 1}
        or horizon_hours <= 0
        or minimum_net_edge < 0
        or not math.isfinite(float(funding_rate))
    ):
        raise ValueError("invalid economic decision inputs")
    friction = costs.friction(float(direction))
    funding_pnl = costs.funding_pnl(float(direction), float(funding_rate), horizon_hours)
    if estimate is None:
        return EconomicDecision(
            action="NO_TRADE",
            expected_net_return=None,
            conservative_net_return=None,
            required_net_edge=minimum_net_edge,
            estimated_round_trip_friction=friction,
            estimated_funding_pnl=funding_pnl,
            calibration_sample_size=0,
            reason="INSUFFICIENT_EDGE_CALIBRATION",
        )
    expected_net = estimate.expected_signed_return + funding_pnl - friction
    conservative_net = estimate.lower_signed_return + funding_pnl - friction
    action = "SHADOW_TRADE" if conservative_net > minimum_net_edge else "NO_TRADE"
    return EconomicDecision(
        action=action,
        expected_net_return=expected_net,
        conservative_net_return=conservative_net,
        required_net_edge=minimum_net_edge,
        estimated_round_trip_friction=friction,
        estimated_funding_pnl=funding_pnl,
        calibration_sample_size=estimate.sample_size,
        reason="EDGE_CLEARS_COSTS" if action == "SHADOW_TRADE" else "EDGE_DOES_NOT_CLEAR_COSTS",
    )


__all__ = ["EconomicDecision", "EdgeEstimate", "decide_cost_aware", "estimate_edge"]
