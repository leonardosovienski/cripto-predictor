"""Current public order-book diagnostics, never orders or historical fill estimates."""

from __future__ import annotations

import argparse
import gzip
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx

from scripts.basis_data import EVIDENCE, protocol, sha, write


def walk(levels: list, quantity: float, ascending: bool) -> float:
    if quantity <= 0 or not math.isfinite(quantity):
        raise ValueError("Invalid quantity")
    prices = [float(x[0]) for x in levels]
    if prices != sorted(prices, reverse=not ascending) or len(set(prices)) != len(prices):
        raise ValueError("Invalid book ordering")
    remaining, total = quantity, 0.0
    for price_raw, size_raw in levels:
        price, size = float(price_raw), float(size_raw)
        if not all(math.isfinite(x) and x > 0 for x in (price, size)):
            raise ValueError("Invalid book level")
        fill = min(remaining, size)
        total += fill * price
        remaining -= fill
        if remaining <= 1e-12:
            return total / quantity
    raise ValueError("Insufficient published depth")


def grid_floor(quantity: float, step: str) -> float:
    return float((Decimal(str(quantity)) // Decimal(step)) * Decimal(step))


def common_grid(a: str, b: str) -> str:
    x, y = Decimal(a), Decimal(b)
    if min(x, y) <= 0:
        raise ValueError("Invalid step")
    scale = 10 ** max(-int(x.as_tuple().exponent), -int(y.as_tuple().exponent), 0)
    return str(Decimal(math.lcm(int(x * scale), int(y * scale))) / Decimal(scale))


def filters(info: dict) -> dict:
    row = next(r for r in info["symbols"] if r["symbol"] == "BTCUSDT")
    f = {v["filterType"]: v for v in row["filters"]}
    lot, market = f["LOT_SIZE"], f.get("MARKET_LOT_SIZE", {})
    step = lot["stepSize"]
    if Decimal(market.get("stepSize", "0")) > 0:
        step = common_grid(step, market["stepSize"])
    notional = f.get("NOTIONAL", f.get("MIN_NOTIONAL", {}))
    return {
        "step": step,
        "min_qty": max(float(lot["minQty"]), float(market.get("minQty", 0))),
        "max_qty": min(float(lot["maxQty"]), float(market.get("maxQty", lot["maxQty"]))),
        "min_notional": float(notional.get("minNotional", notional.get("notional", 0))),
        "status": row["status"],
    }


def estimate(spot: dict, future: dict, sf: dict, ff: dict) -> dict:
    smid = (float(spot["bids"][0][0]) + float(spot["asks"][0][0])) / 2
    fmid = (float(future["bids"][0][0]) + float(future["asks"][0][0])) / 2
    if float(spot["bids"][0][0]) >= float(spot["asks"][0][0]) or float(
        future["bids"][0][0]
    ) >= float(future["asks"][0][0]):
        raise ValueError("Crossed public book")
    q = grid_floor(1250 / smid, common_grid(sf["step"], ff["step"]))
    for f, price in ((sf, smid), (ff, fmid)):
        if (
            f["status"] != "TRADING"
            or not f["min_qty"] <= q <= f["max_qty"]
            or q * price < f["min_notional"]
        ):
            raise ValueError("Current market-lot/minimum constraint")
    sbuy, ssell = walk(spot["asks"], q, True), walk(spot["bids"], q, False)
    fsell, fbuy = walk(future["bids"], q, False), walk(future["asks"], q, True)
    book_cost = q * (sbuy - ssell + fbuy - fsell)
    fees = q * ((sbuy + ssell) * 0.001 + (fsell + fbuy) * 0.0005)
    reserve = 5000 - q * sbuy * 1.001 - q * fsell * 0.0005
    jump = fmid * 1.3
    # Alternative: a spot buy commission deducted in BTC reduces the available hedge quantity.
    gross = grid_floor(1250 / float(spot["asks"][0][0]), sf["step"])
    received = gross * (1 - 0.001)
    short = grid_floor(received, ff["step"])
    dust = max(0.0, received - short)
    return {
        "matched_quantity_btc_assuming_usdt_fees": q,
        "spot_buy_vwap": sbuy,
        "future_sell_vwap": fsell,
        "quoted_entry_basis_fraction": fsell / sbuy - 1,
        "book_only_instant_round_trip_usdt": book_cost,
        "assumed_fees_round_trip_usdt": fees,
        "total_instant_round_trip_bps_spot_notional": (book_cost + fees) / (q * smid) * 10000,
        "cash_reserve_usdt_assuming_usdt_fees": reserve,
        "margin_surplus_after_30pct_mid_jump_usdt": reserve + q * (fsell - jump) - 0.015 * q * jump,
        "spot_fee_in_btc_alternative": {
            "gross_spot_btc": gross,
            "fee_btc_at_assumed_10bps": gross * 0.001,
            "received_btc": received,
            "rounded_future_short_btc": short,
            "unhedged_dust_btc": dust,
            "dust_marked_usdt": dust * smid,
        },
        "actual_account_fees": "UNKNOWN",
        "all_venue_filters_certified": False,
        "simultaneous_execution_certified": False,
    }


def collect(output: Path) -> None:
    protocol()
    output.mkdir(parents=True, exist_ok=False)
    raw_dir = output / "raw"
    raw_dir.mkdir()
    sources = []
    client = httpx.Client(timeout=10, trust_env=False)

    def get(kind: str, name: str, info=False):
        url = (
            "https://api.binance.com/api/v3/"
            if kind == "spot"
            else "https://fapi.binance.com/fapi/v1/"
        ) + ("exchangeInfo" if info else "depth")
        params = {} if info else {"symbol": "BTCUSDT", "limit": 100}
        request = client.build_request("GET", url, params=params)
        start = time.time_ns()
        response = client.send(request)
        finish = time.time_ns()
        raw = response.content
        (raw_dir / (name + ".bin.gz")).write_bytes(gzip.compress(raw, mtime=0))
        meta = {
            "name": name,
            "url": str(request.url),
            "request_start_ns": start,
            "received_ns": finish,
            "status": response.status_code,
            "sha256": sha(raw),
        }
        response.raise_for_status()
        return response.json(), meta

    try:
        sinfo, smeta = get("spot", "spot_info", True)
        finfo, fmeta = get("future", "future_info", True)
        sources.extend([smeta, fmeta])
        sf, ff = filters(sinfo), filters(finfo)
        snapshots = []
        for index in range(12):
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(get, "spot", f"spot_{index:02d}")
                b = pool.submit(get, "future", f"future_{index:02d}")
                spot, sm = a.result()
                future, fm = b.result()
            sources.extend([sm, fm])
            duration = max((m["received_ns"] - m["request_start_ns"]) / 1e9 for m in (sm, fm))
            skew = (
                abs(
                    (sm["received_ns"] + sm["request_start_ns"])
                    - (fm["received_ns"] + fm["request_start_ns"])
                )
                / 2e9
            )
            try:
                values = estimate(spot, future, sf, ff)
                error = None
            except ValueError as exc:
                values, error = None, str(exc)
            snapshots.append(
                {
                    "index": index,
                    "max_request_seconds": duration,
                    "midpoint_skew_seconds": skew,
                    "freshness_pass": duration <= 2 and skew <= 0.5,
                    "estimate": values,
                    "error": error,
                }
            )
            print("Public diagnostic", index + 1, "/ 12", flush=True)
            if index < 11:
                time.sleep(5)
        good = [
            s["estimate"]["total_instant_round_trip_bps_spot_notional"]
            for s in snapshots
            if s["freshness_pass"] and s["estimate"]
        ]
        result = {
            "protocol_sha256": sha((EVIDENCE / "protocol.json").read_bytes()),
            "known_at": datetime.now(UTC).isoformat(),
            "diagnostic_only": True,
            "historical_calibration": False,
            "orders_sent": 0,
            "account_access": False,
            "current_filters": {"spot": sf, "future": ff},
            "snapshots": snapshots,
            "fresh_valid_snapshots": len(good),
            "median_round_trip_bps": statistics.median(good) if good else None,
            "maximum_round_trip_bps": max(good) if good else None,
            "sources": sources,
        }
        write(output / "diagnostic.json", result)
    except Exception as exc:
        write(output / "failure.json", {"error": repr(exc), "sources": sources})
        raise
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    collect(parser.parse_args().output)
