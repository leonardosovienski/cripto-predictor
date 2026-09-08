"""Bounded public BTC data capture. No credentials, orders, redirects or retries."""

from __future__ import annotations

import gzip
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from scripts.diagnose_btc_execution import filters
from scripts.plan_btc_hedge_v2 import validate_book, validate_filters
from scripts.plan_btc_hedge_v3 import validate_timing
from scripts.research_io import encoded, integer, sha, strict_json

URLS = {
    "spot_time": "https://api.binance.com/api/v3/time",
    "future_time": "https://fapi.binance.com/fapi/v1/time",
    "spot_info": "https://api.binance.com/api/v3/exchangeInfo",
    "future_info": "https://fapi.binance.com/fapi/v1/exchangeInfo",
    "spot_book": "https://api.binance.com/api/v3/depth",
    "future_book": "https://fapi.binance.com/fapi/v1/depth",
    "funding": "https://fapi.binance.com/fapi/v1/fundingRate",
    "mark": "https://fapi.binance.com/fapi/v1/markPriceKlines",
}


def durable_raw(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def verify_sources(directory, records):
    seen = set()
    for meta in records:
        ident = meta["id"]
        if not re.fullmatch(r"[0-9a-f]{32}", ident) or ident in seen:
            raise ValueError("Invalid saved public source identity")
        seen.add(ident)
        if meta["raw_file"] != "raw/" + ident + ".bin.gz":
            raise ValueError("Saved public source path mismatch")
        path = (directory / meta["raw_file"]).resolve()
        if not path.is_relative_to((directory / "raw").resolve()):
            raise ValueError("Saved source outside raw directory")
        url = urlsplit(meta["url"])
        if url._replace(query="").geturl() != URLS.get(meta["name"]):
            raise ValueError("Saved endpoint outside allowlist")
        raw = gzip.decompress(path.read_bytes())
        if (
            sha(raw) != meta["sha256"]
            or strict_json(path.with_name(ident + ".json").read_bytes()) != meta
        ):
            raise ValueError("Changed saved public source")


def utc_now():
    return datetime.now(UTC)


class PublicSource:
    def __init__(self, directory: Path):
        self.directory = directory / "raw"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=10, trust_env=False, follow_redirects=False)
        self.lock = threading.Lock()
        self.requests, self.bytes = 0, 0
        self.records = []

    def close(self):
        self.client.close()

    def get(self, name: str, params=None):
        if name not in URLS:
            raise ValueError("Endpoint outside public allowlist")
        allowed = {
            "spot_book": {"symbol", "limit"},
            "future_book": {"symbol", "limit"},
            "funding": {"symbol", "startTime", "endTime", "limit"},
            "mark": {"symbol", "interval", "startTime", "endTime", "limit"},
        }
        if set(params or {}) - allowed.get(name, set()):
            raise ValueError("Unregistered public request parameter")
        if (
            name in {"spot_book", "future_book", "funding", "mark"}
            and (params or {}).get("symbol") != "BTCUSDT"
        ):
            raise ValueError("Only registered BTC symbol is allowed")
        with self.lock:
            if self.requests >= 16 or self.bytes >= 20_000_000:
                raise ValueError("Invocation data budget exceeded")
            self.requests += 1
        request = self.client.build_request("GET", URLS[name], params=params)
        ident = uuid.uuid4().hex
        start, monotonic = time.time_ns(), time.monotonic_ns()
        try:
            response = self.client.send(request, stream=True)
        except httpx.HTTPError as exc:
            durable_raw(
                self.directory / (ident + ".json"),
                encoded(
                    {
                        "name": name,
                        "url": str(request.url),
                        "request_start_ns": start,
                        "received_ns": time.time_ns(),
                        "error": str(exc),
                    }
                )
                + b"\n",
            )
            raise
        chunks, failure = [], None
        try:
            for chunk in response.iter_bytes(chunk_size=65536):
                with self.lock:
                    remaining = max(0, 20_000_000 - self.bytes)
                    accepted = chunk[:remaining]
                    self.bytes += len(accepted)
                chunks.append(accepted)
                if len(accepted) != len(chunk):
                    raise ValueError("Invocation byte budget exceeded")
        except (httpx.HTTPError, ValueError) as exc:
            failure = exc
        finally:
            response.close()
        end, elapsed = time.time_ns(), time.monotonic_ns() - monotonic
        raw = b"".join(chunks)
        meta = {
            "id": ident,
            "name": name,
            "url": str(request.url),
            "request_start_ns": start,
            "received_ns": end,
            "monotonic_elapsed_ns": elapsed,
            "status": response.status_code,
            "complete_response": failure is None,
            "sha256": sha(raw),
            "raw_file": "raw/" + ident + ".bin.gz",
        }
        durable_raw(self.directory / (ident + ".bin.gz"), gzip.compress(raw, mtime=0))
        durable_raw(self.directory / (ident + ".json"), encoded(meta) + b"\n")
        with self.lock:
            self.records.append(meta)
        if failure:
            raise failure
        response.raise_for_status()
        if self.bytes > 20_000_000:
            raise ValueError("Invocation byte budget exceeded")
        if elapsed > 2_000_000_000 or abs((end - start) - elapsed) > 100_000_000:
            raise ValueError("Slow request or changed local clock")
        return strict_json(raw), meta


