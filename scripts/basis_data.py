"""Bounded public acquisition and raw-to-normalized verification for BTC basis research."""

from __future__ import annotations

import argparse
import calendar
import csv
import gzip
import hashlib
import io
import json
import math
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx

HOUR = 3_600_000
DAY = HOUR * 24
START = int(datetime(2023, 12, 1, tzinfo=UTC).timestamp() * 1000)
ENTRY = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
END = int(datetime(2026, 9, 7, tzinfo=UTC).timestamp() * 1000)
TAIL = int(datetime(2026, 9, 1, tzinfo=UTC).timestamp() * 1000)
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/basis_research_20260908"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def stamp(t: int) -> str:
    return datetime.fromtimestamp(t / 1000, UTC).isoformat()


def protocol() -> dict:
    raw = (EVIDENCE / "protocol.json").read_bytes()
    registry = json.loads((EVIDENCE / "trials.json").read_text(encoding="utf-8"))
    if sha(raw) != registry["protocol_sha256"]:
        raise ValueError("Registered protocol changed")
    return json.loads(raw)


def contracts() -> dict[str, int]:
    result = {}
    for year in range(2024, 2027):
        for month in (3, 6, 9, 12):
            day = calendar.monthrange(year, month)[1]
            while datetime(year, month, day).weekday() != 4:
                day -= 1
            expiry = datetime(year, month, day, 8, tzinfo=UTC)
            result["BTCUSDT_" + expiry.strftime("%y%m%d")] = int(expiry.timestamp() * 1000)
    return result


class PublicCache:
    """No credentials or order endpoints. Responses are immutable and resumable."""

    def __init__(self, directory: Path):
        self.directory = directory
        (directory / "raw").mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.client = httpx.Client(timeout=40, trust_env=False, follow_redirects=False)
        self.sources = {}
        for p in (directory / "raw").glob("*.json"):
            meta = json.loads(p.read_text(encoding="utf-8"))
            self.sources[p.stem] = meta
        self.requests = len(self.sources)
        self.bytes = sum(m["bytes"] for m in self.sources.values())

    def get(self, url: str, params: dict | None = None) -> tuple[bytes, str]:
        req = self.client.build_request("GET", url, params=params)
        if req.url.host not in {
            "api.binance.com",
            "fapi.binance.com",
            "data.binance.vision",
            "s3-ap-northeast-1.amazonaws.com",
        }:
            raise ValueError("Source host outside public allowlist")
        if req.url.host in {"api.binance.com", "fapi.binance.com"} and req.url.path not in {
            "/api/v3/klines",
            "/fapi/v1/klines",
            "/fapi/v1/markPriceKlines",
            "/fapi/v1/fundingRate",
            "/futures/data/delivery-price",
        }:
            raise ValueError("Non-research endpoint")
        key = sha(str(req.url).encode())
        raw_path = self.directory / "raw" / (key + ".bin.gz")
        if key in self.sources:
            raw = gzip.decompress(raw_path.read_bytes())
            if sha(raw) != self.sources[key]["sha256"]:
                raise ValueError("Changed cached response")
            return raw, key
        for attempt in range(3):
            with self.lock:
                if self.requests >= 1000 or self.bytes >= 250_000_000:
                    raise ValueError("Acquisition budget exceeded")
                self.requests += 1
            try:
                started = datetime.now(UTC).isoformat()
                response = self.client.send(req)
                raw = response.content
                meta = {
                    "url": str(req.url),
                    "request_started_utc": started,
                    "known_at": datetime.now(UTC).isoformat(),
                    "status": response.status_code,
                    "sha256": sha(raw),
                    "bytes": len(raw),
                }
                if response.status_code in (418, 429) or response.status_code >= 500:
                    write(self.directory / f"failure_{key}_{attempt}.json", meta)
                    response.raise_for_status()
                raw_path.write_bytes(gzip.compress(raw, mtime=0))
                write(self.directory / "raw" / (key + ".json"), meta)
                with self.lock:
                    self.sources[key] = meta
                    self.bytes += len(raw)
                    if self.bytes > 250_000_000:
                        raise ValueError("Download byte budget exceeded")
                return raw, key
            except httpx.HTTPError:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        raise AssertionError("unreachable")

    def ok(self, key: str) -> None:
        if self.sources[key]["status"] != 200:
            raise ValueError("Source returned " + str(self.sources[key]["status"]))


def bars_from_zip(raw: bytes) -> list:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        if len(names) != 1 or not names[0].endswith(".csv"):
            raise ValueError("Unexpected archive members")
        rows = list(csv.reader(io.StringIO(z.read(names[0]).decode("utf-8-sig"))))
    if rows and not rows[0][0].isdigit():
        rows = rows[1:]
    return rows


