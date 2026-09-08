"""Offline, multi-strategy economic screening. Never authorizes or sends orders.

Public yield collection is explicit and read-only. Historical/frozen engines are
not imported or modified. All monetary inputs share one declared quote currency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SOURCE = "https://yields.llama.fi/pools"
COST_NAMES = ("execution", "financing", "infrastructure", "tax", "conversion", "other")
EVIDENCE_KINDS = {"SCENARIO", "ADAPTIVE_BACKTEST", "PROSPECTIVE_PAPER"}
LIMIT_BYTES = 20 * 1024 * 1024


def number(value: Any) -> Decimal:
    """Reject booleans, non-finite numbers and implicit missing-as-zero inputs."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("Expected an explicit finite number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid number") from exc
    if not result.is_finite():
        raise ValueError("Non-finite number")
    return result


def nonnegative(value: Any) -> Decimal:
    result = number(value)
    if result < 0:
        raise ValueError("Expected a nonnegative number")
    return result


def text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty text")
    return value.strip()


def instant(value: Any) -> datetime:
    result = datetime.fromisoformat(text(value).replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return result.astimezone(UTC)


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def loads(raw: str) -> Any:
    def invalid(value: str) -> Any:
        raise ValueError("Invalid JSON constant: " + value)

    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid)


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def assess(case: dict[str, Any]) -> dict[str, Any]:
    """Accounting feasibility only; declared evidence is not independently verified."""
    identity = {k: text(case[k]) for k in ("id", "family", "asset", "venue", "currency")}
    evidence = text(case["evidence_kind"])
    if evidence not in EVIDENCE_KINDS:
        raise ValueError("Unsupported evidence kind; real-profit certification is not supported")
    source = text(case["evidence_ref"])
    scenario = text(case["scenario"])
    start, end = instant(case["period_start"]), instant(case["period_end"])
    if end <= start:
        raise ValueError("Invalid comparison period")
    capital = number(case["capital"])
    if capital <= 0:
        raise ValueError("Capital must be positive and include collateral/idle reserves")
    flows, costs = _mapping(case["cashflows"]), _mapping(case["costs"])
    if not flows or set(costs) != set(COST_NAMES):
        raise ValueError("Cashflows and all six cost categories must be explicit")
    notes = _mapping(case["cost_notes"])
    for name in COST_NAMES:
        text(notes[name])  # A zero requires a rationale, not an implicit default.
    missing_flows = [name for name, value in flows.items() if value is None]
    missing_costs = [name for name, value in costs.items() if value is None]
    known_flows = [number(v) for v in flows.values() if v is not None]
    gross = None if missing_flows else sum(known_flows, Decimal(0))
    known_costs = sum((nonnegative(v) for v in costs.values() if v is not None), Decimal(0))
    ceiling = None if gross is None else gross - known_costs
    net = ceiling if not missing_costs else None
    risk_limit = nonnegative(case["risk_limit"])
    if risk_limit > capital:
        raise ValueError("Risk limit cannot exceed the declared simulation capital")
    stress_loss = None if case["stress_loss"] is None else nonnegative(case["stress_loss"])
    blockers = ["UNKNOWN_CASHFLOW:" + n for n in missing_flows]
    blockers += ["UNKNOWN_COST:" + n for n in missing_costs]
    if stress_loss is None:
        blockers.append("UNKNOWN_STRESS_LOSS")
    elif stress_loss > risk_limit:
        blockers.append("STRESS_LOSS_EXCEEDS_BUDGET")
    if not isinstance(case.get("risk_evidence"), str) or not case["risk_evidence"].strip():
        blockers.append("MISSING_RISK_EVIDENCE")
    if (
        not isinstance(case.get("execution_evidence"), str)
        or not case["execution_evidence"].strip()
    ):
        blockers.append("MISSING_EXECUTION_EVIDENCE")
    if net is not None and net <= 0:
        blockers.append("NON_POSITIVE_NET")
    other_costs = [costs[n] for n in COST_NAMES if n != "execution"]
    execution_budget = (
        gross - sum((nonnegative(v) for v in other_costs), Decimal(0))
        if gross is not None and all(v is not None for v in other_costs)
        else None
    )
    return {
        **identity,
        "scenario": scenario,
        "evidence_kind": evidence,
        "evidence_ref": source,
        "evidence_independently_verified": False,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "capital": str(capital),
        "gross": None if gross is None else str(gross),
        "known_costs": str(known_costs),
        "known_net_ceiling_not_profit": None if ceiling is None else str(ceiling),
        "net": None if net is None else str(net),
        "return_pct": None if net is None else str(100 * net / capital),
        "break_even_execution_budget": None if execution_budget is None else str(execution_budget),
        "cost_reduction_to_break_even": None if net is None else str(max(-net, Decimal(0))),
        "economics_status": "INCOMPLETE"
        if net is None
        else "POSITIVE_MODELLED"
        if net > 0
        else "NON_POSITIVE",
        "research_status": "BLOCKED" if blockers else "CANDIDATE_FOR_VALIDATION",
        "blockers": blockers,
        "capital_permission": False,
        "assumptions": {"cashflows": flows, "costs": costs, "cost_notes": notes},
    }


