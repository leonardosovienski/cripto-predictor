"""Independent boundary regressions: no evidence erasure or false eligibility."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from GarimpoInvestimentos.dpl.macro_calendar import MacroEvent
from GarimpoInvestimentos.durable_io import load_json_history
from GarimpoInvestimentos.trading.portfolio import correlation_matrix
from GarimpoInvestimentos.v3 import backtest_v3, paper_report, paper_trader
from GarimpoInvestimentos.v3.macro_features import build_macro_event_dummy


@pytest.mark.parametrize("values", [[], [1.0], [1.0, 1.0], [float("nan"), 1.0]])
def test_self_correlation_is_not_evidence_without_variation(values):
    with pytest.raises(ValueError):
        correlation_matrix({"BTC": values})


@pytest.mark.parametrize("payload", ['[{"x": NaN}]', '[{"x":1,"x":2}]'])
def test_invalid_scientific_json_is_preserved(tmp_path, payload):
    path = tmp_path / "history.json"
    path.write_text(payload, encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        load_json_history(path)
    assert path.read_bytes() == before


def test_sweeps_stop_before_data_or_registry_when_family_frozen(monkeypatch):
    monkeypatch.setattr(
        backtest_v3,
        "load_scientific_state",
        lambda: SimpleNamespace(frozen_families=("funding_oi_hmm_v3",)),
    )
    monkeypatch.setattr(
        backtest_v3, "run_wfa", lambda **kwargs: pytest.fail("read data before freeze check")
    )
    monkeypatch.setattr(
        backtest_v3,
        "register_trial",
        lambda *args, **kwargs: pytest.fail("changed frozen registry"),
    )
    with pytest.raises(backtest_v3.FrozenFamilyError):
        backtest_v3.run_kelly_sweep("BTCUSDT", [1.0])
    with pytest.raises(backtest_v3.FrozenFamilyError):
        backtest_v3.run_threshold_grid("BTCUSDT", [1.0], [0.5])


def test_kelly_attempts_all_exist_before_first_result(monkeypatch):
    calls = []
    monkeypatch.setattr(backtest_v3, "_require_open_sweep", lambda: "synthetic")
    monkeypatch.setattr(backtest_v3, "register_trial", lambda name, **kw: calls.append((name, kw)))
    monkeypatch.setattr(backtest_v3, "emit_event", lambda *a, **kw: None)

    def result(**kw):
        assert len([c for c in calls if "metric" in c[1]]) == 2
        return backtest_v3.WFAResult(
            "BTCUSDT",
            0,
            [],
            0,
            0,
            0,
            0,
            0,
            "NO-GO",
            "synthetic",
            kelly_fraction=kw["kelly_fraction"],
        )

    monkeypatch.setattr(backtest_v3, "run_wfa", result)
    backtest_v3.run_kelly_sweep("BTCUSDT", [1.0, 0.5])
    assert len(calls) == 4
    assert len({c[0] for c in calls}) == 2


def test_macro_current_year_is_not_zero_feature_for_missing_historical_year():
    fv = SimpleNamespace(
        timestamp_exchange_ms=int(datetime(2024, 5, 1, tzinfo=UTC).timestamp() * 1000)
    )
    with pytest.raises(ValueError, match="cobertura"):
        build_macro_event_dummy(
            [fv],
            events=[MacroEvent("CPI", datetime(2026, 5, 1).date())],
            calendar_available_at=datetime(2024, 1, 1, tzinfo=UTC),
        )


def test_paper_idempotency_checks_corruption_after_matching_row(tmp_path, monkeypatch):
    monkeypatch.setattr(paper_trader, "_PAPER_DIR", tmp_path)
    p = tmp_path / "BTCUSDT_paper.jsonl"
    p.write_text('{"timestamp_exchange_ms":1}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError):
        paper_trader._already_recorded("BTCUSDT", 1)


def test_retrospective_paper_is_counted_without_spot(monkeypatch, tmp_path):
    monkeypatch.setattr(
        paper_report,
        "_load_paper_trades",
        lambda s: [{"signal_ts_utc": "2026-09-09T00:00:00+00:00", "timestamp_exchange_ms": 1}],
    )
    monkeypatch.setattr(paper_report, "_spot_path", lambda s: tmp_path / "absent.csv")
    report = paper_report.build_report("BTCUSDT")
    assert report["retrospective_records"] == 1
    assert report["cum_pnl"] is None


def test_sortino_sample_repetition_does_not_improve_risk_adjusted_return():
    returns = [0.1, -0.02, 0.03]
    assert backtest_v3._sortino_ratio(returns * 4) == pytest.approx(
        backtest_v3._sortino_ratio(returns)
    )
