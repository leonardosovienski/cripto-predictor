"""Supported strict saved-quote planner; earlier versions remain frozen artifacts."""

from __future__ import annotations

import argparse
import gzip
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from scripts.diagnose_btc_execution import filters
from scripts.plan_btc_hedge_v2 import net_hedge_plan as previous_plan
from scripts.plan_btc_hedge_v2 import number, validate_book, validate_filters
from scripts.research_io import encoded, integer, sha, strict_json


def validate_timing(sm: dict, fm: dict) -> None:
    for meta in (sm, fm):
        if not isinstance(meta, dict) or meta.get("status") != 200:
            raise ValueError("Failed quote source")
        start, end = integer(meta.get("request_start_ns"), 1), integer(meta.get("received_ns"), 1)
        if not 0 <= end - start <= 2_000_000_000:
            raise ValueError("Invalid or stale quote timing")
    if (
        abs(sm["received_ns"] + sm["request_start_ns"] - fm["received_ns"] - fm["request_start_ns"])
        > 1_000_000_000
    ):
        raise ValueError("Asynchronous books")


def net_hedge_plan(spot, future, sf, ff, precision):
    if not all(isinstance(x, dict) for x in (spot, future, sf, ff)):
        raise ValueError("Books and filters must be objects")
    for book in (spot, future):
        validate_book(book)
    for constraints in (sf, ff):
        validate_filters(constraints)
    integer(precision)
    if precision > 18:
        raise ValueError("Invalid commission precision")
    return previous_plan(spot, future, sf, ff, precision)


def walk_decimal(levels: list, quantity: Decimal) -> Decimal:
    if not quantity.is_finite() or quantity <= 0:
        raise ValueError("Invalid requested quantity")
    remaining, value = quantity, Decimal(0)
    for price, size in levels:
        taken = min(remaining, number(size))
        value += taken * number(price)
        remaining -= taken
        if remaining == 0:
            return value / quantity
    raise ValueError("Insufficient published depth")


def saved_sources(directory: Path):
    record = strict_json((directory / "diagnostic.json").read_bytes())
    sources, metadata = {}, {}
    raw_root = (directory / "raw").resolve()
    for meta in record["sources"]:
        name = meta.get("name")
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"(spot|future)_(info|\d{2})", name)
            or name in sources
        ):
            raise ValueError("Invalid or duplicate source identity")
        u = urlsplit(meta["url"])
        venue = name.split("_")[0]
        endpoint = "exchangeInfo" if name.endswith("info") else "depth"
        host, prefix = (
            ("api.binance.com", "/api/v3/")
            if venue == "spot"
            else ("fapi.binance.com", "/fapi/v1/")
        )
        if u.scheme != "https" or u.netloc != host or u.path != prefix + endpoint or u.fragment:
            raise ValueError("Source URL identity mismatch")
        if endpoint == "depth" and parse_qs(u.query).get("symbol") != ["BTCUSDT"]:
            raise ValueError("Unexpected quote symbol")
        path = (raw_root / (name + ".bin.gz")).resolve()
        if not path.is_relative_to(raw_root):
            raise ValueError("Source outside raw directory")
        raw = gzip.decompress(path.read_bytes())
        if sha(raw) != meta["sha256"] or meta["status"] != 200:
            raise ValueError("Changed or failed source")
        sources[name], metadata[name] = strict_json(raw), meta
    indices = [integer(s["index"]) for s in record["snapshots"]]
    if not indices or len(indices) != len(set(indices)) or any(i > 99 for i in indices):
        raise ValueError("Invalid sample identities")
    required = {"spot_info", "future_info"} | {
        f"{v}_{i:02d}" for i in indices for v in ("spot", "future")
    }
    if set(sources) != required:
        raise ValueError("Missing or unrelated saved sources")
    return record, sources, metadata


def replay(directory: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Preserve existing output")
    record, sources, metadata = saved_sources(directory)
    for venue in ("spot", "future"):
        if len([s for s in sources[venue + "_info"]["symbols"] if s["symbol"] == "BTCUSDT"]) != 1:
            raise ValueError("Ambiguous BTC venue symbol")
    sf, ff = filters(sources["spot_info"]), filters(sources["future_info"])
    symbols = [s for s in sources["spot_info"]["symbols"] if s["symbol"] == "BTCUSDT"]
    if len(symbols) != 1:
        raise ValueError("Ambiguous BTC spot symbol")
    precision = integer(symbols[0]["baseCommissionPrecision"])
    rows = []
    for sample in record["snapshots"]:
        i = sample["index"]
        try:
            if sample.get("error") or sample.get("freshness_pass") is not True:
                raise ValueError("Previously invalid sample")
            s, f = f"spot_{i:02d}", f"future_{i:02d}"
            validate_timing(metadata[s], metadata[f])
            plan = net_hedge_plan(sources[s], sources[f], sf, ff, precision)
            error = None
        except ValueError as exc:
            plan, error = None, str(exc)
        rows.append({"snapshot_index": i, "plan": plan, "error": error})
    result = {
        "version": 3,
        "status": "PASS" if all(p["plan"] for p in rows) else "REJECTED",
        "plans": rows,
        "new_network_requests": 0,
        "orders_sent": 0,
        "actual_fills_certified": False,
        "source_code_sha256": sha(Path(__file__).read_bytes()),
        "diagnostic_sha256": sha((directory / "diagnostic.json").read_bytes()),
    }
    with output.open("xb") as stream:
        stream.write(encoded(result) + b"\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = replay(args.diagnostic, args.output)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f"REJECTED: {exc}\n")
    print(result["status"])
    raise SystemExit(0 if result["status"] == "PASS" else 1)