def compare(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Never rank incomparable periods/capital/currencies or sum alternative accounts."""
    if not isinstance(cases, list) or not cases:
        raise ValueError("Expected a nonempty list of cases")
    rows = [assess(_mapping(case)) for case in cases]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate opportunity id")
    groups = {
        (
            r["currency"],
            number(r["capital"]),
            r["period_start"],
            r["period_end"],
            r["scenario"],
            r["evidence_kind"],
        )
        for r in rows
    }
    if len(groups) != 1:
        raise ValueError(
            "Compare only identical capital, currency, period, scenario and evidence kind"
        )
    ranked = sorted(
        (r for r in rows if r["research_status"] == "CANDIDATE_FOR_VALIDATION"),
        key=lambda r: (-number(r["net"]), r["id"]),
    )
    return {
        "schema_version": 1,
        "purpose": "RESEARCH_ONLY_NOT_A_PORTFOLIO_OR_PROFIT_FORECAST",
        "capital_permission": False,
        "ranking": [r["id"] for r in ranked],
        "blocker_counts": dict(Counter(reason for r in rows for reason in r["blockers"])),
        "cases": rows,
    }


def transition(spec: dict[str, Any]) -> dict[str, Any]:
    """Same-instrument turnover arithmetic, not a replay or an executable order.

    Signed quantities use one venue/contract/settlement identity. Price and bps
    are declared scenario assumptions. Real rounding/min-notional/margin/fills
    need validation separately. Do not net spot against perp or different venues.
    """
    if text(spec["current_instrument"]) != text(spec["target_instrument"]):
        raise ValueError("Cannot net different instruments or venues")
    before, target = number(spec["current_quantity"]), number(spec["target_quantity"])
    price, step = number(spec["price"]), number(spec["quantity_step"])
    bps = nonnegative(spec["cost_bps"])
    if price <= 0 or step <= 0 or before % step or target % step:
        raise ValueError("Invalid price or quantities off the declared grid")
    gross, delta = abs(before) + abs(target), abs(target - before)
    baseline, adjusted = gross * price * bps / 10000, delta * price * bps / 10000
    return {
        "purpose": "HYPOTHETICAL_TURNOVER_ONLY_NOT_HISTORICAL_PROFIT",
        "capital_permission": False,
        "signed_quantity_delta": str(target - before),
        "close_reopen_quantity": str(gross),
        "adjust_only_quantity": str(delta),
        "close_reopen_cost": str(baseline),
        "adjust_only_cost": str(adjusted),
        "modelled_cost_difference": str(baseline - adjusted),
        "action": "HOLD" if delta == 0 else "REVIEW_DELTA",
    }


def yield_return(rate_pct: Any, days: Any, convention: str) -> Decimal:
    """Constant-rate *scenario*, not a forecast from the displayed snapshot APY."""
    rate, horizon = number(rate_pct) / 100, number(days)
    if horizon <= 0 or convention not in {"APR", "APY"}:
        raise ValueError("Positive horizon and explicit APR/APY convention required")
    if convention == "APR":
        return rate * horizon / 365
    if rate <= -1:
        raise ValueError("APY must exceed -100 percent")
    return (1 + rate) ** (horizon / 365) - 1


def discover_yields(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Keep all assets. Separate base/reward yields; missing base is never total APY."""
    if snapshot["source"] != SOURCE:
        raise ValueError("Unexpected public source")
    retrieved = instant(snapshot["retrieved_at"])
    raw = snapshot["raw_json"]
    if not isinstance(raw, str) or hashlib.sha256(raw.encode()).hexdigest() != snapshot["sha256"]:
        raise ValueError("Snapshot hash mismatch")
    body = _mapping(loads(raw))
    if body.get("status") != "success" or not isinstance(body.get("data"), list):
        raise ValueError("Invalid provider payload; do not interpret failure as no opportunities")
    candidates, rejected = [], []
    counts: Counter[tuple[str, ...]] = Counter()
    for item in body["data"]:
        try:
            row = _mapping(item)
            counts[tuple(text(row[k]) for k in ("chain", "project", "pool"))] += 1
        except (KeyError, ValueError, TypeError):
            pass  # The reporting pass below records every invalid row.
    for index, item in enumerate(body["data"]):
        try:
            row = _mapping(item)
            identity = {k: text(row[k]) for k in ("pool", "chain", "project", "symbol")}
            key = (identity["chain"], identity["project"], identity["pool"])
            if counts[key] > 1:
                raise ValueError("Duplicate pool identity")
            tvl = nonnegative(row["tvlUsd"])
            rates = {
                k: None if row.get(k) is None else str(number(row[k]))
                for k in ("apyBase", "apyReward")
            }
        except (KeyError, ValueError, TypeError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
            continue
        candidates.append(
            {
                **identity,
                **rates,
                "tvlUsd": str(tvl),
                "status": "DISCOVERY_ONLY",
                "capital_permission": False,
                "source_timestamp": None,
                "needs": ["SOURCE_FRESHNESS", "YIELD_CONVENTION", "COSTS", "EXIT_LIQUIDITY", "RISK"]
                + (["BASE_YIELD"] if rates["apyBase"] is None else [])
                + (["REWARD_YIELD"] if rates["apyReward"] is None else []),
            }
        )
    return {
        "schema_version": 1,
        "retrieved_at": retrieved.isoformat(),
        "source": SOURCE,
        "sha256": snapshot["sha256"],
        "source_freshness_verified": False,
        "capital_permission": False,
        "candidates": candidates,
        "rejected": rejected,
        "input_count": len(body["data"]),
    }


def capture_yields(destination: Path) -> None:
    """One unauthenticated GET; exclusive-create snapshot, no scheduling or trades."""
    import httpx

    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing snapshot")
    try:
        with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
            with client.stream("GET", SOURCE, headers={"Accept": "application/json"}) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > LIMIT_BYTES:
                        raise ValueError("Provider payload exceeds the snapshot limit")
    except httpx.HTTPError as exc:
        raise ValueError(f"Public data request failed ({type(exc).__name__})") from exc
    snapshot = {
        "source": SOURCE,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "raw_json": raw.decode("utf-8"),
    }
    discover_yields(snapshot)  # Validate before publishing, never overwrite evidence.
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("evaluate", "transition", "discover-yields", "capture-yields")
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture-yields":
            capture_yields(args.path)
            print(json.dumps({"snapshot": str(args.path), "capital_permission": False}))
            return 0
        if args.path.stat().st_size > LIMIT_BYTES * 2:
            raise ValueError("Input exceeds size limit")
        raw = args.path.read_bytes()
        payload = loads(raw.decode("utf-8"))
        if args.command == "evaluate":
            result = compare(payload)
        elif args.command == "transition":
            result = transition(_mapping(payload))
        else:
            result = discover_yields(_mapping(payload))
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0  # Well-formed blocked cases are reports, not parsing failures.
    except (ValueError, KeyError, TypeError, ArithmeticError, OSError) as exc:
        print(json.dumps({"error": str(exc), "capital_permission": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