def normalize_bars(rows: list) -> list:
    out = {}
    for original in rows:
        row = list(original)
        t = int(row[0])
        microseconds = t > 100_000_000_000_000
        if microseconds:
            t //= 1000
        if not START <= t <= END:
            continue
        row[0] = t
        if t == END:
            row = [t, str(row[1])]
        else:
            if len(row) < 8:
                raise ValueError("Incomplete historical bar")
            row[6] = int(row[6]) // (1000 if microseconds else 1)
            row = [t, *[str(v) for v in row[1:6]], row[6], str(row[7])]
            prices = list(map(float, row[1:5]))
            if not all(math.isfinite(v) and v > 0 for v in prices):
                raise ValueError("Invalid historical OHLC")
            if (
                prices[1] < max(prices[0], prices[3])
                or prices[2] > min(prices[0], prices[3])
                or prices[2] > prices[1]
            ):
                raise ValueError("Invalid OHLC bounds")
            if row[6] != t + HOUR - 1 or t % HOUR or float(row[7]) < 0:
                raise ValueError("Invalid hourly alignment or volume")
        if not math.isfinite(float(row[1])) or float(row[1]) <= 0:
            raise ValueError("Invalid opening price")
        if t in out and out[t] != row:
            raise ValueError("Conflicting duplicate bar")
        out[t] = row
    return [out[t] for t in sorted(out)]


def rest_bars(cache: PublicCache, symbol: str, kind: str, start=START) -> list[dict]:
    url = (
        "https://api.binance.com/api/v3/klines"
        if kind == "spot"
        else "https://fapi.binance.com/fapi/v1/markPriceKlines"
        if kind == "mark"
        else "https://fapi.binance.com/fapi/v1/klines"
    )
    parts, cursor = [], start
    while cursor <= END:
        raw, key = cache.get(
            url,
            {
                "symbol": symbol,
                "interval": "1h",
                "startTime": cursor,
                "endTime": END,
                "limit": 1000,
            },
        )
        cache.ok(key)
        rows = json.loads(raw)
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"Missing REST bars {symbol} {kind} {cursor}")
        if int(rows[0][0]) != cursor:
            raise ValueError("REST coverage gap")
        parts.append({"source": key, "format": "rest_bars"})
        cursor = int(rows[-1][0]) + HOUR
    return parts


def quarterly_parts(cache: PublicCache, symbol: str, expiry: int, kind: str) -> list[dict]:
    dataset = "klines" if kind == "trade" else "markPriceKlines"
    prefix = f"data/futures/um/monthly/{dataset}/{symbol}/1h/"
    raw, key = cache.get(
        "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision",
        {"prefix": prefix, "max-keys": 1000},
    )
    cache.ok(key)
    listing = ET.fromstring(raw)
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    if listing.findtext("s:IsTruncated", namespaces=ns) != "false":
        raise ValueError("Truncated archive listing")
    parts = []
    for item in listing.findall("s:Contents", ns):
        name = item.findtext("s:Key", namespaces=ns)
        if name is None or not name.endswith(".zip"):
            continue
        month = name[-11:-4]
        if not "2023-12" <= month <= "2026-08":
            continue
        body, file_key = cache.get("https://data.binance.vision/" + name)
        checksum, sum_key = cache.get("https://data.binance.vision/" + name + ".CHECKSUM")
        cache.ok(file_key)
        cache.ok(sum_key)
        if checksum.decode().split()[0].lower() != sha(body):
            raise ValueError("Provider archive checksum mismatch")
        parts.append({"source": file_key, "checksum_source": sum_key, "format": "archive_bars"})
    if expiry >= END:
        parts.extend(rest_bars(cache, symbol, "mark" if kind == "mark" else "perp", TAIL))
    print(symbol, kind, "source parts", len(parts), flush=True)
    return parts


def normalize_group(directory: Path, parts: list[dict], kind: str) -> list:
    rows = []
    for part in parts:
        raw = gzip.decompress((directory / "raw" / (part["source"] + ".bin.gz")).read_bytes())
        if part["format"] == "archive_bars":
            checksum = gzip.decompress(
                (directory / "raw" / (part["checksum_source"] + ".bin.gz")).read_bytes()
            )
            if checksum.decode().split()[0].lower() != sha(raw):
                raise ValueError("Archive checksum differs")
            rows.extend(bars_from_zip(raw))
        else:
            rows.extend(json.loads(raw))
    if kind == "bars":
        return normalize_bars(rows)
    field = "fundingTime" if kind == "funding" else "deliveryTime"
    result = {}
    for row in rows:
        t = int(row[field])
        if not START <= t < END:
            continue
        if t in result and result[t] != row:
            raise ValueError("Conflicting cashflow outcome")
        if kind == "funding":
            if (
                row["symbol"] != "BTCUSDT"
                or not math.isfinite(float(row["fundingRate"]))
                or not math.isfinite(float(row["markPrice"]))
                or float(row["markPrice"]) <= 0
            ):
                raise ValueError("Invalid funding cashflow")
        elif not math.isfinite(float(row["deliveryPrice"])) or float(row["deliveryPrice"]) <= 0:
            raise ValueError("Invalid settlement")
        result[t] = row
    return [result[t] for t in sorted(result)]


