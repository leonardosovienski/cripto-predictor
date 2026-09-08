"""Second raw-data reconstruction using only stdlib; no production normalizer imports."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import zipfile
from decimal import Decimal
from pathlib import Path

HOUR = 3_600_000
START = 1701388800000
END = 1788739200000


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError("Duplicate JSON field")
            out[k] = v
        return out

    def reject(value):
        raise ValueError("Nonfinite JSON literal: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def finite(value, positive=False):
    x = Decimal(str(value))
    if not x.is_finite() or (positive and x <= 0):
        raise ValueError("Invalid financial observation")
    return x


def timestamp(value):
    if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)):
        raise ValueError("Invalid timestamp")
    return int(value)


def rebuild(rows, kind):
    result = {}
    for original in rows:
        if kind == "bars":
            t = timestamp(original[0])
            divisor = 1000 if t > 100_000_000_000_000 else 1
            t //= divisor
            if not START <= t <= END:
                continue
            if t == END:
                finite(original[1], positive=True)
                row = [t, str(original[1])]
            else:
                if len(original) < 8:
                    raise ValueError("Incomplete raw bar")
                o, h, low, c = [finite(x, positive=True) for x in original[1:5]]
                if h < max(o, c) or low > min(o, c) or low > h:
                    raise ValueError("Invalid raw OHLC")
                if finite(original[5]) < 0 or finite(original[7]) < 0:
                    raise ValueError("Invalid raw volume")
                close = timestamp(original[6]) // divisor
                if t % HOUR or close != t + HOUR - 1:
                    raise ValueError("Raw bar alignment")
                row = [t, *map(str, original[1:6]), close, str(original[7])]
        else:
            field = "fundingTime" if kind == "funding" else "deliveryTime"
            t = timestamp(original[field])
            if not START <= t < END:
                continue
            row = original
            if kind == "funding":
                if row["symbol"] != "BTCUSDT":
                    raise ValueError("Unexpected funding asset")
                finite(row["fundingRate"])
                finite(row["markPrice"], positive=True)
            elif kind == "delivery":
                finite(row["deliveryPrice"], positive=True)
            else:
                raise ValueError("Unknown source kind")
        if t in result and result[t] != row:
            raise ValueError("Conflicting raw observations")
        result[t] = row
    return [result[t] for t in sorted(result)]


def audit(directory: Path, output: Path):
    manifest = decode((directory / "manifest.json").read_bytes())
    raw = {}
    for key, meta in manifest["sources"].items():
        if not re.fullmatch(r"[0-9a-f]{64}", key) or digest(meta["url"].encode()) != key:
            raise ValueError("Invalid source identity")
        body = gzip.decompress((directory / "raw" / (key + ".bin.gz")).read_bytes())
        if meta["status"] != 200 or digest(body) != meta["sha256"]:
            raise ValueError("Changed raw response")
        raw[key] = body
    counts = {}
    for name, group in manifest["groups"].items():
        collected = []
        for part in group["parts"]:
            body = raw[part["source"]]
            if part["format"] == "archive_bars":
                if raw[part["checksum_source"]].decode().split()[0].lower() != digest(body):
                    raise ValueError("Archive checksum mismatch")
                with zipfile.ZipFile(io.BytesIO(body)) as archive:
                    if len(archive.namelist()) != 1:
                        raise ValueError("Unexpected CSV archive")
                    lines = list(
                        csv.reader(
                            io.StringIO(archive.read(archive.namelist()[0]).decode("utf-8-sig"))
                        )
                    )
                if lines and not lines[0][0].isdigit():
                    lines = lines[1:]
            else:
                lines = decode(body)
            collected.extend(lines)
        rows = rebuild(collected, group["kind"])
        normalized = (directory / group["file"]).resolve()
        if not normalized.is_relative_to(directory.resolve()):
            raise ValueError("Unexpected normalized file path")
        body = normalized.read_bytes()
        if digest(body) != group["sha256"] or decode(gzip.decompress(body)) != rows:
            raise ValueError("Second reconstruction differs: " + name)
        if len(rows) != group["rows"]:
            raise ValueError("Changed normalized row count")
        counts[name] = len(rows)
    expected = {"spot", "perp", "mark", "funding", "delivery"} | {
        symbol + "_" + kind for symbol in manifest["contracts"] for kind in ("trade", "mark")
    }
    if set(counts) != expected or len(manifest["contracts"]) != 12:
        raise ValueError("Incomplete registered group universe")
    result = {
        "status": "PASS",
        "raw_sources": len(raw),
        "groups": counts,
        "production_normalizer_imported": False,
        "stdlib_only": True,
        "author_independence": False,
        "source_independence": False,
        "meaning": "Separate parser/normalizer implementation by the same assistant; not external or economic validation.",
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data, args.output)
    print(
        json.dumps(
            {
                "status": result["status"],
                "raw_sources": result["raw_sources"],
                "groups": len(result["groups"]),
            }
        )
    )
