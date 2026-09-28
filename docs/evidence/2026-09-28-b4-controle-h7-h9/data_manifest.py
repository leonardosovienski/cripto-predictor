"""Controle do H7/H9 (B4 item 7): manifesto dos dados reconstruídos (sem versionar os dados).

Lista cada CSV usado (linhas, primeiro/último instante, sha256) e cada arquivo do data.binance.vision no cache
verificado (caminho relativo, bytes, sha256; cada zip foi conferido contra o .CHECKSUM publicado pelo importador).
Uso: python data_manifest.py <data_dir/v3/BTCUSDT> <cache verified_v2> <data_manifest.json>
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

TIME_COLUMN = {
    "funding.csv": "funding_time_ms",
    "oi.csv": "timestamp_ms",
    "spot_binance_1h.csv": "open_ms",
    "spot_1h.csv": "open_ms",
}


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def main() -> int:
    data, cache, dest = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    csvs = {}
    for name, column in TIME_COLUMN.items():
        path = data / name
        with path.open(encoding="utf-8-sig", newline="") as f:
            times = [int(row[column]) for row in csv.DictReader(f)]
        csvs[name] = {
            "rows": len(times),
            "first": iso(min(times)),
            "last": iso(max(times)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    archives = []
    for path in sorted(cache.rglob("*.zip")):
        raw = path.read_bytes()
        checksum = path.with_suffix(path.suffix + ".CHECKSUM")
        published = (
            checksum.read_text(encoding="utf-8").split()[0].lower() if checksum.exists() else None
        )
        digest = hashlib.sha256(raw).hexdigest()
        archives.append(
            {
                "file": path.relative_to(cache).as_posix(),
                "bytes": len(raw),
                "sha256": digest,
                "checksum_ok": published == digest,
            }
        )
    kinds = {}
    for a in archives:
        kind = (
            "fundingRate"
            if "fundingRate" in a["file"]
            else "metrics"
            if "metrics" in a["file"]
            else "klines"
        )
        kinds[kind] = kinds.get(kind, 0) + 1
    doc = {
        "schema": "cripto-b4-control-data/1",
        "source": "data.binance.vision (vision_ingest do domínio)",
        "csv": csvs,
        "archives_by_kind": kinds,
        "archives_checksum_ok": all(a["checksum_ok"] for a in archives),
        "archives": archives,
    }
    dest.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: doc[k] for k in ("csv", "archives_by_kind", "archives_checksum_ok")},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
