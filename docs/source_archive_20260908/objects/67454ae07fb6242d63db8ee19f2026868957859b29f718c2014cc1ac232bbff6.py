"""A finite public-data diagnostic collector; no account or order capability."""

from __future__ import annotations

import gzip
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scripts.carry_public import PublicSource, durable_raw
from scripts.diagnose_btc_execution import filters
from scripts.plan_btc_hedge_v2 import validate_book, validate_filters
from scripts.plan_btc_hedge_v3 import validate_timing
from scripts.research_io import encoded, integer, sha, strict_json, write_atomic

URLS = {
    "spot_time": "https://api.binance.com/api/v3/time",
    "future_time": "https://fapi.binance.com/fapi/v1/time",
    "okx_time": "https://www.okx.com/api/v5/public/time",
    "spot_info": "https://api.binance.com/api/v3/exchangeInfo",
    "future_info": "https://fapi.binance.com/fapi/v1/exchangeInfo",
    "spot_book": "https://api.binance.com/api/v3/depth",
    "future_book": "https://fapi.binance.com/fapi/v1/depth",
    "okx_book": "https://www.okx.com/api/v5/market/books",
    "spot_daily": "https://api.binance.com/api/v3/klines",
    "future_daily": "https://fapi.binance.com/fapi/v1/klines",
    "mark": "https://fapi.binance.com/fapi/v1/markPriceKlines",
    "funding": "https://fapi.binance.com/fapi/v1/fundingRate",
}


class Source(PublicSource):
    def __init__(self, directory: Path):
        self.directory = directory
        (directory / "raw").mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=10, trust_env=False, follow_redirects=False)
        self.lock = threading.Lock()
        self.requests, self.bytes, self.records = 0, 0, []

    def get(self, name, params=None):
        if name not in URLS or set(params or {}) - {
            "symbol",
            "limit",
            "startTime",
            "endTime",
            "interval",
            "instId",
            "sz",
        }:
            raise ValueError("Unregistered public request")
        if (params or {}).get("symbol", "BTCUSDT") != "BTCUSDT" or (params or {}).get(
            "instId", "BTC-USDT"
        ) != "BTC-USDT":
            raise ValueError("Unregistered instrument")
        with self.lock:
            if self.requests >= 128 or self.bytes >= 80_000_000:
                raise ValueError("Diagnostic request budget exceeded")
            self.requests += 1
        ident = uuid.uuid4().hex
        request = self.client.build_request("GET", URLS[name], params=params)
        start, mono = time.time_ns(), time.monotonic_ns()
        meta = {"id": ident, "name": name, "url": str(request.url), "request_start_ns": start}
        chunks, error = [], None
        try:
            with self.client.stream("GET", URLS[name], params=params) as response:
                meta["status"] = response.status_code
                received_bytes = 0
                for chunk in response.iter_bytes(chunk_size=65536):
                    with self.lock:
                        available = min(80_000_000 - self.bytes, 20_000_000 - received_bytes)
                        accepted = chunk[: max(0, available)]
                        self.bytes += len(accepted)
                    received_bytes += len(accepted)
                    chunks.append(accepted)
                    if len(accepted) < len(chunk):
                        raise ValueError("Diagnostic byte budget exceeded")
                response.raise_for_status()
        except Exception as exc:
            error = exc
        meta.update(received_ns=time.time_ns(), elapsed_ns=time.monotonic_ns() - mono)
        raw = b"".join(chunks)
        meta.update(
            sha256=sha(raw),
            raw_file="raw/" + ident + ".bin.gz",
            error=str(error) if error else None,
        )
        durable_raw(self.directory / meta["raw_file"], gzip.compress(raw, mtime=0))
        durable_raw(self.directory / "raw" / (ident + ".json"), encoded(meta) + b"\n")
        with self.lock:
            self.records.append(meta)
            write_atomic(self.directory / "sources.json", self.records)
        if error:
            raise error
        if abs(meta["received_ns"] - start - meta["elapsed_ns"]) > 100_000_000:
            raise ValueError("Local clock moved during public request")
        return strict_json(raw), meta


def clock_offsets(source):
    offsets, errors = {}, {}
    for venue in ("spot", "future", "okx"):
        try:
            row, meta = source.get(venue + "_time")
            stamp = int(row["data"][0]["ts"]) if venue == "okx" else integer(row["serverTime"], 1)
            offset = stamp - (meta["request_start_ns"] + meta["received_ns"]) / 2_000_000
            if abs(offset) > 5000 or meta["elapsed_ns"] > 2_000_000_000:
                raise ValueError("Invalid public clock freshness")
            offsets[venue] = offset
        except Exception as exc:
            if venue != "okx":
                raise
            errors[venue] = str(exc)
    return offsets, errors


