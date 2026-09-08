"""Daily public BTC shadow observation. Durable decisions; no orders or account access."""

from __future__ import annotations

import argparse
import importlib.metadata
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.carry_forward_math import opening, valuation
from scripts.carry_public import PublicSource, capture, history, utc_now, verify_sources
from scripts.plan_btc_hedge_v3 import net_hedge_plan
from scripts.research_io import Ledger, encoded, exclusive, sha, strict_json, write_atomic

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/carry_forward_20260908"


def verify(evidence=EVIDENCE, root=ROOT):
    raw = (evidence / "code_freeze.json").read_bytes()
    freeze = strict_json(raw)
    for name, digest in freeze["files"].items():
        if sha((root / name).read_bytes()) != digest:
            raise ValueError("Frozen carry observer file changed: " + name)
    if (
        list(sys.version_info[:3]) != freeze["python"]
        or importlib.metadata.version("httpx") != freeze["httpx"]
    ):
        raise ValueError("Unverified observer runtime")
    return strict_json((evidence / "protocol.json").read_bytes()), sha(raw)


def bounds(protocol):
    return datetime.fromisoformat(protocol["start"]), datetime.fromisoformat(protocol["end"])


def action(ledger, protocol, instant):
    start, end = bounds(protocol)
    width = timedelta(minutes=protocol["window_minutes"])
    for failure in ("MISSED_ENTRY", "MISSED_EXIT"):
        if ledger.find(failure, "position"):
            return failure, "position"
    if instant < start:
        return "WAITING", start.date().isoformat()
    entry = ledger.find("ENTRY", "position")
    if entry is None:
        if ledger.find("DECISION", "position"):
            return "ENTRY_INTERRUPTED", "position"
        if instant >= start + width:
            return "MISSED_ENTRY", "position"
        return "OPEN", "position"
    if ledger.find("EXIT", "position"):
        return "COMPLETED", "position"
    if ledger.find("CLOSE_DECISION", "position"):
        return "EXIT_INTERRUPTED", "position"
    if instant >= end + width:
        return "MISSED_EXIT", "position"
    if instant >= end:
        return "CLOSE", "position"
    slot = instant.date().isoformat()
    anchor = datetime.combine(instant.date(), datetime.min.time(), tzinfo=UTC)
    if (
        slot
        == datetime.fromtimestamp(entry["payload"]["entry"]["entry_ms"] / 1000, UTC)
        .date()
        .isoformat()
    ):
        return "ACTIVE", slot
    if instant >= anchor + width or ledger.find("ATTEMPT", slot):
        return "ACTIVE", slot
    return "SAMPLE", slot


def status(ledger, protocol, instant, error=None):
    phase, _ = action(ledger, protocol, instant)
    start, end = bounds(protocol)
    entry, exit_row = ledger.find("ENTRY", "position"), ledger.find("EXIT", "position")
    values = [r for r in ledger.rows if r["kind"] in {"VALUE", "EXIT"}]
    known = {
        datetime.fromtimestamp(r["payload"]["value"]["quote_ms"] / 1000, UTC).date().isoformat()
        for r in values
    }
    if entry:
        known.add(
            datetime.fromtimestamp(entry["payload"]["entry"]["entry_ms"] / 1000, UTC)
            .date()
            .isoformat()
        )
    expected, anchor = [], start
    while anchor <= end and anchor + timedelta(minutes=protocol["window_minutes"]) <= instant:
        expected.append(anchor.date().isoformat())
        anchor += timedelta(days=1)
    missing = sorted(set(expected) - known)
    latest = values[-1]["payload"]["value"] if values else None
    if error is None:
        for row in reversed(ledger.rows):
            if row["kind"] == "ERROR":
                error = row["payload"]["error"]
                break
            if row["kind"] in {"PREFLIGHT", "ENTRY", "VALUE", "EXIT"}:
                break
    breached = any(
        c["margin_breaches"] for r in values for c in r["payload"]["value"]["cases"].values()
    )
    drawdown = {}
    for name in protocol["costs"]:
        peak, worst = float(protocol["capital_usdt"]), 0.0
        for r in values:
            equity = protocol["capital_usdt"] + float(
                r["payload"]["value"]["cases"][name]["modeled_liquidation_profit_usdt"]
            )
            peak = max(peak, equity)
            worst = min(worst, equity / peak - 1)
        drawdown[name] = worst if values else None
    terminal = phase in {
        "COMPLETED",
        "MISSED_ENTRY",
        "MISSED_EXIT",
        "ENTRY_INTERRUPTED",
        "EXIT_INTERRUPTED",
    }
    result = {
        "protocol_id": protocol["id"],
        "updated_utc": instant.isoformat(),
        "phase": phase,
        "entry_observed": entry is not None,
        "exit_observed": exit_row is not None,
        "known_quote_slots": sorted(known),
        "due_quote_slots": expected,
        "missing_quote_slots": missing,
        "latest_value": latest,
        "final_value": exit_row["payload"]["value"] if exit_row else None,
        "sampled_quote_drawdown_fraction": drawdown,
        "observed_margin_breach": breached,
        "observation_finished": terminal,
        "error": error,
        "ledger_rows": len(ledger.rows),
        "ledger_head": ledger.rows[-1]["sha256"] if ledger.rows else None,
        "real_profit_usdt": None,
        "validated_expected_profit_usdt": None,
        "independent_profit_confirmation": False,
        "orders_sent": 0,
        "meaning": "One fixed prospective shadow holding; missing observations are not zero and quotes are not fills.",
    }
    result["notification_signature"] = sha(
        encoded(
            {
                "phase": phase if terminal or phase == "WAITING" else "ACTIVE",
                "entry": bool(entry),
                "exit": bool(exit_row),
                "missing": missing,
                "breach": breached,
                "error": error,
            }
        )
    )
    return result


