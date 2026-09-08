"""Public-only bounded acquisition for the registered absolute carry study."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/evidence/absolute_research_20260908/protocol.json"
DAY = 86_400_000
HOUR = DAY // 24
START = int(datetime(2023, 12, 1, tzinfo=UTC).timestamp() * 1000)
END = int(datetime(2026, 9, 7, tzinfo=UTC).timestamp() * 1000)
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )


class PublicCache:
    def __init__(self, directory: Path):
        self.directory = directory
        (directory / "raw").mkdir(parents=True, exist_ok=True)
        self.sources = []
        self.client = httpx.Client(timeout=40, follow_redirects=True, trust_env=False)

    def get(self, url: str, params: dict):
        request = self.client.build_request("GET", url, params=params)
        if request.url.host not in {"api.binance.com", "fapi.binance.com"}:
            raise ValueError("Unregistered public source")
        key = sha(str(request.url).encode())
        meta_path = self.directory / "raw" / f"{key}.json"
        raw_path = self.directory / "raw" / f"{key}.bin.gz"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            payload = gzip.decompress(raw_path.read_bytes())
            if meta["sha256"] != sha(payload) or meta["url"] != str(request.url):
                raise ValueError("Cached source integrity failure")
        else:
            if len(self.sources) >= 180:
                raise ValueError("Public request budget exhausted")
            for attempt in range(3):
                known_at = datetime.now(UTC).isoformat()
                try:
                    response = self.client.send(request)
                    payload = response.content
                    meta = {
                        "url": str(request.url),
                        "known_at": known_at,
                        "status": response.status_code,
                        "sha256": sha(payload),
                        "raw": str(raw_path.relative_to(self.directory)),
                    }
                    if response.status_code != 200:
                        write(
                            self.directory / f"failure_{key}_{attempt}.json",
                            meta | {"body": response.text[:300]},
                        )
                    response.raise_for_status()
                    break
                except httpx.HTTPError:
                    if attempt == 2:
                        raise
                    time.sleep(2 * (attempt + 1))
            raw_path.write_bytes(gzip.compress(payload, mtime=0))
            write(meta_path, meta)
            time.sleep(0.15)
        self.sources.append(meta | {"metadata": str(meta_path.relative_to(self.directory))})
        return json.loads(payload)


def collect_bars(cache: PublicCache, symbol: str, kind: str):
    interval = HOUR if kind == "mark_hourly" else DAY
    endpoint = (
        "https://api.binance.com/api/v3/klines"
        if kind == "spot_daily"
        else "https://fapi.binance.com/fapi/v1/markPriceKlines"
        if kind == "mark_hourly"
        else "https://fapi.binance.com/fapi/v1/klines"
    )
    cursor = START
    result = []
    while cursor <= END:
        part = cache.get(
            endpoint,
            {
                "symbol": symbol,
                "interval": "1h" if interval == HOUR else "1d",
                "startTime": cursor,
                "endTime": END,
                "limit": 1000,
            },
        )
        if not isinstance(part, list) or not part:
            raise ValueError(f"Missing bars {symbol} {kind} {cursor}")
        if part[0][0] != cursor or any(r[0] > END for r in part):
            raise ValueError("Unexpected bar coverage")
        result.extend(part)
        cursor = int(part[-1][0]) + interval
        print(symbol, kind, len(result), flush=True)
    if [r[0] for r in result] != list(range(START, END + interval, interval)):
        raise ValueError("Missing/duplicate bars")
    # Strip the final unfinished candle to its opening field only.
    result[-1] = result[-1][:2]
    return result


def collect_funding(cache: PublicCache, symbol: str):
    cursor, rows = START, []
    while cursor < END:
        part = cache.get(
            "https://fapi.binance.com/fapi/v1/fundingRate",
            {"symbol": symbol, "startTime": cursor, "endTime": END - 1, "limit": 1000},
        )
        if not isinstance(part, list):
            raise ValueError("Invalid funding response")
        if not part:
            break
        times = [r["fundingTime"] for r in part]
        if times != sorted(set(times)) or not all(cursor <= t < END for t in times):
            raise ValueError("Funding pagination overlap/future")
        rows.extend(part)
        cursor = times[-1] + 1
        if len(part) < 1000:
            break
    buckets = {r["fundingTime"] // (8 * HOUR) for r in rows}
    expected = set(range(START // (8 * HOUR), END // (8 * HOUR)))
    if buckets != expected:
        raise ValueError(f"Missing funding baseline buckets: {len(expected - buckets)}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    if (args.data_dir / "manifest.json").exists():
        raise ValueError("Completed dataset exists; use offline runner or a separate directory")
    cache = PublicCache(args.data_dir)
    normalized = {}
    try:
        for kind, url in (
            ("spot", "https://api.binance.com/api/v3/exchangeInfo"),
            ("perp", "https://fapi.binance.com/fapi/v1/exchangeInfo"),
        ):
            info = cache.get(url, {})
            write(args.data_dir / f"{kind}_exchangeInfo.json", info)
            normalized[f"{kind}_exchangeInfo.json"] = sha(
                (args.data_dir / f"{kind}_exchangeInfo.json").read_bytes()
            )
        for symbol in SYMBOLS:
            for kind in ("spot_daily", "perp_daily", "mark_hourly", "funding"):
                rows = (
                    collect_funding(cache, symbol)
                    if kind == "funding"
                    else collect_bars(cache, symbol, kind)
                )
                path = args.data_dir / f"{symbol}_{kind}.json.gz"
                path.write_bytes(
                    gzip.compress(json.dumps(rows, separators=(",", ":")).encode(), mtime=0)
                )
                normalized[path.name] = sha(path.read_bytes())
                print(symbol, kind, "complete", len(rows), flush=True)
        write(
            args.data_dir / "manifest.json",
            {
                "protocol_sha256": sha(PROTOCOL.read_bytes()),
                "start_ms": START,
                "end_exclusive_ms": END,
                "normalized": normalized,
                "sources": cache.sources,
                "errors": [],
                "historical_filter_coverage": "CURRENT_FILTERS_ONLY_NOT_HISTORICAL_CERTIFICATION",
            },
        )
    except Exception as exc:
        write(
            args.data_dir / "acquisition_failure.json",
            {"error": repr(exc), "sources": cache.sources},
        )
        raise


if __name__ == "__main__":
    main()
