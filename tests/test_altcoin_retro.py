"""Protect causal decisions, abstention, censored weights and cost accounting."""

import copy
import gzip
import json
from datetime import date
from decimal import Decimal

import numpy as np
import pytest

from scripts import backtest_altcoin_payoff as b
from scripts.collect_altcoin_retro import symbols_for


def test_historical_catalog_does_not_remove_dead_or_suffix_named_assets():
    symbols = symbols_for(
        [
            "BTCUSDT",
            "DEADUSDT",
            "JUPUSDT",
            "SYRUPUSDT",
            "BTCUPUSDT",
            "RLUSDUSDT",
            "USDCUSDT",
            "ETHBTC",
        ],
        {"BTC", "USDC"},
    )
    assert symbols == ["BTCUSDT", "DEADUSDT", "JUPUSDT", "SYRUPUSDT"]


def test_candidate_future_returns_cannot_affect_selection():
    train = [
        {"features": [0.0] * 8, "date": f"week-{i // 5}", "gross_return": 0.03} for i in range(200)
    ]
    rows = [
        {
            "date": "2024-01-01",
            "symbol": f"COIN{i:02}USDT",
            "features": [0.0] * 8,
            "gross_return": 0.1,
        }
        for i in range(10)
    ]
    decisions, scores = b.make_decisions(train, rows, ["2024-01-01"])
    changed = copy.deepcopy(rows)
    for i, row in enumerate(changed):
        row["gross_return"] = -1 if i % 2 else 100
        row["future_price"] = 999999
    second = b.make_decisions(train, changed, ["2024-01-01"])
    assert b.blob([decisions, scores]) == b.blob(second)
    assert decisions[0]["selected"] == [f"COIN{i:02}USDT" for i in range(5)]
    assert "gross_return" not in scores[0]


def test_fixed_eligibility_minimum_does_not_force_entries():
    train = [
        {"features": [0.0] * 8, "date": f"week-{i // 5}", "gross_return": 0.03} for i in range(200)
    ]
    rows = [{"date": "2024-01-01", "symbol": str(i), "features": [0.0] * 8} for i in range(9)]
    decisions, _ = b.make_decisions(train, rows, ["2024-01-01"])
    assert decisions[0]["selected"] == []
    assert decisions[0]["selection_status"] == "INSUFFICIENT_UNIVERSE"


def test_primary_cost_factor_matches_decimal_v4_buy_and_sell_haircuts():
    expected = Decimal("1.1") * Decimal("0.999") ** 4
    assert b.cost_factor(0.1, 1, 10) == pytest.approx(float(expected), abs=1e-14)
    assert b.cost_factor(0.1, 2, 10) < b.cost_factor(0.1, 1, 10)
    assert (
        b.cost_factor(0.1, 1, 90)
        < b.cost_factor(0.1, 1, 40)
        < b.cost_factor(0.1, 1, 10)
        < b.cost_factor(0.1, 1, 0)
    )


def test_missing_outcome_retains_its_twenty_percent_allocation():
    holding = [{"gross_return": None, "sell_legs": 1}]
    assert b.portfolio_factor(holding, 10) is None
    assert b.portfolio_factor(holding, 10, "total_loss") == 0.8
    assert b.portfolio_factor(holding, 10, "flat_gross") == pytest.approx(0.8 + 0.2 * 0.999**4)
    assert b.portfolio_factor([], 10) == 1


def test_cash_is_not_a_winning_trade_or_a_meaningful_confidence_interval():
    data = {"AUSDT": np.ones(((b.END - b.BASE).days, 6))}
    weeks = b.attach_outcomes([{"date": "2024-01-01", "selected": [], "cash_weight": 1}], data, [])
    report = b.summarize(weeks)
    assert report["decision"] == "NO_TRADING_EVIDENCE_RULE_ABSTAINS"
    assert report["selected_holdings"] == 0
    assert report["trade_stats_primary"]["win_rate_among_complete"] is None
    assert report["cost_scenarios"]["10"]["ending_5000_usdt"] == 5000
    assert report["uncertainty_primary"]["interval"] is None


