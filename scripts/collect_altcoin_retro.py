"""Expand archived historical symbol coverage without present-survivor filtering."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from scripts.collect_altcoin_analogs import Acquisition
from scripts.prepare_altcoin_payoff import is_known_leveraged_symbol

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/altcoin_retro_20260907"


def symbols_for(catalog: list[str], excluded: set[str]) -> list[str]:
    excluded = (set(excluded) | {"RLUSD"}) - {"BTC"}
    return sorted(
        {
            s
            for s in catalog
            if s.endswith("USDT") and s[:-4] not in excluded and not is_known_leveraged_symbol(s)
        }
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-data-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    protocol_path = EVIDENCE / "protocol.json"
    protocol = json.loads(protocol_path.read_text())
    base = json.loads((args.base_data_dir / "acquisition.json").read_text())
    original = json.loads(
        (ROOT / "docs/evidence/altcoin_analogs_20260907/protocol.json").read_text()
    )
    selected = symbols_for(base["catalog"], set(original["data"]["exclude_bases"]))
    acquisition = Acquisition(args.data_dir)
    copied = []
    # Reuse exact bytes and their original actual known_at, never rewrite them as new observations.
    for path in (args.base_data_dir / "raw").glob("*"):
        target = args.data_dir / "raw" / path.name
        if not target.exists():
            shutil.copyfile(path, target)
    for symbol in selected:
        path = args.base_data_dir / "pairs" / f"{symbol}.json.gz"
        target = args.data_dir / "pairs" / path.name
        if path.exists():
            if not target.exists():
                shutil.copyfile(path, target)
            if target.read_bytes() != path.read_bytes():
                raise ValueError("frozen cached history changed")
            copied.append(symbol)
    manifest = {
        "id": protocol["id"],
        "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "base_catalog_sha256": hashlib.sha256(
            (args.base_data_dir / "acquisition.json").read_bytes()
        ).hexdigest(),
        "selected": selected,
        "reused_pair_symbols": copied,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "pairs": [],
        "errors": [],
    }
    start = int(datetime(2020, 10, 1, tzinfo=UTC).timestamp() * 1000)
    end = int(datetime(2026, 9, 7, tzinfo=UTC).timestamp() * 1000)
    path = args.data_dir / "acquisition.json"
    print(
        f"Historical catalog: {len(selected)} symbols; {len(copied)} cached histories reused.",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(acquisition.pair, s, start, end): s for s in selected}
        for i, future in enumerate(as_completed(futures), 1):
            symbol = futures[future]
            try:
                row = future.result()
                payload = args.data_dir / "pairs" / f"{symbol}.json.gz"
                row["normalized_sha256"] = hashlib.sha256(payload.read_bytes()).hexdigest()
                manifest["pairs"].append(row)
            except Exception as error:
                manifest["errors"].append({"symbol": symbol, "error": str(error)})
                print(f"ERROR {symbol}: {error}", flush=True)
            if i % 40 == 0 or i == len(selected):
                path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                print(
                    f"Completed {i}/{len(selected)}; errors={len(manifest['errors'])}", flush=True
                )
    acquisition.client.close()
    manifest["pairs"].sort(key=lambda x: x["symbol"])
    manifest["completed_at_utc"] = datetime.now(UTC).isoformat()
    manifest["total_rows"] = sum(p["rows"] for p in manifest["pairs"])
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if manifest["errors"]:
        raise SystemExit(
            "Acquisition incomplete: repair transport, do not silently narrow the universe"
        )
    # Parse every saved normalized file once before evaluation.
    for p in manifest["pairs"]:
        json.loads(
            gzip.decompress((args.data_dir / "pairs" / f"{p['symbol']}.json.gz").read_bytes())
        )
    print(json.dumps({"symbols": len(selected), "rows": manifest["total_rows"]}), flush=True)


if __name__ == "__main__":
    main()