def capture(source: PublicSource):
    offsets = {}
    for venue in ("spot", "future"):
        clock, meta = source.get(venue + "_time")
        midpoint = (meta["request_start_ns"] + meta["received_ns"]) / 2_000_000
        offset = integer(clock["serverTime"], 1) - midpoint
        if abs(offset) > 5000:
            raise ValueError("Public clock offset exceeds tolerance")
        offsets[venue] = offset
    sinfo, _ = source.get("spot_info")
    finfo, _ = source.get("future_info")
    selected = []
    for info in (sinfo, finfo):
        rows = [s for s in info["symbols"] if s["symbol"] == "BTCUSDT"]
        if len(rows) != 1:
            raise ValueError("Ambiguous BTC venue symbol")
        selected.append(rows[0])
    sf, ff = filters(sinfo), filters(finfo)
    for value in (sf, ff):
        validate_filters(value)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(source.get, "spot_book", {"symbol": "BTCUSDT", "limit": 100})
        b = pool.submit(source.get, "future_book", {"symbol": "BTCUSDT", "limit": 100})
        spot, sm = a.result()
        future, fm = b.result()
    validate_timing(sm, fm)
    for book in (spot, future):
        validate_book(book)
    # Spot REST depth has no event timestamp; do not turn transport freshness into fill certification.
    if "E" in future:
        age = fm["received_ns"] / 1_000_000 + offsets["future"] - integer(future["E"], 1)
        if not -1000 <= age <= 5000:
            raise ValueError("Stale futures book event")
    return {
        "spot": spot,
        "future": future,
        "sf": sf,
        "ff": ff,
        "base_commission_precision": integer(selected[0]["baseCommissionPrecision"]),
        "quote_ns": max(sm["received_ns"], fm["received_ns"]),
        "clock_offsets_ms": offsets,
        "spot_event_freshness_certified": False,
        "actual_fills_certified": False,
        "sources": list(source.records),
    }


def history(source: PublicSource, entry_ms: int, cutoff_ms: int):
    hour = 3_600_000
    funding, cursor = [], entry_ms // hour * hour + hour
    while cursor < cutoff_ms:
        rows, _ = source.get(
            "funding",
            {"symbol": "BTCUSDT", "startTime": cursor, "endTime": cutoff_ms - 1, "limit": 1000},
        )
        if not isinstance(rows, list):
            raise ValueError("Invalid funding response")
        funding.extend(rows)
        if len(rows) < 1000:
            break
        next_cursor = integer(rows[-1]["fundingTime"]) + 1
        if next_cursor <= cursor:
            raise ValueError("Funding pagination did not advance")
        cursor = next_cursor
    marks, cursor, stop = [], entry_ms // hour * hour, cutoff_ms // hour * hour
    while cursor < stop:
        rows, _ = source.get(
            "mark",
            {
                "symbol": "BTCUSDT",
                "interval": "1h",
                "startTime": cursor,
                "endTime": stop - 1,
                "limit": 1000,
            },
        )
        if not isinstance(rows, list) or not rows or rows[0][0] != cursor:
            raise ValueError("Missing mark-price history")
        marks.extend(rows)
        next_cursor = integer(rows[-1][0]) + hour
        if next_cursor <= cursor:
            raise ValueError("Mark pagination did not advance")
        cursor = next_cursor
    return funding, marks
