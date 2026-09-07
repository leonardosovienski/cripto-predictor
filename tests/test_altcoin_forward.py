"""Causal, accounting and interruption controls for the isolated observer."""

import argparse
import copy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from scripts import observe_altcoin_forward as f

BOOK = {"bids": [["99", "100"], ["98", "100"]], "asks": [["101", "5"], ["102", "100"]]}


def test_depth_cost_and_size_are_accounted():
    mark = f.buy_mark(BOOK, 1010)
    assert Decimal(mark["gross_quantity"]) == Decimal(5) + Decimal(505) / 102
    assert float(mark["ask_vwap"]) > 101
    assert f.sell_mark(BOOK, "110") == 100 * 99 + 10 * 98
    assert mark["spread_bps"] == 200
    assert Decimal(mark["quantity_after_assumed_fee_and_extra_slippage"]["10"]) < Decimal(
        mark["gross_quantity"]
    )


def test_insufficient_depth_is_not_a_fill():
    with pytest.raises(ValueError, match="insufficient"):
        f.buy_mark(BOOK, 999999)
    with pytest.raises(ValueError, match="insufficient"):
        f.sell_mark(BOOK, "999999")


@pytest.mark.parametrize("change", ["crossed", "duplicate", "negative"])
def test_invalid_books_fail_closed(change):
    book = copy.deepcopy(BOOK)
    if change == "crossed":
        book["bids"][0][0] = "105"
    elif change == "duplicate":
        book["asks"][1][0] = "101"
    else:
        book["asks"][0][1] = "-1"
    with pytest.raises(ValueError):
        f.buy_mark(book, 1000)


def test_missing_position_keeps_its_weight():
    holdings = [{"symbol": "AUSDT", "weight": 0.2, "factors": None}]
    result = f.aggregate(holdings, 0.8)
    assert result["status"] == "CENSORED"
    assert all(x is None for x in result["net_return_by_extra_slippage_bps"].values())
    assert result["realized_pnl"] is None
    with pytest.raises(ValueError, match="weights"):
        f.aggregate(holdings, 1)
    assert f.aggregate([], 1)["net_return_by_extra_slippage_bps"]["0"] == 0


def test_ledger_durability_duplicate_and_tamper_detection(tmp_path):
    path = tmp_path / "ledger.jsonl"
    log = f.Ledger(path)
    log.append("DECISION", "slot", {"selected": ["A"]})
    log.append("ENTRY_MARKS", "slot", {"price": 1})
    assert len(f.Ledger(path).rows) == 2
    with pytest.raises(ValueError, match="duplicate"):
        log.append("DECISION", "slot", {})
    path.write_text(path.read_text().replace('"price":1', '"price":2'))
    with pytest.raises(ValueError, match="chain"):
        f.Ledger(path)


def test_single_writer(tmp_path):
    with f.exclusive(tmp_path):
        with pytest.raises(FileExistsError):
            with f.exclusive(tmp_path):
                pytest.fail("second writer entered")
    assert not (tmp_path / "observer.lock").exists()


def rows_for(anchor):
    start = int((anchor - timedelta(days=91)).timestamp() * 1000)
    return [
        [
            start + i * f.DAY_MS,
            "100",
            "102",
            "99",
            "101",
            "100000",
            start + (i + 1) * f.DAY_MS - 1,
            "10000000",
        ]
        for i in range(90)
    ]


def test_exact_90_day_delay_and_future_exclusion():
    anchor = datetime(2026, 9, 14, tzinfo=UTC)
    rows = rows_for(anchor)
    bars = f.normalize_window(rows, anchor)
    assert bars.shape == (92, 6)
    result = f.extract_features(bars, bars, 91)
    assert result is not None
    first = result[0]
    bars[90:] = 999999
    result = f.extract_features(bars, bars, 91)
    assert result is not None
    assert np.array_equal(first, result[0])
    with pytest.raises(ValueError):
        f.normalize_window(rows[1:], anchor)
    with pytest.raises(ValueError):
        f.normalize_window(rows + [rows[-1]], anchor)
    rows[0][0] += f.DAY_MS
    with pytest.raises(ValueError):
        f.normalize_window(rows, anchor)


def test_window_cannot_backdate_and_timezone_is_utc():
    anchor = datetime(2026, 9, 14, tzinfo=UTC)
    assert not f.in_window(anchor - timedelta(microseconds=1), anchor)
    assert f.in_window(anchor + timedelta(minutes=59), anchor)
    assert not f.in_window(anchor + timedelta(hours=1), anchor)
    assert f.anchor_for(anchor + timedelta(days=3)) == anchor


def test_live_investability_and_real_token_names():
    symbol = {
        "symbol": "JUPUSDT",
        "baseAsset": "JUP",
        "quoteAsset": "USDT",
        "status": "TRADING",
        "isSpotTradingAllowed": True,
    }
    assert f.eligibility(symbol, {"JUPUSDT"}, {"RLUSD"})
    symbol["status"] = "BREAK"
    assert not f.eligibility(symbol, {"JUPUSDT"}, set())
    symbol.update(symbol="RLUSDUSDT", baseAsset="RLUSD", status="TRADING")
    assert not f.eligibility(symbol, {"RLUSDUSDT"}, {"RLUSD"})


