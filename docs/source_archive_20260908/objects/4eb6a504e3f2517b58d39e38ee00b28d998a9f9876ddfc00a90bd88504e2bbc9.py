from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from scripts import observe_carry_forward as observer
from scripts.carry_forward_math import HOUR, observations, opening, valuation
from scripts.research_io import Ledger, strict_json

START = datetime(2026, 9, 9, tzinfo=UTC)
ZERO = dict(
    spot_bps=0,
    future_bps=0,
    extra_slippage_bps=0,
    annual_overhead_usdt=0,
    positive_funding_multiplier=1,
    entry_mismatch_fraction=0,
)


def protocol():
    p = strict_json(
        (
            Path(__file__).resolve().parents[1]
            / "docs/evidence/carry_forward_20260908/protocol.json"
        ).read_bytes()
    )
    p["end"] = (START + timedelta(days=2)).isoformat()
    return p


def snapshot(instant):
    return {
        "spot": {"asks": [["100", "100"]], "bids": [["99.9", "100"]]},
        "future": {"asks": [["102.1", "100"]], "bids": [["102", "100"]]},
        "sf": dict(step="0.001", min_qty=0.001, max_qty=1000, min_notional=5, status="TRADING"),
        "ff": dict(step="0.001", min_qty=0.001, max_qty=1000, min_notional=5, status="TRADING"),
        "base_commission_precision": 8,
        "quote_ns": int(instant.timestamp()) * 1_000_000_000,
        "sources": [],
    }


def history(start, end, rate="0"):
    first = start // HOUR * HOUR
    due = ((first + HOUR + 8 * HOUR - 1) // (8 * HOUR)) * 8 * HOUR
    fund = [
        {"symbol": "BTCUSDT", "fundingTime": t, "fundingRate": rate, "markPrice": "100"}
        for t in range(due, end, 8 * HOUR)
    ]
    bars = [
        [t, "102", "103", "101", "102", "0", t + HOUR - 1, "0"]
        for t in range(first, end // HOUR * HOUR, HOUR)
    ]
    return fund, bars


@pytest.mark.parametrize("price", [60, 140])
def test_equal_quantity_cancels_direction_and_costs_reconcile(price):
    p = protocol()
    p["costs"] = {"zero": ZERO}
    first = snapshot(START + timedelta(minutes=15))
    entry = opening(first, p)
    last = snapshot(START + timedelta(days=1, minutes=15))
    last["spot"]["bids"] = [[str(price), "100"]]
    last["spot"]["asks"] = [[str(price + 0.1), "100"]]
    last["future"]["asks"] = [[str(price + 2), "100"]]
    last["future"]["bids"] = [[str(price + 1.9), "100"]]
    fund, bars = history(entry["entry_ms"], last["quote_ns"] // 1_000_000)
    result = valuation(entry, last, fund, bars, p)
    assert Decimal(result["cases"]["zero"]["modeled_liquidation_profit_usdt"]) == 0
    assert result["real_profit_usdt"] is None


def test_stress_preserves_negative_funding_and_reduces_positive_only():
    p = protocol()
    first = snapshot(START + timedelta(minutes=15))
    entry = opening(first, p)
    last = snapshot(START + timedelta(days=1, minutes=15))
    fund, bars = history(entry["entry_ms"], last["quote_ns"] // 1_000_000, ".001")
    fund[0]["fundingRate"] = "-.001"
    result = valuation(entry, last, fund, bars, p)["cases"]
    assert Decimal(result["base"]["funding_usdt"]) == Decimal("1.25")
    assert Decimal(result["stress"]["funding_usdt"]) == 0
    assert Decimal(result["adverse"]["modeled_liquidation_profit_usdt"]) < Decimal(
        result["base"]["modeled_liquidation_profit_usdt"]
    )


@pytest.mark.parametrize(
    "failure", ["missing_fund", "duplicate_fund", "missing_mark", "duplicate_mark", "invalid_mark"]
)
def test_unknown_or_duplicate_history_never_becomes_zero_profit(failure):
    begin = int((START + timedelta(minutes=15)).timestamp() * 1000)
    end = begin + 24 * HOUR
    fund, bars = history(begin, end)
    if failure == "missing_fund":
        fund.pop()
    elif failure == "duplicate_fund":
        fund.append(fund[0])
    elif failure == "missing_mark":
        bars.pop()
    elif failure == "duplicate_mark":
        bars.append(bars[0])
    else:
        bars[0][2] = "NaN"
    with pytest.raises(ValueError):
        observations(fund, bars, begin, end)


class Source:
    records = []


def test_decision_is_durable_before_entry_quote_and_tick_is_idempotent(tmp_path, monkeypatch):
    instant = START + timedelta(minutes=15)
    calls = []

    def capture(_):
        assert Ledger(tmp_path / "ledger.jsonl").find("DECISION", "position")
        calls.append(1)
        return snapshot(instant)

    monkeypatch.setattr(observer, "capture", capture)
    first = observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: instant)
    second = observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: instant)
    assert len(calls) == 1 and first["entry_observed"] and second["entry_observed"]


def test_interrupted_entry_is_not_retried_with_later_quote(tmp_path, monkeypatch):
    instant = START + timedelta(minutes=15)

    def fail(_):
        raise ValueError("unavailable quote")

    monkeypatch.setattr(observer, "capture", fail)
    with pytest.raises(ValueError):
        observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: instant)
    result = observer.run(
        tmp_path, protocol(), "fixed", Source(), clock=lambda: instant + timedelta(minutes=1)
    )
    assert result["phase"] == "ENTRY_INTERRUPTED" and result["real_profit_usdt"] is None


def test_missed_entry_is_durable_and_cannot_be_backdated(tmp_path):
    result = observer.run(
        tmp_path, protocol(), "fixed", Source(), clock=lambda: START + timedelta(hours=2)
    )
    assert result["phase"] == "MISSED_ENTRY" and not result["entry_observed"]
    with pytest.raises(ValueError, match="clock"):
        observer.run(
            tmp_path, protocol(), "fixed", Source(), clock=lambda: START + timedelta(minutes=15)
        )


def test_late_entry_quote_is_censored(tmp_path, monkeypatch):
    monkeypatch.setattr(observer, "capture", lambda _: snapshot(START + timedelta(hours=2)))
    with pytest.raises(ValueError, match="window"):
        observer.run(
            tmp_path, protocol(), "fixed", Source(), clock=lambda: START + timedelta(minutes=59)
        )
    assert Ledger(tmp_path / "ledger.jsonl").find("ENTRY", "position") is None


def test_synthetic_lifecycle_keeps_missing_days_visible_and_closes_once(tmp_path, monkeypatch):
    moment = [START + timedelta(minutes=15)]
    monkeypatch.setattr(observer, "capture", lambda _: snapshot(moment[0]))
    monkeypatch.setattr(observer, "history", lambda _, a, b: history(a, b))
    observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    moment[0] = START + timedelta(days=2, minutes=15)
    result = observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    assert result["phase"] == "COMPLETED" and result["exit_observed"]
    assert (START + timedelta(days=1)).date().isoformat() in result["missing_quote_slots"]
    count = result["ledger_rows"]
    assert (
        observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])[
            "ledger_rows"
        ]
        == count
    )


