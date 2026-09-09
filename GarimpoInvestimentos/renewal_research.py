"""Read-only renewal cost bounds on a fixed, declared inventory trajectory.

These are partial historical accounting bounds, not fills, a new signal backtest,
personal net profit, or permission to deploy. Frozen engines are never imported.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from GarimpoInvestimentos.profit_research import nonnegative, number, text, transition

ZERO = Decimal(0)
HOUR_MS = 3_600_000


def _integer(value: Any) -> int:
    result = number(value)
    if result != int(result) or result < 0:
        raise ValueError("Expected a nonnegative integer")
    return int(result)


def _positive(value: Any) -> Decimal:
    result = number(value)
    if result <= 0:
        raise ValueError("Expected a positive value")
    return result


def _equal(left: Any, right: Any, label: str) -> None:
    if abs(number(left) - number(right)) > Decimal("0.0000001"):
        raise ValueError("Reference accounting mismatch: " + label)


def renewal_bound(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate the declared ledger and bound savings only at adjacent renewals."""
    currency = text(spec["currency"])
    evidence = text(spec["evidence_ref"])
    identities = [text(value) for value in spec["instruments"]]
    if len(identities) != 2 or identities[0] == identities[1]:
        raise ValueError("Two distinct spot/perpetual instrument identities required")
    start, end = _integer(spec["start_ms"]), _integer(spec["end_ms"])
    if start >= end:
        raise ValueError("Invalid research interval")
    step = _positive(spec["quantity_step"])
    reference = spec["reference"]
    capital = _positive(reference["initial_usdt"])
    if currency != "USDT":
        raise ValueError("The supplied reference ledger is explicitly denominated in USDT")
    costs = spec["costs"]
    bps = [
        nonnegative(costs[name]) + nonnegative(costs["slippage_bps_each_leg"])
        for name in ("spot_fee_bps_side", "perp_fee_bps_side")
    ]
    multiplier = nonnegative(costs["positive_funding_multiplier"])
    if multiplier > 1:
        raise ValueError("Funding stress multiplier must not amplify positive income")
    shock_fraction = nonnegative(costs["entry_unhedged_shock_fraction_notional"])
    spells = spec["spells"]
    if not isinstance(spells, list):
        raise ValueError("Expected an ordered list of holding spells")
    totals: dict[str, Decimal] = dict.fromkeys(("funding", "basis", "execution", "shock"), ZERO)
    previous_exit = start
    for spell in spells:
        entry, exit_ = _integer(spell["entry_ms"]), _integer(spell["exit_ms"])
        if not previous_exit <= entry < exit_ <= end or entry % HOUR_MS or exit_ % HOUR_MS:
            raise ValueError("Unsorted, overlapping, out-of-period or non-hour-aligned spells")
        previous_exit = exit_
        if spell["instruments"] != identities:
            raise ValueError("Cannot net different venues, contracts or settlement currencies")
        quantity = _positive(spell["quantity"])
        if quantity % step:
            raise ValueError("Reference quantity is off the declared grid")
        prices = {
            name: _positive(spell[name])
            for name in ("spot_entry", "spot_exit", "perp_entry", "perp_exit")
        }
        for side in ("entry", "exit"):
            expected = (
                quantity
                * sum(
                    (
                        prices[f"{leg}_{side}"] * rate
                        for leg, rate in zip(("spot", "perp"), bps, strict=True)
                    ),
                    ZERO,
                )
                / 10000
            )
            recorded = nonnegative(spell[f"{side}_cost_usdt"])
            _equal(expected, recorded, side + " costs")
            totals["execution"] += recorded
        basis = quantity * (
            prices["spot_exit"] - prices["spot_entry"] + prices["perp_entry"] - prices["perp_exit"]
        )
        _equal(basis, spell["basis_pnl_usdt"], "basis cashflow")
        totals["basis"] += number(spell["basis_pnl_usdt"])
        totals["funding"] += number(spell["funding_usdt"])
        shock = nonnegative(spell["unhedged_shock_usdt"])
        _equal(quantity * prices["spot_entry"] * shock_fraction, shock, "entry shock")
        totals["shock"] += shock
    for name, field in (
        ("funding", "funding_usdt"),
        ("basis", "basis_pnl_usdt"),
        ("execution", "fees_slippage_usdt"),
        ("shock", "unhedged_shock_usdt"),
    ):
        _equal(totals[name], reference[field], field)
    residual = nonnegative(reference["residual_cost_usdt"])
    elapsed_with_fixed_cost = (
        Decimal(end - _integer(spells[0]["entry_ms"])) / 86400000 if spells else ZERO
    )
    _equal(
        nonnegative(costs["annual_residual_usdt"]) * elapsed_with_fixed_cost / 365,
        residual,
        "fixed overhead",
    )
    original = (
        totals["funding"] + totals["basis"] - totals["execution"] - totals["shock"] - residual
    )
    _equal(original, reference["profit_usdt_mechanical"], "profit")
    _equal(capital + original, reference["ending_usdt_mechanical"], "ending capital")
    events: list[tuple[int, Decimal]] = []
    previous_event = -1
    for event in spec["funding_events"]:
        timestamp = _integer(event["fundingTime"])
        if timestamp <= previous_event or not start <= timestamp < end:
            raise ValueError("Duplicate, unsorted or out-of-period funding events")
        previous_event = timestamp
        flow = number(event["fundingRate"]) * _positive(event["markPrice"])
        events.append((timestamp, flow * multiplier if flow > 0 else flow))
    # Separate path: rebuild every reference funding receipt from market events.
    for spell in spells:
        held = [
            flow
            for timestamp, flow in events
            if timestamp // HOUR_MS > _integer(spell["entry_ms"]) // HOUR_MS
            and timestamp < _integer(spell["exit_ms"])
        ]
        _equal(
            _positive(spell["quantity"]) * sum(held, ZERO), spell["funding_usdt"], "signed funding"
        )

    renewals = []
    for before, after in zip(spells, spells[1:], strict=False):
        if before["exit_ms"] != after["entry_ms"]:
            continue
        quantities = (_positive(before["quantity"]), _positive(after["quantity"]))
        legs = []
        for index, leg in enumerate(("spot", "perp")):
            price = _positive(before[f"{leg}_exit"])
            if price != _positive(after[f"{leg}_entry"]):
                raise ValueError("Renewal prices differ; same-price netting is not justified")
            sign = 1 if leg == "spot" else -1
            legs.append(
                transition(
                    {
                        "current_instrument": identities[index],
                        "target_instrument": identities[index],
                        "current_quantity": quantities[0] * sign,
                        "target_quantity": quantities[1] * sign,
                        "price": price,
                        "quantity_step": step,
                        "cost_bps": bps[index],
                    }
                )
            )
        flows = [
            flow
            for timestamp, flow in events
            if _integer(after["entry_ms"]) <= timestamp < _integer(after["entry_ms"]) + HOUR_MS
        ]
        positive = sum((flow for flow in flows if flow > 0), ZERO)
        negative = sum((flow for flow in flows if flow < 0), ZERO)
        renewals.append(
            {
                "at_ms": after["entry_ms"],
                "old_quantity": str(quantities[0]),
                "target_quantity": str(quantities[1]),
                "legs": legs,
                "close_reopen_cost": str(
                    sum((number(row["close_reopen_cost"]) for row in legs), ZERO)
                ),
                "delta_only_cost": str(
                    sum((number(row["adjust_only_cost"]) for row in legs), ZERO)
                ),
                "delta_only_savings": str(
                    sum((number(row["modelled_cost_difference"]) for row in legs), ZERO)
                ),
                "renewal_shock_waiver": str(nonnegative(after["unhedged_shock_usdt"])),
                "optimistic_extra_positive_boundary_funding": str(max(quantities) * positive),
                "signed_continuity_boundary_diagnostic": str(
                    min(quantities) * (positive + negative)
                ),
                "additional_negative_boundary_diagnostic": str(min(quantities) * negative),
            }
        )
    total = lambda key: sum((number(row[key]) for row in renewals), ZERO)
    strict_bound = original + total("close_reopen_cost")
    extended_bound = (
        strict_bound
        + total("renewal_shock_waiver")
        + total("optimistic_extra_positive_boundary_funding")
    )
    sensitivities = []
    for amount in (1000, 5000, 25000):
        scale = Decimal(amount) / capital
        sensitivities.append(
            {
                "capital_usdt": str(amount),
                "optimistic_scale_only_remainder_usdt": str(
                    (extended_bound + residual) * scale - residual
                ),
                "status": "ANALYTICAL_SCENARIO_NOT_A_BACKTEST_OR_CAPACITY_PROOF",
            }
        )
    return {
        "currency": currency,
        "evidence_ref": evidence,
        "capital": str(capital),
        "duration_days": str(Decimal(end - start) / 86400000),
        "holding_spells": len(spells),
        "adjacent_renewals": len(renewals),
        "accounting": {
            **{key: str(value) for key, value in totals.items()},
            "residual": str(residual),
        },
        "reference_partial_remainder": str(original),
        "delta_turnover_savings_only": str(total("delta_only_savings")),
        "partial_remainder_with_delta_costs_only": str(original + total("delta_only_savings")),
        "zero_renewal_execution_cost_upper_bound": str(strict_bound),
        "extended_optimistic_upper_bound_not_profit": str(extended_bound),
        "upper_bound_still_nonpositive": extended_bound <= 0,
        "renewals": renewals,
        "capital_sensitivities": sensitivities,
        "net": None,
        "capital_permission": False,
        "unknown_costs": [
            "personal_fees",
            "tax",
            "conversion_and_transfers",
            "custody_and_operational_losses",
        ],
        "limitations": [
            "Fixed reference quantities; savings are not reinvested or fed into later sizing.",
            "Upper bounds deliberately waive necessary delta trades, renewal shock and additional negative boundary funding; they are not executable return estimates.",
            "Historical open-price proxies, grid and actual fills/margin remain uncertified.",
            "Source hash/completeness validation is the responsibility of the acquisition runner; declared references alone are not evidence certification.",
        ],
    }
