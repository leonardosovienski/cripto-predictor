"""Bounded, read-only forward observation. No exchange account or order API.

Decision is durable before entry quotes. Marks are hypothetical, not fills.
Missing observations stay censored. The original strategy and evidence are intact.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import numpy as np

from scripts.collect_altcoin_analogs import time_ms
from scripts.prepare_altcoin_payoff import is_known_leveraged_symbol, payoff_summary
from scripts.research_altcoin_analogs import AnalogModel, extract_features

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/altcoin_forward_20260907"
API = "https://data-api.binance.vision/api/v3/"
CMS = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
DAY_MS = 86_400_000
SLIPS = (0, 10, 40, 90)


def now() -> datetime:
    return datetime.now(UTC)


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


@contextmanager
def exclusive(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / "observer.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, encoded({"pid": os.getpid(), "known_at": now().isoformat()}))
        os.fsync(fd)
        yield
    finally:
        os.close(fd)
        lock.unlink()


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.rows: list[dict] = []
        previous = "0" * 64
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                digest = row.pop("sha256")
                if row["previous_sha256"] != previous or sha(encoded(row)) != digest:
                    raise ValueError("ledger chain damaged; do not repair by dropping observations")
                if row["sequence"] != len(self.rows):
                    raise ValueError("ledger sequence mismatch")
                row["sha256"] = digest
                self.rows.append(row)
                previous = digest

    def append(self, kind: str, slot: str, payload: dict) -> dict:
        if any(r["kind"] == kind and r["slot"] == slot for r in self.rows):
            raise ValueError("duplicate observation event")
        row = {
            "sequence": len(self.rows),
            "kind": kind,
            "slot": slot,
            "known_at": now().isoformat(),
            "previous_sha256": self.rows[-1]["sha256"] if self.rows else "0" * 64,
            "payload": payload,
        }
        row["sha256"] = sha(encoded(row))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as stream:
            stream.write(encoded(row) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.rows.append(row)
        return row

    def find(self, kind: str, slot: str):
        return next((r for r in self.rows if r["kind"] == kind and r["slot"] == slot), None)


class PublicSource:
    def __init__(self, directory: Path):
        self.directory = directory / "raw"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=20, follow_redirects=False)

    def get(self, endpoint: str, params: dict | None = None) -> tuple[dict | list, dict]:
        if endpoint not in {"time", "exchangeInfo", "klines", "depth", "cms"}:
            raise ValueError("endpoint outside public read-only allowlist")
        started = now()
        timer = time.perf_counter()
        response = self.client.get(CMS if endpoint == "cms" else API + endpoint, params=params)
        received = now()
        key = uuid.uuid4().hex
        meta = {
            "url": str(response.request.url),
            "requested_at": started.isoformat(),
            "known_at": received.isoformat(),
            "elapsed_ms": (time.perf_counter() - timer) * 1000,
            "status": response.status_code,
            "sha256": sha(response.content),
            "raw_file": f"raw/{key}.bin.gz",
        }
        (self.directory / f"{key}.bin.gz").write_bytes(gzip.compress(response.content, mtime=0))
        write_json(self.directory / f"{key}.json", meta)
        response.raise_for_status()
        return response.json(), meta

    def close(self):
        self.client.close()


def anchor_for(instant: datetime) -> datetime:
    day = instant.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


def in_window(instant: datetime, anchor: datetime) -> bool:
    return anchor <= instant < anchor + timedelta(hours=1)


def eligibility(symbol: dict, sampled: set[str], excluded: set[str]) -> bool:
    return (
        symbol["symbol"] in sampled
        and symbol["quoteAsset"] == "USDT"
        and symbol["baseAsset"] not in excluded
        and not is_known_leveraged_symbol(symbol["symbol"])
        and symbol["status"] == "TRADING"
        and symbol.get("isSpotTradingAllowed") is True
    )


def normalize_window(rows: list, anchor: datetime) -> np.ndarray:
    """Fail if missing, duplicate, revised into invalid OHLC, or future bars leak in."""
    start = int((anchor - timedelta(days=91)).timestamp() * 1000)
    expected = list(range(start, start + 90 * DAY_MS, DAY_MS))
    if [time_ms(r[0]) for r in rows] != expected:
        raise ValueError("incomplete, duplicate or out-of-window candle history")
    window = []
    for row, open_ms in zip(rows, expected, strict=True):
        if time_ms(row[6]) != open_ms + DAY_MS - 1:
            raise ValueError("invalid candle close time")
        o, h, low, c, v, q = [float(row[i]) for i in (1, 2, 3, 4, 5, 7)]
        if not all(math.isfinite(x) and x > 0 for x in (o, h, low, c, v, q)):
            raise ValueError("nonpositive/incomplete candle")
        if h < max(o, c) or low > min(o, c) or low > h:
            raise ValueError("inconsistent OHLC")
        window.append([o, h, low, c, v, q])
    return np.vstack((window, np.full((2, 6), np.nan)))


def levels(book: dict) -> tuple[list, list]:
    sides = []
    for key, descending in (("bids", True), ("asks", False)):
        rows = [(Decimal(p), Decimal(q)) for p, q in book[key]]
        if not rows or any(not x.is_finite() or x <= 0 for row in rows for x in row):
            raise ValueError("invalid/empty order book")
        prices = [p for p, _ in rows]
        if prices != sorted(set(prices), reverse=descending):
            raise ValueError("book levels not strictly sorted")
        sides.append(rows)
    bids, asks = sides
    if bids[0][0] >= asks[0][0]:
        raise ValueError("crossed/locked order book")
    return bids, asks


def buy_mark(book: dict, notional: float) -> dict:
    bids, asks = levels(book)
    remaining = Decimal(str(notional))
    if not remaining.is_finite() or remaining <= 0:
        raise ValueError("invalid notional")
    quantity = Decimal(0)
    for price, available in asks:
        spent = min(remaining, price * available)
        quantity += spent / price
        remaining -= spent
        if remaining == 0:
            break
    if remaining > Decimal("0.00000001"):
        raise ValueError("insufficient displayed ask depth")
    vwap = Decimal(str(notional)) / quantity
    mid = (bids[0][0] + asks[0][0]) / 2
    return {
        "notional_usdt": notional,
        "gross_quantity": str(quantity),
        "ask_vwap": str(vwap),
        "spread_bps": float((asks[0][0] - bids[0][0]) / mid * 10000),
        "buy_impact_from_best_ask_bps": float((vwap / asks[0][0] - 1) * 10000),
        "buy_cost_from_mid_bps": float((vwap / mid - 1) * 10000),
        "quantity_after_assumed_fee_and_extra_slippage": {
            str(slip): str(quantity * Decimal("0.999") * (1 - Decimal(slip) / 10000))
            for slip in SLIPS
        },
    }


def sell_mark(book: dict, quantity: str) -> Decimal:
    bids, _ = levels(book)
    remaining = Decimal(quantity)
    if not remaining.is_finite() or remaining <= 0:
        raise ValueError("invalid quantity")
    value = Decimal(0)
    for price, available in bids:
        size = min(remaining, available)
        value += price * size
        remaining -= size
        if remaining == 0:
            break
    if remaining > Decimal("0.000000000000000001"):
        raise ValueError("insufficient displayed bid depth")
    return value


def aggregate(positions: list[dict], cash_weight: float) -> dict:
    weight = cash_weight + sum(p["weight"] for p in positions)
    if not math.isclose(weight, 1, abs_tol=1e-9):
        raise ValueError("portfolio weights do not sum to one")
    missing = [p["symbol"] for p in positions if p.get("factors") is None]
    return {
        "status": "CENSORED" if missing else "HYPOTHETICAL_MARKS_COMPLETE",
        "missing_symbols": missing,
        "net_return_by_extra_slippage_bps": {
            str(slip): None
            if missing
            else cash_weight + sum(p["weight"] * p["factors"][str(slip)] for p in positions) - 1
            for slip in SLIPS
        },
        "realized_pnl": None,
    }


def event_catalog(source: PublicSource, catalog_id: int) -> dict:
    def page(number):
        data, meta = source.get(
            "cms", {"type": 1, "pageNo": number, "pageSize": 50, "catalogId": catalog_id}
        )
        if not isinstance(data, dict) or data.get("code") != "000000":
            raise ValueError("announcement service unavailable")
        catalog = next(c for c in data["data"]["catalogs"] if c["catalogId"] == catalog_id)
        return catalog, meta

    first, metadata = page(1)
    total = first["total"]
    pages = [(first, metadata)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        pages += list(pool.map(page, range(2, math.ceil(total / 50) + 1)))
    articles = {a["code"]: a for p, _ in pages for a in p["articles"]}
    return {
        "catalog_id": catalog_id,
        "reported_total": total,
        "unique_articles": len(articles),
        "pagination_count_matches": len(articles) == total
        and all(p["total"] == total for p, _ in pages),
        "sources": [meta for _, meta in pages],
        "articles": sorted(articles.values(), key=lambda a: a["releaseDate"], reverse=True),
        "complete_investability_event_feed": False,
        "limitation": "Current provider headline catalog only. Deletions, edits, other categories, full event interpretation and historical known_at are not certified.",
    }


def snapshot(source: PublicSource, anchor: datetime, base_data: Path, training: Path) -> dict:
    clock, clock_meta = source.get("time")
    if not isinstance(clock, dict):
        raise ValueError("invalid public clock response")
    midpoint = (
        datetime.fromisoformat(clock_meta["requested_at"]).timestamp()
        + datetime.fromisoformat(clock_meta["known_at"]).timestamp()
    ) / 2
    offset = clock["serverTime"] / 1000 - midpoint
    if abs(offset) > 10 or clock_meta["elapsed_ms"] > 5000:
        raise ValueError("clock offset or public API latency exceeds pilot tolerance")
    exchange, exchange_meta = source.get("exchangeInfo")
    if not isinstance(exchange, dict):
        raise ValueError("invalid exchange catalog response")
    manifest = json.loads((base_data / "acquisition.json").read_text())
    original_protocol = json.loads(
        (ROOT / "docs/evidence/altcoin_analogs_20260907/protocol.json").read_text()
    )
    excluded = set(original_protocol["data"]["exclude_bases"]) | {"RLUSD"}
    sampled = set(manifest["selected"])
    current = sorted(s["symbol"] for s in exchange["symbols"] if eligibility(s, sampled, excluded))
    statuses = {s["symbol"]: s["status"] for s in exchange["symbols"] if s["symbol"] in sampled}
    start = int((anchor - timedelta(days=91)).timestamp() * 1000)
    end = int((anchor - timedelta(days=1)).timestamp() * 1000) - 1

    def history(symbol):
        try:
            rows, metadata = source.get(
                "klines",
                {
                    "symbol": symbol,
                    "interval": "1d",
                    "startTime": start,
                    "endTime": end,
                    "limit": 100,
                },
            )
            if not isinstance(rows, list):
                raise ValueError("candle response is not a list")
            try:
                bars = normalize_window(rows, anchor)
            except ValueError as error:
                return symbol, None, metadata, str(error), False
            return symbol, bars, metadata, None, False
        except (httpx.HTTPError, ValueError, KeyError) as error:
            return symbol, None, None, str(error), True

    with ThreadPoolExecutor(max_workers=6) as pool:
        histories = list(pool.map(history, ["BTCUSDT"] + current))
    btc = histories[0][1]
    if btc is None:
        raise ValueError("BTC reference history unavailable")
    failures = [symbol for symbol, _, _, _, network_error in histories if network_error]
    if failures:
        raise ValueError(f"acquisition failures must not shrink selection universe: {failures}")
    candidates, rejected = [], []
    for symbol, bars, metadata, error, _ in histories[1:]:
        features = None if bars is None else extract_features(bars, btc, 91)
        if features is None:
            rejected.append(
                {
                    "symbol": symbol,
                    "reason": error or "below_fixed_liquidity_threshold",
                    "source": metadata,
                }
            )
        else:
            vector, volume = features
            candidates.append(
                {
                    "symbol": symbol,
                    "features": vector.tolist(),
                    "median_quote_volume_30d": volume,
                    "source": metadata,
                }
            )
    train = [
        s for s in json.loads(gzip.decompress(training.read_bytes())) if s["period"] == "train"
    ]
    if any(s["date"] >= "2024-01-01" for s in train):
        raise ValueError("future training observations")
    model = AnalogModel().fit(np.array([s["features"] for s in train]), np.zeros(len(train)))
    ranked = []
    if candidates:
        _, _, indices = model.predict(np.array([s["features"] for s in candidates]))
        for candidate, neighbors in zip(candidates, indices, strict=True):
            ranked.append({**candidate, **payoff_summary([train[int(i)] for i in neighbors])})
    ranked.sort(key=lambda s: (s["score_log"] is None, -(s["score_log"] or 0), s["symbol"]))
    qualified = [s["symbol"] for s in ranked if s["qualified"]]
    selected = qualified[:5] if len(ranked) >= 10 else []
    notices = []
    for catalog_id in (161, 49):
        try:
            notices.append(event_catalog(source, catalog_id))
        except (httpx.HTTPError, ValueError, KeyError, StopIteration) as error:
            notices.append(
                {
                    "catalog_id": catalog_id,
                    "error": str(error),
                    "complete_investability_event_feed": False,
                }
            )
    return {
        "anchor_utc": anchor.isoformat(),
        "recorded_after_acquisition": now().isoformat(),
        "clock": {"offset_seconds": offset, "source": clock_meta},
        "exchange_source": exchange_meta,
        "sample_status": statuses,
        "sample_size": len(sampled),
        "currently_trading_after_exclusions": len(current),
        "rejected": rejected,
        "btc_history_source": histories[0][2],
        "ranked": ranked,
        "qualified_symbols": qualified,
        "selected": selected,
        "cash_weight": 1 - 0.2 * len(selected),
        "minimum_universe_met": len(ranked) >= 10,
        "announcements": notices,
        "execution_ready": False,
        "promotion_ready": False,
    }


def quoted_book(source: PublicSource, symbol: str) -> tuple[dict, dict]:
    book, metadata = source.get("depth", {"symbol": symbol, "limit": 1000})
    if metadata["elapsed_ms"] > 5000:
        raise ValueError("quote request exceeded five seconds")
    if not isinstance(book, dict):
        raise ValueError("invalid quote response")
    levels(book)
    return book, metadata


def catalog_changes(previous: dict, current: dict) -> list[dict]:
    return [
        {
            "symbol": symbol,
            "previous": previous.get(symbol, "MISSING"),
            "current": current.get(symbol, "MISSING"),
        }
        for symbol in sorted(set(previous) | set(current))
        if previous.get(symbol, "MISSING") != current.get(symbol, "MISSING")
    ]


def attach_catalog_changes(snap: dict, ledger: Ledger):
    prior = next((r for r in reversed(ledger.rows) if r["payload"].get("snapshot")), None)
    if prior:
        path = Path(prior["payload"]["snapshot"])
        if sha(path.read_bytes()) != prior["payload"]["snapshot_sha256"]:
            raise ValueError("prior snapshot hash mismatch")
        previous = json.loads(path.read_text())
        snap["sample_status_changes"] = catalog_changes(
            previous["sample_status"], snap["sample_status"]
        )
        snap["compared_with_ledger_sha256"] = prior["sha256"]
    else:
        snap["sample_status_changes"] = None
        snap["compared_with_ledger_sha256"] = None


def portfolio_specs(snap: dict) -> dict:
    selected = [{"symbol": s, "weight": 0.2} for s in snap["selected"]]
    eligible = [s["symbol"] for s in snap["ranked"]] if snap["minimum_universe_met"] else []
    basket = [{"symbol": s, "weight": 1 / len(eligible)} for s in eligible]
    return {
        "payoff": {"positions": selected, "cash_weight": snap["cash_weight"]},
        "equal_basket": {"positions": basket, "cash_weight": 0 if basket else 1},
        "btc_same_weeks": {
            "positions": [{"symbol": "BTCUSDT", "weight": 1}] if eligible else [],
            "cash_weight": 0 if eligible else 1,
        },
    }


def entry_marks(source: PublicSource, portfolios: dict, anchor: datetime | None) -> dict:
    books, errors = {}, {}
    for symbol in sorted({p["symbol"] for spec in portfolios.values() for p in spec["positions"]}):
        try:
            book, meta = quoted_book(source, symbol)
            if anchor and not in_window(datetime.fromisoformat(meta["known_at"]), anchor):
                raise ValueError("entry quote outside registered window")
            books[symbol] = (book, meta)
        except (httpx.HTTPError, ValueError, KeyError) as error:
            errors[symbol] = str(error)
    result = {}
    for name, spec in portfolios.items():
        positions = []
        for p in spec["positions"]:
            symbol = p["symbol"]
            try:
                if symbol not in books:
                    raise ValueError(errors[symbol])
                book, meta = books[symbol]
                positions.append({**p, "entry": buy_mark(book, 5000 * p["weight"]), "source": meta})
            except ValueError as error:
                positions.append({**p, "entry": None, "reason": str(error)})
        result[name] = {"positions": positions, "cash_weight": spec["cash_weight"]}
    return result


def settle(source: PublicSource, entry: dict, due: datetime, missed: bool) -> dict:
    books, errors = {}, {}
    if not missed:
        for symbol in sorted(
            {p["symbol"] for spec in entry.values() for p in spec["positions"] if p["entry"]}
        ):
            try:
                book, meta = quoted_book(source, symbol)
                if not in_window(datetime.fromisoformat(meta["known_at"]), due):
                    raise ValueError("exit quote outside registered window")
                books[symbol] = (book, meta)
            except (httpx.HTTPError, ValueError, KeyError) as error:
                errors[symbol] = str(error)
    result = {}
    for name, spec in entry.items():
        positions = []
        for p in spec["positions"]:
            position = {"symbol": p["symbol"], "weight": p["weight"], "factors": None}
            try:
                if not p["entry"] or missed:
                    raise ValueError("entry missing or due window missed")
                if p["symbol"] not in books:
                    raise ValueError(errors[p["symbol"]])
                book, meta = books[p["symbol"]]
                factors = {}
                for slip, qty in p["entry"][
                    "quantity_after_assumed_fee_and_extra_slippage"
                ].items():
                    value = sell_mark(book, qty) * Decimal("0.999") * (1 - Decimal(slip) / 10000)
                    factors[slip] = float(value / Decimal(str(p["entry"]["notional_usdt"])))
                position.update({"factors": factors, "source": meta})
            except ValueError as error:
                position["reason"] = str(error)
            positions.append(position)
        result[name] = {
            "positions": positions,
            "cash_weight": spec["cash_weight"],
            **aggregate(positions, spec["cash_weight"]),
        }
    return result


def verify_freeze(base_data: Path, training: Path):
    freeze = json.loads((EVIDENCE / "freeze.json").read_text())
    paths = {
        **{str(ROOT / k): v for k, v in freeze["repository_files"].items()},
        str(base_data / "acquisition.json"): freeze["acquisition_sha256"],
        str(training): freeze["training_sha256"],
    }
    for path, digest in paths.items():
        if sha(Path(path).read_bytes()) != digest:
            raise ValueError(f"frozen input/code changed: {path}")
    return sha((EVIDENCE / "freeze.json").read_bytes())


def run(args):
    freeze_hash = verify_freeze(args.base_data_dir, args.training)
    protocol = json.loads((EVIDENCE / "protocol.json").read_text())
    with exclusive(args.data_dir):
        ledger = Ledger(args.data_dir / "ledger.jsonl")
        source = PublicSource(args.data_dir)
        try:
            if args.mode == "preflight":
                snap = snapshot(source, anchor_for(now()), args.base_data_dir, args.training)
                attach_catalog_changes(snap, ledger)
                run_id = "preflight-" + uuid.uuid4().hex
                path = args.data_dir / "snapshots" / f"{run_id}.json"
                write_json(path, snap)
                # Durable diagnostic observation before its diagnostic book requests.
                ledger.append(
                    "PREFLIGHT",
                    run_id,
                    {
                        "prospective": False,
                        "snapshot": str(path),
                        "snapshot_sha256": sha(path.read_bytes()),
                        "freeze_sha256": freeze_hash,
                    },
                )
                specs = portfolio_specs(snap)
                specs["cost_probe_1000"] = {
                    "positions": [{"symbol": s["symbol"], "weight": 0.2} for s in snap["ranked"]],
                    "cash_weight": None,
                }
                marks = entry_marks(source, specs, None)
                write_json(args.data_dir / "preflight_marks.json", marks)
                ledger.append("PREFLIGHT_QUOTES", run_id, {"marks": marks, "prospective": False})
            else:
                first = datetime.fromisoformat(protocol["start_utc"])
                last = datetime.fromisoformat(protocol["last_entry_utc"])
                slot_time = first
                while slot_time <= min(now(), last):
                    slot = slot_time.isoformat()
                    entry = ledger.find("ENTRY_MARKS", slot)
                    decision = ledger.find("DECISION", slot)
                    if entry is None and decision is None:
                        if not in_window(now(), slot_time):
                            ledger.append(
                                "DECISION", slot, {"status": "MISSED_ENTRY", "prospective": False}
                            )
                        else:
                            try:
                                snap = snapshot(
                                    source, slot_time, args.base_data_dir, args.training
                                )
                                attach_catalog_changes(snap, ledger)
                                if not in_window(now(), slot_time):
                                    raise ValueError("acquisition finished after entry window")
                                path = args.data_dir / "snapshots" / f"{slot_time.date()}.json"
                                write_json(path, snap)
                                specs = portfolio_specs(snap)
                                ledger.append(
                                    "DECISION",
                                    slot,
                                    {
                                        "status": "RECORDED_BEFORE_QUOTES",
                                        "prospective": True,
                                        "snapshot": str(path),
                                        "snapshot_sha256": sha(path.read_bytes()),
                                        "freeze_sha256": freeze_hash,
                                        "portfolios": specs,
                                    },
                                )
                                marks = entry_marks(source, specs, slot_time)
                                entry = ledger.append("ENTRY_MARKS", slot, marks)
                            except (httpx.HTTPError, ValueError, KeyError) as error:
                                if not ledger.find("DECISION", slot):
                                    ledger.append(
                                        "DECISION",
                                        slot,
                                        {
                                            "status": "ACQUISITION_FAILED",
                                            "error": str(error),
                                            "prospective": False,
                                        },
                                    )
                                raise
                    elif (
                        entry is None
                        and decision
                        and decision["payload"]["status"] == "RECORDED_BEFORE_QUOTES"
                    ):
                        # Crash after durable decision cannot create a fresh delayed pretend entry.
                        if not ledger.find("ENTRY_INTERRUPTED", slot):
                            ledger.append(
                                "ENTRY_INTERRUPTED",
                                slot,
                                {
                                    "status": "CENSORED_NO_ENTRY_MARKS",
                                    "decision_sha256": decision["sha256"],
                                },
                            )
                    due = slot_time + timedelta(days=7)
                    if entry and now() >= due and not ledger.find("OUTCOME", slot):
                        results = settle(source, entry["payload"], due, not in_window(now(), due))
                        ledger.append(
                            "OUTCOME",
                            slot,
                            {
                                "due_utc": due.isoformat(),
                                "portfolios": results,
                                "actual_holding_time": "quote timestamps recorded; anchor windows can differ by up to 60 minutes",
                                "realized_pnl": None,
                            },
                        )
                    slot_time += timedelta(days=7)
            summary = {
                "updated_at": now().isoformat(),
                "mode": args.mode,
                "ledger_rows": len(ledger.rows),
                "ledger_head": ledger.rows[-1]["sha256"] if ledger.rows else None,
                "prospective_decisions": sum(
                    r["kind"] == "DECISION" and r["payload"].get("prospective") is True
                    for r in ledger.rows
                ),
                "matured_observations": sum(r["kind"] == "OUTCOME" for r in ledger.rows),
                "first_entry_utc": protocol["start_utc"],
                "last_due_utc": protocol["last_due_utc"],
                "pilot_finished": now() >= datetime.fromisoformat(protocol["last_due_utc"])
                and all(
                    ledger.find("OUTCOME", r["slot"])
                    for r in ledger.rows
                    if r["kind"] == "ENTRY_MARKS"
                ),
                "execution_ready": False,
                "formal_promotion": False,
                "capital": False,
            }
            write_json(args.data_dir / "status.json", summary)
            print(json.dumps(summary, indent=2))
        finally:
            source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "tick"), required=True)
    parser.add_argument("--base-data-dir", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