def test_preflight_cannot_be_counted_as_prospective_entry(tmp_path, monkeypatch):
    moment = START - timedelta(days=1)
    monkeypatch.setattr(observer, "capture", lambda _: snapshot(moment))
    result = observer.run(
        tmp_path, protocol(), "fixed", Source(), mode="preflight", clock=lambda: moment
    )
    assert (
        result["phase"] == "WAITING"
        and not result["entry_observed"]
        and result["latest_value"] is None
    )


def test_modified_freeze_cannot_continue_existing_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(observer, "capture", lambda _: snapshot(START + timedelta(minutes=15)))
    observer.run(
        tmp_path, protocol(), "fixed", Source(), clock=lambda: START + timedelta(minutes=15)
    )
    with pytest.raises(ValueError, match="freeze"):
        observer.run(
            tmp_path, protocol(), "changed", Source(), clock=lambda: START + timedelta(minutes=16)
        )


def test_exit_interruption_is_terminal_and_retains_error(tmp_path, monkeypatch):
    moment = [START + timedelta(minutes=15)]
    monkeypatch.setattr(observer, "capture", lambda _: snapshot(moment[0]))
    observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    moment[0] += timedelta(days=2)

    def failed_history(*_):
        raise ValueError("missing settlement")

    monkeypatch.setattr(observer, "history", failed_history)
    with pytest.raises(ValueError):
        observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    result = observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    assert result["phase"] == "EXIT_INTERRUPTED"
    assert result["final_value"] is None and "missing settlement" in result["error"]


def test_daily_failure_is_not_retried_or_erased(tmp_path, monkeypatch):
    moment = [START + timedelta(minutes=15)]
    monkeypatch.setattr(observer, "capture", lambda _: snapshot(moment[0]))
    observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    moment[0] += timedelta(days=1)
    calls = []

    def fail(_):
        calls.append(1)
        raise ValueError("no quote")

    monkeypatch.setattr(observer, "capture", fail)
    with pytest.raises(ValueError):
        observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    result = observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    assert len(calls) == 1 and result["error"]
    moment[0] += timedelta(hours=1)
    result = observer.run(tmp_path, protocol(), "fixed", Source(), clock=lambda: moment[0])
    assert moment[0].date().isoformat() in result["missing_quote_slots"]


def test_changed_exit_lot_and_margin_failure_are_visible():
    p = protocol()
    entry = opening(snapshot(START + timedelta(minutes=15)), p)
    last = snapshot(START + timedelta(days=1, minutes=15))
    fund, bars = history(entry["entry_ms"], last["quote_ns"] // 1_000_000)
    last["ff"]["step"] = "0.003"
    with pytest.raises(ValueError, match="lot"):
        valuation(entry, last, fund, bars, p)
    last["ff"]["step"] = "0.001"
    bars[0][2] = "10000"
    result = valuation(entry, last, fund, bars, p)
    assert all(c["margin_breaches"] for c in result["cases"].values())
    assert result["real_profit_usdt"] is None
