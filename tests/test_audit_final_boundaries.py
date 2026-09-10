import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from GarimpoInvestimentos import watchdog
from GarimpoInvestimentos.analyzers import indicators, score_engine
from GarimpoInvestimentos.core import cache
from GarimpoInvestimentos.dpl.alignment import AlignmentEngine
from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.signals import SignalPoint
from GarimpoInvestimentos.governance import load_observation_plan
from GarimpoInvestimentos.observation_reporting import weekly_report
from GarimpoInvestimentos.observation_watchdog import check_observation_health
from GarimpoInvestimentos.phase1_watchdog import check_phase1_health

T = datetime(2026, 9, 10, tzinfo=UTC)


def test_zero_momentum_and_flat_rsi_are_neutral():
    assert (
        score_engine.technical_direction({"preco_vs_sma200_pct": 0, "macd_histogram": 0})
        == "neutral"
    )
    assert indicators.rsi([100.0] * 30) == 50.0


def test_nonfinite_score_cannot_propagate():
    with pytest.raises(ValueError):
        score_engine.calculate_final_score({"opportunity_score": float("nan")})


def test_corrupt_cache_is_not_overwritten(tmp_path, monkeypatch):
    p = tmp_path / "cache.json"
    p.write_text("invalid original", encoding="utf-8")
    monkeypatch.setattr(cache, "CACHE_PATH", str(p))
    with pytest.raises(ValueError):
        cache.save_cache({"bitcoin": {}})
    assert p.read_text(encoding="utf-8") == "invalid original"


def test_old_revision_cannot_replace_latest_observation():
    newer = SignalPoint("x", T, 2.0, "test", T, vintage=T)
    older_revised = SignalPoint(
        "x",
        T - timedelta(days=1),
        99.0,
        "test",
        T + timedelta(hours=1),
        vintage=T + timedelta(hours=1),
    )
    c = MarketDataPoint(
        "BTC", T + timedelta(hours=2), 1, 1, 1, 1, 1, "test", "1h", T + timedelta(hours=3)
    )
    assert AlignmentEngine().align([c], {"x": [newer, older_revised]})[0]["x"] == 2.0


@pytest.mark.parametrize(
    "finished", ["not a timestamp", "2026-09-10T00:00:00", "2026-09-11T00:00:00+00:00"]
)
def test_phase1_watchdog_bad_time_is_failed(tmp_path, finished):
    p = tmp_path / "ops" / "cripto-phase1" / "heartbeat.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"run_status": "SUCCEEDED", "finished_at": finished}), encoding="utf-8")
    r = check_phase1_health(db_path=tmp_path / "missing.db", state_root=tmp_path / "ops", now=T)
    assert any("heartbeat" in v for v in r["violations"])


def test_observation_watchdog_bad_json_is_failure_report(tmp_path):
    p = tmp_path / "ops" / "cripto-v3-daily" / "heartbeat.json"
    p.parent.mkdir(parents=True)
    p.write_text("bad json", encoding="utf-8")
    r = check_observation_health(
        db_path=tmp_path / "missing.db", state_root=tmp_path / "ops", now=T
    )
    assert not r["healthy"]


def test_watchdog_reads_operational_log_directory(tmp_path, monkeypatch):
    p = tmp_path / "logs" / "garimpo_fase1_20260910.log"
    p.parent.mkdir()
    p.write_text("test", encoding="utf-8")
    monkeypatch.setattr(watchdog, "LOG", p.parent / "watchdog.log")
    monkeypatch.setattr(watchdog, "ROOT", tmp_path / "checkout")
    assert watchdog._log_mais_recente() == p


def test_one_perfect_day_cannot_pass_weekly_coverage(tmp_path):
    card = {
        "window_start": T.isoformat(),
        "per_instrument": {"BTCUSDT": {"coverage": 1.0}, "ETHUSDT": {"coverage": 1.0}},
        "state": "HEALTHY",
    }
    store = SimpleNamespace(read_observation_scorecards=lambda **kw: [card])
    result = weekly_report(
        store, plan=load_observation_plan(), week_start=T.date(), output_dir=tmp_path
    )
    assert not result["metrics"]["funding_rate"]["weekly_coverage_passed"]


def test_ccxt_duplicate_timestamp_rejected(monkeypatch):
    from GarimpoInvestimentos.dpl.providers.binance import BinanceProvider

    class Client:
        async def fetch_ohlcv(self, *a, **kw):
            return [[1_600_000_000_000, 1, 2, 1, 1, 1]] * 2

        async def close(self):
            pass

    p = BinanceProvider({"bitcoin": "BTC/USDT"})
    monkeypatch.setattr(p, "_client", lambda: Client())
    with pytest.raises(ValueError, match="duplic"):
        asyncio.run(p.fetch_ohlcv("bitcoin", limit=2))


def test_discovery_nonfinite_row_is_not_candidate():
    from GarimpoInvestimentos.collectors.discovery import rank_candidates

    row = {
        "id": "bad",
        "symbol": "bad",
        "current_price": 10,
        "total_volume": float("inf"),
        "price_change_percentage_7d_in_currency": 2.0,
    }
    assert rank_candidates([row]) == []
