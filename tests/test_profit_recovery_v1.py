"""Engineering tests only; synthetic fixtures do not demonstrate market edge."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.profit_recovery_v1 import (
    BULL,
    Candle,
    Capturability,
    CostEvidence,
    CostModelV1,
    Decision,
    Forecast,
    Quote,
    baseline_report,
    causal_opportunity_ledger,
    default_trial,
    economic_decision,
    freeze_trial,
    load_candles_sqlite,
    money_left_on_table,
    operational_status,
    opportunity_metrics,
    oracle_opportunity_catalog,
    paper_execute_v2,
    portfolio_summary,
    run_replay,
    synthetic_control,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def candles(*, n: int = 90, jump_at: int = 60, jump: float = 0.10) -> list[Candle]:
    rows = []
    price = 100.0
    for index in range(n):
        if index == jump_at:
            price *= 1 + jump
        elif index > jump_at:
            price *= 1.004
        stamp = T0 + timedelta(days=index)
        rows.append(
            Candle(
                asset="bitcoin",
                timestamp=stamp,
                published_at=stamp + timedelta(days=1),
                open=price * 0.999,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1000 if index != jump_at else 3000,
                source="binance",
            )
        )
    return rows


def assumed_cost() -> CostModelV1:
    return CostModelV1(
        venue="binance",
        instrument="BTCUSDT spot",
        order_type="marketable",
        fee_bps_per_leg=10,
        spread_bps_round_trip=5,
        slippage_bps_round_trip=10,
        latency_bps_round_trip=2,
    )


def test_oracle_and_causal_ledgers_are_separate() -> None:
    series = candles()
    oracle = oracle_opportunity_catalog(series, horizon_days=7, move_threshold=0.05)
    causal = causal_opportunity_ledger(series, assumed_cost(), horizon_days=3)
    assert oracle and causal
    assert all(row["catalog_type"] == "ORACLE_DIAGNOSTIC" for row in oracle)
    assert all(row["used_for_training"] is False for row in oracle)
    assert all(row["ledger_type"] == "CAUSAL_OPPORTUNITY_LEDGER" for row in causal)
    assert all(row["PR122_detected"] for row in causal)
    assert all(row["capital_permission"] is False for row in causal)
    assert all(row["paper_result"] == "NOT_AVAILABLE_MISSING_QUOTES" for row in causal)


def test_causal_forecast_never_uses_unmatured_outcome() -> None:
    rows = causal_opportunity_ledger(candles(n=70), assumed_cost(), horizon_days=7)
    assert rows
    first = rows[0]
    assert first["forecast"]["sample_size"] == 0
    assert first["decision"] == Decision.WATCH.value
    assert first["capturability"] in {item.value for item in Capturability}


def test_cost_break_even_and_assumed_cost_blocks_trade() -> None:
    costs = assumed_cost()
    assert costs.round_trip_bps == 37
    assert costs.break_even_edge == pytest.approx(0.0037)
    forecast = Forecast(3, 0.05, 0.0037, 0.0463, 0.8, 0.02, 0.04, 30, "OOS")
    decision = economic_decision(forecast, candidate_time=T0, costs=costs)
    assert decision.action is Decision.WATCH
    assert "not market observed" in decision.reason
    assert decision.capital_permission is False


def test_observed_cost_and_conservative_forecast_can_only_authorize_paper_decision() -> None:
    costs = CostModelV1(
        venue="test",
        instrument="BTCUSDT spot",
        order_type="marketable",
        fee_bps_per_leg=5,
        spread_bps_round_trip=2,
        slippage_bps_round_trip=2,
        latency_bps_round_trip=1,
        evidence=CostEvidence.OBSERVED_MARKET,
    )
    forecast = Forecast(3, 0.04, 0.0015, 0.0385, 0.75, 0.01, 0.03, 30, "OOS")
    decision = economic_decision(forecast, candidate_time=T0, costs=costs)
    assert decision.action is Decision.TRADE
    assert decision.capital_permission is False


def test_realistic_paper_v2_full_and_partial_fills() -> None:
    entry = Quote(T0 + timedelta(seconds=2), 99.0, 100.0, 20.0, 20.0, CostEvidence.OBSERVED_MARKET)
    exit_quote = Quote(
        T0 + timedelta(days=3), 110.0, 111.0, 20.0, 20.0, CostEvidence.OBSERVED_MARKET
    )
    full = paper_execute_v2(
        opportunity_id="x",
        direction=BULL,
        requested_notional=1000,
        decision_timestamp=T0,
        entry=entry,
        exit=exit_quote,
        fee_bps_per_leg=10,
        latency_seconds=2,
    )
    assert full["fill_status"] == "FILLED"
    assert full["gross_pnl"] == pytest.approx(100)
    assert full["net_pnl"] < full["gross_pnl"]
    assert not full["capital_permission"]

    shallow = Quote(T0 + timedelta(seconds=2), 99.0, 100.0, 20.0, 1.0, CostEvidence.OBSERVED_MARKET)
    partial = paper_execute_v2(
        opportunity_id="x",
        direction=BULL,
        requested_notional=1000,
        decision_timestamp=T0,
        entry=shallow,
        exit=exit_quote,
        fee_bps_per_leg=10,
        latency_seconds=2,
    )
    assert partial["fill_status"] == "PARTIAL_FILL"
    assert partial["filled_size"] == 1


def test_paper_rejects_lookahead_and_crossed_quotes() -> None:
    with pytest.raises(ValueError, match="crossed"):
        Quote(T0, 101, 100, 1, 1, CostEvidence.OBSERVED_MARKET)
    entry = Quote(T0, 99, 100, 1, 1, CostEvidence.OBSERVED_MARKET)
    exit_quote = Quote(T0 + timedelta(days=1), 101, 102, 1, 1, CostEvidence.OBSERVED_MARKET)
    with pytest.raises(ValueError, match="causality"):
        paper_execute_v2(
            opportunity_id="x",
            direction=BULL,
            requested_notional=100,
            decision_timestamp=T0 + timedelta(seconds=1),
            entry=entry,
            exit=exit_quote,
            fee_bps_per_leg=10,
            latency_seconds=0,
        )


def test_portfolio_and_policy_mltt_are_net_and_oracle_separated() -> None:
    paper = [
        {
            "opportunity_id": "c1",
            "gross_pnl": 10,
            "costs": 2,
            "net_pnl": 8,
            "filled_size": 1,
            "entry_price": 100,
            "exit_price": 110,
        },
        {
            "opportunity_id": "c2",
            "gross_pnl": -5,
            "costs": 2,
            "net_pnl": -7,
            "filled_size": 1,
            "entry_price": 100,
            "exit_price": 95,
        },
    ]
    portfolio = portfolio_summary(paper, opening_cash=1000)
    assert portfolio["net_pnl"] == 1
    assert portfolio["cash"] == 1001
    assert portfolio["MaxDD"] > 0
    metrics = money_left_on_table(
        [{"oracle_mfe": 0.9}],
        [
            {"opportunity_id": "c1", "decision": "TRADE", "future_net_return": 0.1},
            {"opportunity_id": "c2", "decision": "WATCH", "future_net_return": 0.8},
        ],
        paper,
    )
    assert metrics["ORACLE_MLTT"] == 0.9
    assert metrics["CAPTURABLE_OPPORTUNITY_VALUE"] == 0.1
    assert metrics["CAPTURED_OPPORTUNITY_VALUE"] == 8
    assert metrics["POLICY_MONEY_LEFT_ON_THE_TABLE"] == 0


def test_freeze_trial_is_stable_and_requires_complete_protocol() -> None:
    spec = {
        "universe": ["BTC", "ETH", "SOL"],
        "frequency": "1d",
        "opportunity_classes": ["STRONG_MOVE", "PERSISTENT"],
        "features": ["returns", "relative_volume", "breadth"],
        "target": "future_net_return_3d",
        "model_rule": "expanding-window-v1",
        "thresholds": "PR122-frozen",
        "baseline": ["always-flat", "momentum-7d", "breakout-20d"],
        "entry": "first observed marketable quote <=5m",
        "exit": "fixed 72h",
        "cost_model": "observed-market-v1",
        "sizing": "fixed 1 percent",
        "risk": "max 3 percent gross exposure",
        "minimum_observations": 60,
        "minimum_duration": "180d",
        "GO": "lower95 net and incremental >0; PF>1.1; MaxDD<=15%",
        "NO_GO": "upper95 net or incremental <=0",
        "INCONCLUSIVE": "otherwise or fewer than 60 events at 365d",
        "version": "1",
        "freeze_policy": "material change creates new version",
    }
    one = freeze_trial(spec)
    two = freeze_trial(dict(reversed(list(spec.items()))))
    assert one["state"] == "READY_FROZEN"
    assert one["sha256"] == two["sha256"]
    with pytest.raises(ValueError, match="trial missing"):
        freeze_trial({})


def test_default_trial_is_not_ready_until_real_blockers_are_resolved() -> None:
    trial = default_trial()
    assert trial["state"] == "NOT_READY"
    assert "OBSERVED_MARKET_COSTS_NOT_AVAILABLE" in trial["blockers"]
    assert trial["capital_permission"] is False


def test_synthetic_control_is_explicit_and_closes_portfolio() -> None:
    result = synthetic_control()
    assert result["artifact_type"] == "SYNTHETIC_ENGINEERING_CONTROL_NOT_MARKET_EVIDENCE"
    assert result["paper_trade"]["fill_status"] == "FILLED"
    assert result["portfolio"]["trade_count"] == 1
    assert result["capital_permission"] is False


def test_baselines_use_same_candidate_cohort_and_oracle_metrics_are_labeled() -> None:
    causal = causal_opportunity_ledger(candles(), assumed_cost(), horizon_days=3)
    report = baseline_report(causal)
    assert report["always-flat"]["mean_net_return"] == 0
    assert report["PR122-direction"]["sample_size"] == len(causal)
    oracle = oracle_opportunity_catalog(candles())
    metrics = opportunity_metrics(oracle, causal)
    assert metrics["metric_scope"].startswith("RETROSPECTIVE_ORACLE")
    assert metrics["Alert_Delivery_Rate"] is None


def test_operational_status_keeps_config_enabled_and_observed_separate(tmp_path) -> None:
    now = T0 + timedelta(days=2)
    state = tmp_path / "state.json"
    heartbeat = tmp_path / "heartbeat.json"
    state.write_text(
        json.dumps(
            {
                "updated_at": (now - timedelta(hours=3)).isoformat(),
                "assets": {"bitcoin": {}},
                "delivery_pending": True,
            }
        ),
        encoding="utf-8",
    )
    heartbeat.write_text(
        json.dumps({"finished_at": (now - timedelta(hours=2)).isoformat()}), encoding="utf-8"
    )
    result = operational_status(opportunity_state=state, heartbeat=heartbeat, now=now)
    assert result["SCHEDULE_CONFIGURED"] is True
    assert result["SCHEDULER_ENABLED"] == "NOT_VERIFIED"
    assert result["HEARTBEAT_OBSERVED"] is True
    assert result["ALERT_DELIVERY_OBSERVED"] is False
    assert result["blind_time_hours"] == 2


def test_read_only_sqlite_replay_and_output(tmp_path) -> None:
    database = tmp_path / "market.db"
    connection = sqlite3.connect(database)
    connection.execute(
        """CREATE TABLE raw_market_data(
        source TEXT, symbol TEXT, interval TEXT, ts TEXT, open REAL, high REAL,
        low REAL, close REAL, volume REAL, published_at TEXT)"""
    )
    for row in candles():
        connection.execute(
            "INSERT INTO raw_market_data VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                row.source,
                row.asset,
                "1d",
                row.timestamp.isoformat(),
                row.open,
                row.high,
                row.low,
                row.close,
                row.volume,
                row.published_at.isoformat(),
            ),
        )
    connection.commit()
    connection.close()
    loaded = load_candles_sqlite(database, asset="bitcoin")
    assert len(loaded) == 90
    output = tmp_path / "result.json"
    result = run_replay(database, output, asset="bitcoin", source="binance")
    assert output.exists()
    assert result["source_database_sha256"]
    assert result["paper_execution"] == "NOT_AVAILABLE_MISSING_QUOTES"
    assert result["capital_permission"] is False


def test_non_contiguous_data_fails_closed() -> None:
    series = candles()
    del series[20]
    with pytest.raises(ValueError, match="contiguous"):
        causal_opportunity_ledger(series, assumed_cost())