def test_public_source_rejects_account_and_order_routes(tmp_path):
    source = f.PublicSource(tmp_path)
    try:
        for endpoint in ("order", "account/commission", "https://example.com"):
            with pytest.raises(ValueError, match="allowlist"):
                source.get(endpoint)
    finally:
        source.close()


def setup_tick(tmp_path, monkeypatch, instant):
    args = argparse.Namespace(
        mode="tick",
        base_data_dir=tmp_path,
        training=tmp_path / "unused",
        data_dir=tmp_path / "data",
    )
    clock = [instant]
    monkeypatch.setattr(f, "now", lambda: clock[0])
    monkeypatch.setattr(f, "verify_freeze", lambda *_: "frozen")
    snap = {
        "ranked": [{"symbol": "AUSDT"}],
        "selected": ["AUSDT"],
        "cash_weight": 0.8,
        "minimum_universe_met": True,
        "sample_status": {"AUSDT": "TRADING"},
    }
    monkeypatch.setattr(f, "snapshot", lambda *_: snap)

    class Source:
        def __init__(self, *_):
            pass

        def get(self, endpoint, params):
            # Every quote must follow an already committed prospective decision.
            log = f.Ledger(args.data_dir / "ledger.jsonl")
            assert any(
                r["kind"] == "DECISION" and r["payload"].get("prospective") for r in log.rows
            )
            return BOOK, {"known_at": clock[0].isoformat(), "elapsed_ms": 1}

        def close(self):
            pass

    monkeypatch.setattr(f, "PublicSource", Source)
    return args, clock


def test_causal_round_trip_idempotency_and_cost_stress(tmp_path, monkeypatch):
    args, clock = setup_tick(tmp_path, monkeypatch, datetime(2026, 9, 14, 0, 10, tzinfo=UTC))
    f.run(args)
    f.run(args)
    log = f.Ledger(args.data_dir / "ledger.jsonl")
    assert [r["kind"] for r in log.rows] == ["DECISION", "ENTRY_MARKS"]
    clock[0] += timedelta(days=7)
    f.run(args)
    log = f.Ledger(args.data_dir / "ledger.jsonl")
    outcome = next(r for r in log.rows if r["kind"] == "OUTCOME")
    returns = outcome["payload"]["portfolios"]["payoff"]["net_return_by_extra_slippage_bps"]
    assert returns["90"] < returns["10"] < returns["0"] < 0
    assert outcome["payload"]["realized_pnl"] is None
    assert sum(r["kind"] == "DECISION" for r in log.rows) == 2


def test_missed_exit_censored_and_missed_entry_not_backfilled(tmp_path, monkeypatch):
    args, clock = setup_tick(tmp_path, monkeypatch, datetime(2026, 9, 14, 0, 10, tzinfo=UTC))
    f.run(args)
    clock[0] += timedelta(days=7, hours=2)
    f.run(args)
    log = f.Ledger(args.data_dir / "ledger.jsonl")
    outcome = next(r for r in log.rows if r["kind"] == "OUTCOME")
    assert outcome["payload"]["portfolios"]["payoff"]["status"] == "CENSORED"
    assert log.rows[-1]["payload"]["status"] == "MISSED_ENTRY"


def test_crash_after_decision_cannot_restart_as_new_entry(tmp_path, monkeypatch):
    args, _ = setup_tick(tmp_path, monkeypatch, datetime(2026, 9, 14, 0, 10, tzinfo=UTC))
    log = f.Ledger(args.data_dir / "ledger.jsonl")
    slot = datetime(2026, 9, 14, tzinfo=UTC).isoformat()
    log.append("DECISION", slot, {"status": "RECORDED_BEFORE_QUOTES", "prospective": True})
    f.run(args)
    assert [r["kind"] for r in f.Ledger(log.path).rows] == ["DECISION", "ENTRY_INTERRUPTED"]


def test_acquisition_failure_is_recorded_not_silently_dropped(tmp_path, monkeypatch):
    args, _ = setup_tick(tmp_path, monkeypatch, datetime(2026, 9, 14, 0, 10, tzinfo=UTC))

    def failed(*_):
        raise ValueError("acquisition failure")

    monkeypatch.setattr(f, "snapshot", failed)
    with pytest.raises(ValueError):
        f.run(args)
    row = f.Ledger(args.data_dir / "ledger.jsonl").rows[0]
    assert row["payload"]["status"] == "ACQUISITION_FAILED"
    assert row["payload"]["prospective"] is False


def test_catalog_diff_preserves_suspension_and_removal():
    changes = f.catalog_changes(
        {"A": "TRADING", "B": "TRADING", "C": "BREAK"}, {"A": "BREAK", "C": "BREAK", "D": "TRADING"}
    )
    assert changes == [
        {"symbol": "A", "previous": "TRADING", "current": "BREAK"},
        {"symbol": "B", "previous": "TRADING", "current": "MISSING"},
        {"symbol": "D", "previous": "MISSING", "current": "TRADING"},
    ]