def test_censoring_prevents_a_fake_portfolio_profit():
    data = {"AUSDT": np.full(((b.END - b.BASE).days, 6), np.nan)}
    decisions = [{"date": "2024-01-01", "selected": ["AUSDT"], "cash_weight": 0.8}]
    weeks = b.attach_outcomes(decisions, data, [])
    report = b.summarize(weeks)
    assert report["decision"] == "INCONCLUSIVE_DATA_FIDELITY"
    assert report["cost_scenarios"]["10"]["compounded_return"] is None
    assert report["censored_selected_holdings"] == 1


def test_verified_exact_horizon_resolution_can_restore_price_proxy():
    data = {"OLDUSDT": np.full(((b.END - b.BASE).days, 6), np.nan)}
    decisions = [{"date": "2024-01-01", "selected": ["OLDUSDT"], "cash_weight": 0.8}]
    resolutions = [
        {
            "symbol": "OLDUSDT",
            "entry": "2024-01-01",
            "gross_return": 0.25,
            "sell_legs": 1,
            "status": "QUANTITY_ADJUSTED_DAILY_MARK",
            "source": "recorded official source",
        }
    ]
    weeks = b.attach_outcomes(decisions, data, resolutions)
    assert weeks[0]["holdings"][0]["gross_return"] == 0.25
    assert b.summarize(weeks)["decision"] == "POSITIVE_BUT_SPARSE"
    assert decisions[0]["selected"] == ["OLDUSDT"]


def test_training_outcome_cannot_cross_into_evaluation(tmp_path, monkeypatch):
    monkeypatch.setattr(b, "ROOT", tmp_path)
    path = tmp_path / "training.gz"
    path.write_bytes(
        gzip.compress(json.dumps([{"period": "train", "date": "2023-12-26"}]).encode())
    )
    directory = tmp_path / "docs/evidence/altcoin_profit_20260907"
    directory.mkdir(parents=True)
    (directory / "freeze.json").write_text(
        json.dumps({"training_sha256": b.digest(path.read_bytes())})
    )
    with pytest.raises(ValueError, match="crosses"):
        b.load_training(path)


def test_future_bar_perturbation_does_not_change_first_week_features():
    bars = np.tile([100, 102, 99, 101, 100000, 10000000], ((b.END - b.BASE).days, 1)).astype(float)
    idx = (date(2024, 1, 1) - b.BASE).days
    first = b.extract_features(bars, bars, idx)
    assert first is not None
    changed = bars.copy()
    changed[idx - 1 :] *= 100
    second = b.extract_features(changed, changed, idx)
    assert second is not None
    assert np.array_equal(first[0], second[0])


def test_drawdown_and_compounding_are_not_arithmetic_return_sum():
    metrics = b.wealth_metrics([1.2, 0.5, 1.1])
    assert metrics["ending_5000_usdt"] == pytest.approx(3300)
    assert metrics["max_drawdown_weekly_endpoints"] == pytest.approx(-0.5)


def test_partial_day_is_preserved_as_missing_without_dropping_symbol(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "protocol.json").write_text("{}")
    monkeypatch.setattr(b, "EVIDENCE", evidence)
    directory = tmp_path / "data"
    (directory / "pairs").mkdir(parents=True)
    first = (b.BASE - b.EPOCH).days * b.DAY
    rows = [
        [first, 100, 101, 99, 100, 100000, 10000000, first + b.DAY - 1],
        [first + b.DAY, 100, 101, 99, 100, 100000, 10000000, first + b.DAY + 3600000 - 1],
    ]
    rows.append([first + 2 * b.DAY, 100, 100, 100, 100, 0, 0, first + b.DAY - 1])
    payload = gzip.compress(json.dumps({"rows": rows}).encode())
    (directory / "pairs/BTCUSDT.json.gz").write_bytes(payload)
    manifest = {
        "protocol_sha256": b.digest((evidence / "protocol.json").read_bytes()),
        "errors": [],
        "selected": ["BTCUSDT"],
        "pairs": [{"symbol": "BTCUSDT", "normalized_sha256": b.digest(payload)}],
    }
    (directory / "acquisition.json").write_text(json.dumps(manifest))
    _, data = b.load_histories(directory)
    assert "BTCUSDT" in data
    assert np.isfinite(data["BTCUSDT"][0]).all()
    assert np.isnan(data["BTCUSDT"][1]).all()
    assert np.isnan(data["BTCUSDT"][2]).all()
