"""Bounded public-data acquisition for the preregistered Discovery screen.

Independent of production collectors, credentials, trials and order adapters.
All downloaded bytes, including the historical symbol catalog, are retained.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/evidence/altcoin_analogs_20260907/protocol.json"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
DAY = 86_400_000


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def time_ms(value: int | str) -> int:
    number = int(value)
    return number // 1000 if number >= 100_000_000_000_000 else number


def select_symbols(symbols: list[str], protocol: dict) -> list[str]:
    excluded = set(protocol["data"]["exclude_bases"])
    allowed = []
    for symbol in set(symbols):
        if not symbol.endswith("USDT"):
            continue
        base = symbol[:-4]
        if base in excluded or base.endswith(("UP", "DOWN", "BULL", "BEAR")):
            continue
        allowed.append(symbol)
    seed = protocol["screen_id"]
    return sorted(allowed, key=lambda s: digest(f"{seed}:{s}".encode()))[
        : protocol["data"]["max_assets"]
    ]


class Acquisition:
    def __init__(self, directory: Path):
        self.directory = directory
        (directory / "raw").mkdir(parents=True, exist_ok=True)
        (directory / "pairs").mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self.next_call = 0.0
        self.client = httpx.Client(timeout=40, follow_redirects=True)

    def get(self, url: str, params: dict | None = None) -> bytes:
        request = self.client.build_request("GET", url, params=params)
        key = digest(str(request.url).encode())
        raw = self.directory / "raw" / f"{key}.bin.gz"
        meta = self.directory / "raw" / f"{key}.json"
        if raw.exists() and meta.exists():
            metadata = json.loads(meta.read_text())
            content = gzip.decompress(raw.read_bytes())
            if digest(content) != metadata["sha256"]:
                raise ValueError(f"cached content hash mismatch: {key}")
            return content
        for attempt in range(4):
            with self.lock:
                delay = max(0.0, self.next_call - time.monotonic())
                self.next_call = time.monotonic() + delay + 0.22
            time.sleep(delay)
            try:
                response = self.client.send(request)
                if response.status_code in (418, 429):
                    # Honor the public service limit rather than rotate hosts/identities.
                    wait = float(response.headers.get("Retry-After", "30"))
                    time.sleep(min(max(wait, 1), 60))
                    response.raise_for_status()
                response.raise_for_status()
                content = response.content
                metadata = {
                    "url": str(response.url),
                    "retrieved_at_utc": utcnow(),
                    "http_status": response.status_code,
                    "sha256": digest(content),
                    "bytes": len(content),
                    "server_date": response.headers.get("date"),
                }
                raw.write_bytes(gzip.compress(content, mtime=0))
                meta.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                return content
            except (httpx.HTTPError, ValueError):
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("unreachable")

    def listing(self, prefix: str, delimiter: str = "") -> tuple[list[str], list[str]]:
        prefixes, keys = [], []
        marker = ""
        while True:
            params = {"prefix": prefix, "max-keys": 1000}
            if delimiter:
                params["delimiter"] = delimiter
            if marker:
                params["marker"] = marker
            root = ET.fromstring(self.get(S3, params))
            prefixes.extend(x.text for x in root.findall("s:CommonPrefixes/s:Prefix", NS))
            page = [x.text for x in root.findall("s:Contents/s:Key", NS)]
            keys.extend(page)
            if root.findtext("s:IsTruncated", namespaces=NS) != "true":
                return prefixes, keys
            marker = root.findtext("s:NextMarker", namespaces=NS) or page[-1]

    def pair(self, symbol: str, start: int, end: int) -> dict:
        output = self.directory / "pairs" / f"{symbol}.json.gz"
        if output.exists():
            return json.loads(gzip.decompress(output.read_bytes()))["metadata"]
        rows = []
        cursor = start
        rest_error = None
        source = "REST"
        try:
            while cursor < end:
                page = json.loads(
                    self.get(
                        "https://api.binance.com/api/v3/klines",
                        {
                            "symbol": symbol,
                            "interval": "1d",
                            "startTime": cursor,
                            "endTime": end - 1,
                            "limit": 1000,
                        },
                    )
                )
                if not isinstance(page, list):
                    raise ValueError("klines response is not a list")
                rows.extend(page)
                if len(page) < 1000:
                    break
                new_cursor = time_ms(page[-1][0]) + DAY
                if new_cursor <= cursor:
                    raise ValueError("non-advancing pagination")
                cursor = new_cursor
        except Exception as exc:
            rest_error = f"{type(exc).__name__}: {exc}"
            rows = []
        if not rows:
            source = "ARCHIVE"
            _, keys = self.listing(f"data/spot/monthly/klines/{symbol}/1d/")
            for key in keys:
                name = key.rsplit("/", 1)[-1]
                if not name.endswith(".zip"):
                    continue
                month = name[len(symbol) + 4 : -4]
                if not "2020-10" <= month <= "2026-08":
                    continue
                content = self.get("https://data.binance.vision/" + key)
                checksum = self.get("https://data.binance.vision/" + key + ".CHECKSUM")
                if digest(content) != checksum.decode().split()[0]:
                    raise ValueError(f"archive checksum mismatch: {key}")
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    for member in archive.namelist():
                        parsed = csv.reader(io.StringIO(archive.read(member).decode()))
                        rows.extend(row for row in parsed if row and row[0].isdigit())
        by_day = {}
        duplicates = 0
        for row in rows:
            opened, closed = time_ms(row[0]), time_ms(row[6])
            if opened < start or closed >= end:
                continue
            if opened % DAY:
                raise ValueError(f"non-UTC daily timestamp: {symbol} {opened}")
            if opened in by_day:
                duplicates += 1
                if by_day[opened] != row:
                    raise ValueError(f"conflicting duplicate: {symbol} {opened}")
            by_day[opened] = row
        normalized = []
        for opened, row in sorted(by_day.items()):
            # event timestamps and raw quote volume are preserved; no imputation.
            normalized.append(
                [opened, *[float(row[i]) for i in (1, 2, 3, 4, 5, 7)], time_ms(row[6])]
            )
        gaps = sum((b[0] - a[0]) // DAY - 1 for a, b in zip(normalized, normalized[1:]))
        metadata = {
            "symbol": symbol,
            "source": source,
            "rest_error": rest_error,
            "rows": len(normalized),
            "first_open_ms": normalized[0][0] if normalized else None,
            "last_open_ms": normalized[-1][0] if normalized else None,
            "missing_internal_days": gaps,
            "duplicate_rows": duplicates,
            "finalized_at_utc": utcnow(),
        }
        payload = {
            "metadata": metadata,
            "columns": [
                "open_ms",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_volume",
                "close_ms",
            ],
            "rows": normalized,
        }
        output.write_bytes(gzip.compress(json.dumps(payload).encode(), mtime=0))
        return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL.read_text())
    acquisition = Acquisition(args.data_dir)
    prefixes, _ = acquisition.listing("data/spot/monthly/klines/", "/")
    catalog = sorted(p.rstrip("/").rsplit("/", 1)[-1] for p in prefixes)
    selected = select_symbols(catalog, protocol)
    manifest = {
        "protocol_sha256": digest(PROTOCOL.read_bytes()),
        "screen_id": protocol["screen_id"],
        "started_at_utc": utcnow(),
        "catalog_count": len(catalog),
        "catalog_usdt_count": sum(s.endswith("USDT") for s in catalog),
        "catalog": catalog,
        "selected": selected,
        "reference": "BTCUSDT",
        "pairs": [],
        "errors": [],
    }
    manifest_path = args.data_dir / "acquisition.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"Catalog: {len(catalog)} pairs; USDT: {manifest['catalog_usdt_count']}; selected: {len(selected)}",
        flush=True,
    )
    start = int(
        datetime.fromisoformat(protocol["data"]["start"]).replace(tzinfo=timezone.utc).timestamp()
        * 1000
    )
    end = int(datetime.fromisoformat(protocol["data"]["cutoff_exclusive"]).timestamp() * 1000)
    with ThreadPoolExecutor(max_workers=6) as executor:
        tasks = {
            executor.submit(acquisition.pair, s, start, end): s for s in selected + ["BTCUSDT"]
        }
        for i, future in enumerate(as_completed(tasks), 1):
            symbol = tasks[future]
            try:
                manifest["pairs"].append(future.result())
            except Exception as exc:
                manifest["errors"].append({"symbol": symbol, "error": str(exc)})
                print(f"ERROR {symbol}: {exc}", flush=True)
            if i % 20 == 0 or i == len(tasks):
                manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                print(f"Completed {i}/{len(tasks)}; errors={len(manifest['errors'])}", flush=True)
    manifest["completed_at_utc"] = utcnow()
    manifest["pairs"].sort(key=lambda x: x["symbol"])
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if manifest["errors"]:
        raise SystemExit(
            "Incomplete acquisition; repair transport without changing the sample before inference"
        )


if __name__ == "__main__":
    main()