def run(directory, protocol, freeze_hash, source, mode="tick", clock=utc_now):
    with exclusive(directory):
        ledger = Ledger(directory / "ledger.jsonl")
        if any(r["payload"].get("freeze_sha256") != freeze_hash for r in ledger.rows):
            raise ValueError("Ledger belongs to a different observer freeze")
        for row in ledger.rows:
            payload = row["payload"]
            verify_sources(
                directory, payload.get("sources", payload.get("snapshot", {}).get("sources", []))
            )
        if any(datetime.fromisoformat(r["known_at"]) > clock() for r in ledger.rows):
            raise ValueError("Local clock moved behind the durable ledger")
        if mode == "status":
            return status(ledger, protocol, clock())
        phase, slot = action(ledger, protocol, clock())
        try:
            if mode == "preflight":
                phase, slot = "PREFLIGHT", clock().isoformat()
                snap = capture(source)
                plan = net_hedge_plan(
                    snap["spot"],
                    snap["future"],
                    snap["sf"],
                    snap["ff"],
                    snap["base_commission_precision"],
                )
                ledger.append(
                    "PREFLIGHT",
                    slot,
                    {
                        "freeze_sha256": freeze_hash,
                        "prospective": False,
                        "snapshot": snap,
                        "plan": plan,
                    },
                    clock().isoformat(),
                )
            elif phase in {"MISSED_ENTRY", "MISSED_EXIT"}:
                if ledger.find(phase, "position") is None:
                    ledger.append(
                        phase,
                        "position",
                        {
                            "freeze_sha256": freeze_hash,
                            "reason": "Observation window passed without a durable quote",
                        },
                        clock().isoformat(),
                    )
            elif phase in {"OPEN", "CLOSE", "SAMPLE"}:
                kind = {"OPEN": "DECISION", "CLOSE": "CLOSE_DECISION", "SAMPLE": "ATTEMPT"}[phase]
                decision = ledger.append(
                    kind,
                    slot,
                    {"freeze_sha256": freeze_hash, "protocol_id": protocol["id"], "action": phase},
                    clock().isoformat(),
                )
                snap = capture(source)
                quote_time = datetime.fromtimestamp(snap["quote_ns"] / 1_000_000_000, UTC)
                start, end = bounds(protocol)
                anchor = (
                    start
                    if phase == "OPEN"
                    else end
                    if phase == "CLOSE"
                    else datetime.combine(clock().date(), datetime.min.time(), tzinfo=UTC)
                )
                if not anchor <= quote_time < anchor + timedelta(
                    minutes=protocol["window_minutes"]
                ) or quote_time < datetime.fromisoformat(decision["known_at"]):
                    raise ValueError("Quote outside decision window; never backdate")
                if phase == "OPEN":
                    position = opening(snap, protocol)
                    ledger.append(
                        "ENTRY",
                        "position",
                        {
                            "freeze_sha256": freeze_hash,
                            "entry": position,
                            "snapshot": snap,
                            "decision_sha256": decision["sha256"],
                        },
                        clock().isoformat(),
                    )
                else:
                    entry_row = ledger.find("ENTRY", "position")
                    if entry_row is None:
                        raise ValueError("Valuation without a durable entry")
                    position = entry_row["payload"]["entry"]
                    funding, marks = history(
                        source, position["entry_ms"], snap["quote_ns"] // 1_000_000
                    )
                    result = valuation(position, snap, funding, marks, protocol)
                    ledger.append(
                        "EXIT" if phase == "CLOSE" else "VALUE",
                        "position" if phase == "CLOSE" else slot,
                        {
                            "freeze_sha256": freeze_hash,
                            "value": result,
                            "snapshot": snap,
                            "sources": list(source.records),
                            "decision_sha256": decision["sha256"],
                        },
                        clock().isoformat(),
                    )
            current = status(ledger, protocol, clock())
            write_atomic(directory / "status.json", current)
            return current
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            error_slot = f"{phase}:{slot}"
            if ledger.find("ERROR", error_slot) is None:
                ledger.append(
                    "ERROR",
                    error_slot,
                    {"freeze_sha256": freeze_hash, "error": message},
                    clock().isoformat(),
                )
            write_atomic(directory / "status.json", status(ledger, protocol, clock(), message))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--mode", choices=("tick", "preflight", "status"), default="tick")
    args = parser.parse_args()
    source = None
    try:
        protocol, freeze_hash = verify()
        source = PublicSource(args.data)
        result = run(args.data, protocol, freeze_hash, source, args.mode)
        write_atomic(
            args.data / "last_run.json",
            {"ok": True, "known_at": utc_now().isoformat(), "phase": result["phase"]},
        )
        print(encoded(result).decode("utf-8"))
    except Exception as exc:
        try:
            write_atomic(
                args.data / "last_run.json",
                {
                    "ok": False,
                    "known_at": utc_now().isoformat(),
                    "error": f"{type(exc).__name__}: {exc}",
                    "status_may_be_stale": True,
                },
            )
        except OSError:
            pass
        parser.exit(1, f"CARRY OBSERVER FAILED: {type(exc).__name__}: {exc}\n")
    finally:
        if source:
            source.close()


if __name__ == "__main__":
    main()
