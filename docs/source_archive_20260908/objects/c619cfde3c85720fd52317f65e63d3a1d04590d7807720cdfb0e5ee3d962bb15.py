"""Validated saved-quote diagnostic; v1 arithmetic remains frozen for reproduction."""

from __future__ import annotations

import argparse
import gzip
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from scripts.basis_data import sha, write
from scripts.diagnose_btc_execution import filters
from scripts.plan_btc_hedge import net_hedge_plan as frozen_plan


def number(value) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid quote or constraint number") from exc
    if not result.is_finite():
        raise ValueError("Nonfinite quote or constraint")
    return result


def validate_book(book: dict) -> None:
    tops = {}
    for side in ("bids", "asks"):
        levels = book.get(side)
        if not isinstance(levels, list) or not levels:
            raise ValueError("Missing book side")
        previous = None
        for row in levels:
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                raise ValueError("Invalid book level shape")
            price, size = map(number, row)
            if min(price, size) <= 0:
                raise ValueError("Nonpositive book price or size")
            if previous is not None and (
                (side == "bids" and price >= previous) or (side == "asks" and price <= previous)
            ):
                raise ValueError("Unordered or duplicate book levels")
            previous = price
        tops[side] = number(levels[0][0])
    if tops["bids"] >= tops["asks"]:
        raise ValueError("Crossed or locked book")


def validate_filters(value: dict) -> None:
    try:
        step, minimum, maximum, notional = (
            number(value[k]) for k in ("step", "min_qty", "max_qty", "min_notional")
        )
    except KeyError as exc:
        raise ValueError("Missing lot constraint") from exc
    if step <= 0 or minimum < 0 or maximum <= 0 or maximum < minimum or notional < 0:
        raise ValueError("Invalid lot constraint")
    if value.get("status") != "TRADING":
        raise ValueError("Market unavailable")


def net_hedge_plan(spot: dict, future: dict, sf: dict, ff: dict, precision: int) -> dict:
    for book in (spot, future):
        validate_book(book)
    for constraints in (sf, ff):
        validate_filters(constraints)
    if type(precision) is not int or not 0 <= precision <= 18:
        raise ValueError("Invalid commission precision")
    return frozen_plan(spot, future, sf, ff, precision)


def validate_sample(sample: dict, sm: dict, fm: dict) -> None:
    if sample.get("error") or sample.get("freshness_pass") is not True:
        raise ValueError("Previously invalid or stale diagnostic sample")
    for meta in (sm, fm):
        if meta["status"] != 200 or meta["received_ns"] < meta["request_start_ns"]:
            raise ValueError("Invalid source response or request timing")
        if meta["received_ns"] - meta["request_start_ns"] > 2_000_000_000:
            raise ValueError("Stale diagnostic response")
    if (
        abs(sm["received_ns"] + sm["request_start_ns"] - fm["received_ns"] - fm["request_start_ns"])
        > 1_000_000_000
    ):
        raise ValueError("Asynchronous diagnostic books")


def replay(directory: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Preserve existing output")
    record_path = directory / "diagnostic.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    sources, metadata = {}, {}
    for meta in record["sources"]:
        raw = gzip.decompress((directory / "raw" / (meta["name"] + ".bin.gz")).read_bytes())
        if sha(raw) != meta["sha256"] or meta["status"] != 200:
            raise ValueError("Changed or failed saved public source")
        sources[meta["name"]] = json.loads(raw)
        metadata[meta["name"]] = meta
    sf, ff = filters(sources["spot_info"]), filters(sources["future_info"])
    symbol = next(s for s in sources["spot_info"]["symbols"] if s["symbol"] == "BTCUSDT")
    precision = int(symbol["baseCommissionPrecision"])
    rows = []
    for sample in record["snapshots"]:
        index = sample["index"]
        s, f = f"spot_{index:02d}", f"future_{index:02d}"
        try:
            validate_sample(sample, metadata[s], metadata[f])
            plan = net_hedge_plan(sources[s], sources[f], sf, ff, precision)
            error = None
        except ValueError as exc:
            plan, error = None, str(exc)
        rows.append({"snapshot_index": index, "plan": plan, "error": error})
    result = {
        "version": 2,
        "source_code_sha256": sha(Path(__file__).read_bytes()),
        "diagnostic_source_sha256": sha(record_path.read_bytes()),
        "historical_strategies_changed": False,
        "new_network_requests": 0,
        "orders_sent": 0,
        "plans": rows,
    }
    write(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.diagnostic, args.output)
    print(json.dumps({"valid_plans": sum(p["plan"] is not None for p in result["plans"])}))
