import asyncio
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from GarimpoInvestimentos.analyzers import ai_insights
from GarimpoInvestimentos.collectors import news
from GarimpoInvestimentos.core import cache
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.ingest import ingest_crypto
from tests.test_review_data_contracts import point
from tests.test_review_input_snapshots import snapshot


@pytest.mark.parametrize("score", [None, "75", True, -1, 101, float("nan"), float("inf")])
def test_invalid_llm_score_is_preserved_as_excluded_fallback(monkeypatch, score):
    response = json.dumps({"sentiment": "positivo", "summary": "test", "opportunity_score": score})

    async def call(prompt):
        return response

    monkeypatch.setattr(ai_insights, "_call_gemini", call)
    result = asyncio.run(ai_insights._analyze_once("bitcoin", "public test", "gemini"))
    assert result["llm_fallback"] is True
    assert result["raw_response"] == response
    assert result["failure_type"] == "ValueError"


def test_llm_exception_does_not_log_secret(monkeypatch, caplog):
    secret = "test-private-value-not-for-logs"

    async def call(prompt):
        raise RuntimeError(secret)

    monkeypatch.setattr(ai_insights, "_call_gemini", call)
    result = asyncio.run(ai_insights._analyze_once("bitcoin", "public test", "gemini"))
    assert result["llm_fallback"]
    assert secret not in caplog.text + json.dumps(result)


@pytest.mark.parametrize("payload", [[], {"bitcoin": []}, {"bitcoin": {"cached_at": "2999-01-01"}}])
def test_malformed_or_future_cache_cannot_be_served(tmp_path, monkeypatch, payload):
    path = tmp_path / "cache.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(cache, "CACHE_PATH", str(path))
    assert cache.load_cache() == {}


def test_news_receipt_is_not_renewed_by_cache_and_expires(monkeypatch):
    current = news.NewsResult(["original title"], "serpapi")
    key = ("serpapi", "bitcoin", 5)
    monkeypatch.setattr(news, "_NEWS_CACHE", {key: current})
    monkeypatch.setattr(news, "_OPEN_CIRCUITS", set())
    monkeypatch.setattr(news, "provider_order_for_asset", lambda query: ["serpapi"])
    monkeypatch.setattr(news, "guard_allow", lambda *args: SimpleNamespace(allowed=True))
    calls = []

    async def fetch(query, limit):
        calls.append(query)
        return ["new title"]

    monkeypatch.setattr(news, "_PROVIDERS", {"serpapi": SimpleNamespace(fetch=fetch)})
    assert asyncio.run(news.get_news_result("bitcoin")) is current
    assert not calls
    news._NEWS_CACHE[key] = news.NewsResult(
        ["expired"], "serpapi", received_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat()
    )
    assert asyncio.run(news.get_news_result("bitcoin")).titles == ["new title"]
    assert calls == ["bitcoin"]


@pytest.mark.parametrize("points", [[], [point(0), point(0)]])
def test_invalid_ingest_does_not_change_store(tmp_path, points):
    async def fetch(*args, **kwargs):
        return points

    with FeatureStore(tmp_path / "store.db") as store:
        with pytest.raises(ValueError):
            asyncio.run(ingest_crypto(store, SimpleNamespace(fetch_ohlcv=fetch), "bitcoin"))
        assert store._conn.execute("SELECT COUNT(*) FROM raw_market_data").fetchone()[0] == 0


def test_sqlite_replace_cannot_bypass_snapshot_immutability(tmp_path):
    with FeatureStore(tmp_path / "store.db") as store:
        digest = snapshot(store)
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            store._conn.execute(
                "INSERT OR REPLACE INTO market_snapshots SELECT snapshot_id,symbol,interval,feature_version,collected_at,'{}' FROM market_snapshots WHERE snapshot_id=?",
                (digest,),
            )


def test_scanner_without_git_reports_location_only(tmp_path, monkeypatch):
    from scripts import scan_secrets

    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(scan_secrets.subprocess, "run", missing)
    secret = "sk-" + "a" * 30
    (tmp_path / "source.txt").write_text(secret, encoding="utf-8")
    findings = scan_secrets.scan(tmp_path)
    assert findings == [{"path": "source.txt", "line": 1, "kind": "openai"}]
    assert secret not in json.dumps(findings)


def test_v3_cache_respects_window_and_excludes_open_candle(monkeypatch, tmp_path):
    from GarimpoInvestimentos.v3 import pipeline
    from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord
    from GarimpoInvestimentos.v3.collectors.spot_collector import KlineRecord

    path = tmp_path / "cached.csv"
    path.touch()
    for name in ("_funding_path", "_oi_path", "spot_path"):
        monkeypatch.setattr(pipeline, name, lambda symbol: path)
    monkeypatch.setattr(
        pipeline,
        "load_funding_csv",
        lambda p: [FundingRecord("BTCUSDT", t, 0, 100) for t in (0, 3600000, 7200000)],
    )
    monkeypatch.setattr(
        pipeline,
        "load_oi_csv",
        lambda p: [SimpleNamespace(timestamp_ms=t) for t in (0, 3600000, 7200000)],
    )
    monkeypatch.setattr(
        pipeline,
        "load_spot_csv",
        lambda p: [KlineRecord("BTCUSDT", t, 100, 1) for t in (0, 3600000, 7200000)],
    )
    funding, oi, spot = asyncio.run(pipeline._collect_symbol("BTCUSDT", 3600000, 7200001))
    assert [r.funding_time_ms for r in funding] == [3600000, 7200000]
    assert [r.timestamp_ms for r in oi] == [3600000, 7200000]
    assert [r.open_ms for r in spot] == [3600000]


def test_new_diagnostics_cannot_acquire_legacy_verdict_or_mutate_trials(monkeypatch, capsys):
    from GarimpoInvestimentos import quality_snapshot
    from GarimpoInvestimentos.analyzers import backtest
    from GarimpoInvestimentos.dpl.snapshots import EVALUATION_CONTRACT

    def forbidden(*args, **kwargs):
        raise AssertionError("diagnostic cannot request an inferential verdict or registry")

    monkeypatch.setattr(backtest, "spearman_block_ci", forbidden)
    monkeypatch.setattr(backtest, "load_trials", forbidden)
    rows = [
        {"score": i, "var_d7_pct": i, "evaluation_contract": EVALUATION_CONTRACT} for i in range(10)
    ]
    backtest._report(rows)
    assert "sem veredito" in capsys.readouterr().out
    assert backtest.close_trial_sharpes(rows, 7) == {}
    assert quality_snapshot._spearman_stats(rows, 7) is None
