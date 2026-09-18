import json
from datetime import UTC, datetime

from GarimpoInvestimentos.analyzers.opportunity_detector import (
    BULL,
    STRONG_MOVE,
    augment_opportunity_features,
)
from GarimpoInvestimentos.opportunity_monitor import scan_opportunities


def _candles(n=30, *, last_jump=False):
    rows = []
    price = 100.0
    for i in range(n):
        if last_jump and i == n - 1:
            price *= 1.07
            volume = 300.0
        else:
            price *= 1.001
            volume = 100.0
        rows.append(
            {
                "timestamp": f"2026-08-{i + 1:02d}T00:00:00+00:00",
                "close": price,
                "volume": volume,
            }
        )
    return rows


def test_detector_only_features_do_not_mutate_llm_hard_data():
    original = {"change_7d": 9.0, "indicadores": {"macd_histogram": 2.0}}
    enriched = augment_opportunity_features(original, _candles(last_jump=True), source="binance")
    assert "change_3d" not in original
    assert "volume_ratio_20d" not in original
    assert enriched["change_3d"] > 0
    assert enriched["volume_ratio_20d"] > 1.5


class _Store:
    pass


def test_scan_persists_and_deduplicates_alert_transition(tmp_path, monkeypatch):
    snapshot = {
        "features": {
            "change_24h": 7.12,
            "change_7d": 9.22,
            "change_30d": 6.25,
            "rsi_14": 73.5,
            "preco_vs_sma50_pct": 8.29,
            "macd_histogram": 369.71,
        },
        "normalized_candles": _candles(last_jump=True),
        "source": "binance",
    }

    monkeypatch.setattr(
        "GarimpoInvestimentos.opportunity_monitor.serving_context",
        lambda store, asset, now=None: snapshot,
    )
    monkeypatch.setattr(
        "GarimpoInvestimentos.opportunity_monitor.emit_event",
        lambda *args, **kwargs: None,
    )
    sent = []
    monkeypatch.setattr(
        "GarimpoInvestimentos.opportunity_monitor._notify_webhook",
        lambda text, title: sent.append((title, text)) or True,
    )

    state = tmp_path / "state.json"
    alert = tmp_path / "alert.txt"
    now = datetime(2026, 8, 20, 1, 0, tzinfo=UTC)

    first = scan_opportunities(_Store(), ["bitcoin"], now=now, state_path=state, alert_path=alert)
    second = scan_opportunities(_Store(), ["bitcoin"], now=now, state_path=state, alert_path=alert)

    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["assets"]["bitcoin"]["state"] == STRONG_MOVE
    assert saved["assets"]["bitcoin"]["direction"] == BULL
    assert first["triggered"] == 1
    assert second["triggered"] == 0
    assert len(sent) == 1
    assert alert.exists()