def market_filters(source):
    spot, _ = source.get("spot_info", {"symbol": "BTCUSDT"})
    future, _ = source.get("future_info")
    selected = []
    for info in (spot, future):
        rows = [r for r in info["symbols"] if r["symbol"] == "BTCUSDT"]
        if len(rows) != 1:
            raise ValueError("Ambiguous venue symbol")
        selected.append(rows[0])
    sf, ff = filters(spot), filters(future)
    validate_filters(sf)
    validate_filters(ff)
    return sf, ff, integer(selected[0]["baseCommissionPrecision"])


def snapshot(source, offsets, constraints):
    results, errors = {}, {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = {
            name: pool.submit(
                source.get,
                name,
                {"instId": "BTC-USDT", "sz": 100}
                if name == "okx_book"
                else {"symbol": "BTCUSDT", "limit": 100},
            )
            for name in ("spot_book", "future_book", "okx_book")
        }
        for name, task in tasks.items():
            try:
                results[name] = task.result()
            except Exception as exc:
                errors[name] = str(exc)
    for name in ("spot_book", "future_book"):
        if name not in results:
            raise ValueError("Paired Binance quote failed: " + str(errors))
    s, sm = results["spot_book"]
    f, fm = results["future_book"]
    validate_timing(sm, fm)
    validate_book(s)
    validate_book(f)
    age = fm["received_ns"] / 1e6 + offsets["future"] - integer(f["E"], 1)
    if not -1000 <= age <= 5000:
        raise ValueError("Stale Binance event")
    cross = {
        "status": "UNKNOWN",
        "error": errors.get("okx_book"),
        "same_exchange_funding_verified": False,
    }
    if "okx_book" in results:
        try:
            o, om = results["okx_book"]
            if o["code"] != "0" or len(o["data"]) != 1 or "okx" not in offsets:
                raise ValueError("OKX public response/clock unavailable")
            item = o["data"][0]
            book = {side: [r[:2] for r in item[side]] for side in ("bids", "asks")}
            validate_book(book)
            validate_timing(sm, om)
            age = om["received_ns"] / 1e6 + offsets["okx"] - int(item["ts"])
            if not -1000 <= age <= 5000:
                raise ValueError("Stale OKX event")
            bmid = sum(float(s[x][0][0]) for x in ("bids", "asks")) / 2
            omid = sum(float(book[x][0][0]) for x in ("bids", "asks")) / 2
            difference = (omid / bmid - 1) * 10000
            cross = {
                "status": "FLAG" if abs(difference) > 50 else "CONSISTENT_WITHIN_50BPS",
                "difference_bps": difference,
                "book": book,
                "same_exchange_funding_verified": False,
            }
        except Exception as exc:
            cross["error"] = str(exc)
    sf, ff, precision = constraints
    return {
        "spot": s,
        "future": f,
        "sf": sf,
        "ff": ff,
        "base_commission_precision": precision,
        "quote_ns": max(sm["received_ns"], fm["received_ns"]),
        "cross_source": cross,
        "sources": [m for _, m in results.values()],
        "actual_fills_certified": False,
    }


def collect_history(source, start, end):
    daily = {}
    for name in ("spot_daily", "future_daily"):
        rows, _ = source.get(
            name,
            {
                "symbol": "BTCUSDT",
                "interval": "1d",
                "startTime": start,
                "endTime": end,
                "limit": 1000,
            },
        )
        daily[name] = rows
    funding, cursor = [], start + 3_600_000
    while cursor < end:
        rows, _ = source.get(
            "funding", {"symbol": "BTCUSDT", "startTime": cursor, "endTime": end - 1, "limit": 1000}
        )
        if not isinstance(rows, list):
            raise ValueError("Invalid funding list")
        funding.extend(rows)
        if len(rows) < 1000:
            break
        following = integer(rows[-1]["fundingTime"], 1) + 1
        if following <= cursor:
            raise ValueError("Nonadvancing funding page")
        cursor = following
    marks, cursor = [], start
    while cursor < end:
        rows, _ = source.get(
            "mark",
            {
                "symbol": "BTCUSDT",
                "interval": "1h",
                "startTime": cursor,
                "endTime": end - 1,
                "limit": 1000,
            },
        )
        if not isinstance(rows, list) or not rows or rows[0][0] != cursor:
            raise ValueError("Missing mark page")
        marks.extend(rows)
        following = integer(rows[-1][0], 1) + 3_600_000
        if following <= cursor:
            raise ValueError("Nonadvancing mark page")
        cursor = following
    return daily["spot_daily"], daily["future_daily"], funding, marks


def utc():
    return datetime.now(UTC).isoformat()
