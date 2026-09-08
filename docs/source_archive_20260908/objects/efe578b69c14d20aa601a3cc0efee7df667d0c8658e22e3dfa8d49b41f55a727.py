"""Recovery and honest coverage/accounting, including complete inactivity."""

import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from scripts import observe_altcoin_forward as f


def protocol():
    first = datetime(2026, 9, 14, tzinfo=UTC)
    return {
        "id": "review-control",
        "start_utc": first.isoformat(),
        "last_entry_utc": (first + timedelta(weeks=11)).isoformat(),
        "last_due_utc": (first + timedelta(weeks=12)).isoformat(),
    }


def test_os_lock_is_released_after_process_exits_without_finally(tmp_path):
    code = (
        "import os, sys; from pathlib import Path; "
        "from scripts.observe_altcoin_forward import exclusive; "
        "guard = exclusive(Path(sys.argv[1])); guard.__enter__(); os._exit(0)"
    )
    subprocess.run([sys.executable, "-c", code, str(tmp_path)], check=True, cwd=f.ROOT)
    with f.exclusive(tmp_path):
        with pytest.raises(FileExistsError):
            with f.exclusive(tmp_path):
                pytest.fail("two writers acquired the lock")


def test_existing_unlocked_lock_file_is_not_a_running_process(tmp_path):
    (tmp_path / "observer.lock").write_text('{"pid":99999999}')
    with f.exclusive(tmp_path):
        assert (tmp_path / "observer.lock").exists()


def record(log, slot, net, symbols=()):
    portfolios = {
        "payoff": {
            "positions": [{"symbol": s, "weight": 0.2} for s in symbols],
            "cash_weight": 1 - 0.2 * len(symbols),
        }
    }
    log.append(
        "DECISION",
        slot,
        {"prospective": True, "status": "RECORDED_BEFORE_QUOTES", "portfolios": portfolios},
    )
    log.append("ENTRY_MARKS", slot, portfolios)
    log.append(
        "OUTCOME",
        slot,
        {
            "portfolios": {
                "payoff": {
                    "status": "CENSORED" if net is None else "HYPOTHETICAL_MARKS_COMPLETE",
                    "net_return_by_extra_slippage_bps": {str(s): net for s in f.SLIPS},
                }
            }
        },
    )


def test_no_observations_does_not_claim_zero_profit(tmp_path):
    summary = f.observation_quality(
        f.Ledger(tmp_path / "ledger.jsonl"), protocol(), datetime(2026, 9, 7, tzinfo=UTC)
    )
    assert summary["expected_slots"] == 12
    assert summary["known_due_weeks"] == 0
    assert summary["standardized_completed_week_profit_usdt"] is None
    assert summary["quality"] == "AWAITING_NEW_OBSERVATIONS"


def test_all_missed_slots_are_unknown_profit(tmp_path):
    config = protocol()
    log = f.Ledger(tmp_path / "ledger.jsonl")
    first = datetime.fromisoformat(config["start_utc"])
    for i in range(12):
        log.append(
            "DECISION",
            (first + timedelta(weeks=i)).isoformat(),
            {"status": "MISSED_ENTRY", "prospective": False},
        )
    summary = f.observation_quality(log, config, first + timedelta(weeks=12))
    assert summary["missing_due_weeks"] == 12
    assert summary["coverage_complete_for_due_weeks"] is False
    assert summary["standardized_pilot_profit_usdt"] is None
    assert summary["quality"] == "INCOMPLETE_OBSERVATIONS"


def test_cash_weeks_do_not_count_as_winning_trades(tmp_path):
    config = protocol()
    log = f.Ledger(tmp_path / "ledger.jsonl")
    first = datetime.fromisoformat(config["start_utc"])
    for i in range(12):
        record(log, (first + timedelta(weeks=i)).isoformat(), 0)
    summary = f.observation_quality(log, config, first + timedelta(weeks=12))
    assert summary["cash_due_weeks"] == 12
    assert summary["known_due_weeks"] == 12
    assert summary["selected_holdings"] == 0
    assert summary["standardized_pilot_profit_usdt"] == 0
    assert summary["quality"] == "NO_TRADING_EVIDENCE_RULE_ABSTAINS"


def test_partial_profit_does_not_erase_missing_due_week(tmp_path):
    config = protocol()
    log = f.Ledger(tmp_path / "ledger.jsonl")
    first = datetime.fromisoformat(config["start_utc"])
    record(log, first.isoformat(), 0.01, ("AUSDT",))
    record(log, (first + timedelta(weeks=1)).isoformat(), None, ("BUSDT",))
    summary = f.observation_quality(log, config, first + timedelta(weeks=2))
    assert summary["standardized_completed_week_profit_usdt"] == 50
    assert summary["missing_due_weeks"] == 1
    assert summary["standardized_pilot_profit_usdt"] is None
    assert summary["quality"] == "INCOMPLETE_OBSERVATIONS"
    assert summary["realized_profit"] is None


def test_incompatible_status_and_return_are_rejected(tmp_path):
    config = protocol()
    log = f.Ledger(tmp_path / "ledger.jsonl")
    slot = config["start_utc"]
    record(log, slot, 0.01, ("AUSDT",))
    log.rows[-1]["payload"]["portfolios"]["payoff"]["status"] = "CENSORED"
    with pytest.raises(ValueError, match="status/return"):
        f.observation_quality(log, config, datetime(2026, 9, 21, tzinfo=UTC))