def collect(directory: Path) -> None:
    spec = protocol()
    if (directory / "manifest.json").exists():
        raise ValueError("Completed data exists; use offline loader")
    cache = PublicCache(directory)
    groups = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = {
            kind: pool.submit(rest_bars, cache, "BTCUSDT", kind)
            for kind in ("spot", "perp", "mark")
        }
        for kind, task in tasks.items():
            groups[kind] = {"kind": "bars", "parts": task.result()}
            print("BTC hourly", kind, "collected", flush=True)
    parts, cursor = [], START
    while cursor < END:
        raw, key = cache.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            {"symbol": "BTCUSDT", "startTime": cursor, "endTime": END - 1, "limit": 1000},
        )
        cache.ok(key)
        rows = json.loads(raw)
        parts.append({"source": key, "format": "funding"})
        if not rows or len(rows) < 1000:
            break
        cursor = int(rows[-1]["fundingTime"]) + 1
    groups["funding"] = {"kind": "funding", "parts": parts}
    _, key = cache.get("https://fapi.binance.com/futures/data/delivery-price", {"pair": "BTCUSDT"})
    cache.ok(key)
    groups["delivery"] = {"kind": "delivery", "parts": [{"source": key, "format": "delivery"}]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {
            (symbol, kind): pool.submit(quarterly_parts, cache, symbol, expiry, kind)
            for symbol, expiry in contracts().items()
            for kind in ("trade", "mark")
        }
        for (symbol, kind), task in tasks.items():
            groups[symbol + "_" + kind] = {"kind": "bars", "parts": task.result()}
    for name, group in groups.items():
        rows = normalize_group(directory, group["parts"], group["kind"])
        raw = gzip.compress(json.dumps(rows, separators=(",", ":")).encode(), mtime=0)
        filename = name + ".json.gz"
        (directory / filename).write_bytes(raw)
        group.update({"file": filename, "sha256": sha(raw), "rows": len(rows)})
    write(
        directory / "manifest.json",
        {
            "protocol_id": spec["id"],
            "protocol_sha256": sha((EVIDENCE / "protocol.json").read_bytes()),
            "sources": dict(sorted(cache.sources.items())),
            "groups": groups,
            "contracts": contracts(),
            "network_requests": cache.requests,
            "download_bytes": cache.bytes,
        },
    )
    load(directory)
    print("Dataset normalized and independently rebuilt from raw sources", flush=True)


def load(directory: Path, verify_raw=True) -> tuple[dict, dict]:
    protocol()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["protocol_sha256"] != sha((EVIDENCE / "protocol.json").read_bytes()):
        raise ValueError("Data protocol mismatch")
    if verify_raw:
        for key, meta in manifest["sources"].items():
            raw = gzip.decompress((directory / "raw" / (key + ".bin.gz")).read_bytes())
            if sha(raw) != meta["sha256"] or meta["status"] != 200:
                raise ValueError("Raw response mismatch")
    groups = {}
    for name, group in manifest["groups"].items():
        raw = (directory / group["file"]).read_bytes()
        if sha(raw) != group["sha256"]:
            raise ValueError("Normalized hash changed")
        rows = json.loads(gzip.decompress(raw))
        if verify_raw and rows != normalize_group(directory, group["parts"], group["kind"]):
            raise ValueError("Raw reconstruction differs: " + name)
        groups[name] = {int(r[0]): r for r in rows} if group["kind"] == "bars" else rows
    expected = list(range(START, END + HOUR, HOUR))
    for kind in ("spot", "perp", "mark"):
        if list(groups[kind]) != expected:
            raise ValueError("Main hourly coverage incomplete: " + kind)
    times = [r["fundingTime"] for r in groups["funding"]]
    if times != sorted(set(times)) or {t // (8 * HOUR) for t in times} != set(
        range(START // (8 * HOUR), END // (8 * HOUR))
    ):
        raise ValueError("Missing funding baseline settlement bucket")
    return groups, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    collect(args.output)
