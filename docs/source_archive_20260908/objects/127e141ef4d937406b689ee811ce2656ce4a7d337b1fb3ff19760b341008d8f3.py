import json
from pathlib import Path


def test_first_strategy_draft_is_simple_spot_and_not_activated():
    path = Path(__file__).resolve().parents[1] / "charters" / "trend_following_spot_4h_v1.json"
    draft = json.loads(path.read_text(encoding="utf-8"))
    assert draft["status"] == "DRAFT_NOT_REGISTERED"
    assert draft["venue"] == "binance_spot"
    assert draft["assets"] == ["BTCUSDT", "ETHUSDT"]
    assert draft["horizon"] == "4h"
    assert draft["position_set"] == [0, 1]
    assert not draft["short_allowed"]
    assert not draft["leverage_allowed"]
    assert not draft["llm_allowed"]
    assert draft["signal"]["lookback_bars"] == 42
    assert draft["validation"]["dsr_minimum"] == 0.95
