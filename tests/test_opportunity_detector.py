from GarimpoInvestimentos.analyzers.opportunity_detector import (
    BULL,
    BEAR,
    NORMAL,
    PERSISTENT,
    STRONG_MOVE,
    WATCH,
    detect_asset_opportunity,
    detect_market_breadth,
    should_notify_transition,
)


def test_august_19_move_is_detected_even_with_overbought_rsi():
    hard = {
        "change_24h": 7.12,
        "change_3d": 10.23,
        "change_7d": 9.22,
        "change_30d": 6.25,
        "volume_ratio_20d": 2.41,
        "indicadores": {
            "preco_vs_sma50_pct": 8.29,
            "macd_histogram": 369.71,
            "rsi_14": 73.5,
        },
    }
    signal = detect_asset_opportunity("bitcoin", hard)
    assert signal.state == STRONG_MOVE
    assert signal.direction == BULL
    assert signal.extension_risk is True
    assert "3d>=8%" in signal.reasons


def test_september_9_persistent_move_survives_short_term_cooling():
    hard = {
        "change_24h": -0.19,
        "change_3d": -2.53,
        "change_7d": 1.25,
        "change_30d": 22.41,
        "volume_ratio_20d": 0.82,
        "indicadores": {
            "preco_vs_sma50_pct": 11.50,
            "preco_vs_sma200_pct": 11.94,
            "macd_histogram": -497.58,
            "rsi_14": 59.5,
        },
    }
    signal = detect_asset_opportunity("bitcoin", hard)
    assert signal.state == PERSISTENT
    assert signal.direction == BULL
    assert "30d>=15% and price above SMA50" in signal.reasons


def test_watch_detects_confirmed_seven_day_trend_without_needing_llm():
    signal = detect_asset_opportunity(
        "ethereum",
        {
            "change_7d": 6.0,
            "indicadores": {"macd_histogram": 1.0, "rsi_14": 55.0},
        },
    )
    assert signal.state == WATCH
    assert signal.direction == BULL


def test_bearish_detection_is_symmetric():
    signal = detect_asset_opportunity(
        "bitcoin",
        {
            "change_24h": -6.0,
            "change_3d": -9.0,
            "change_7d": -12.0,
            "change_30d": -18.0,
            "volume_ratio_20d": 2.0,
            "indicadores": {
                "preco_vs_sma50_pct": -10.0,
                "macd_histogram": -200.0,
                "rsi_14": 25.0,
            },
        },
    )
    assert signal.state == STRONG_MOVE
    assert signal.direction == BEAR
    assert signal.extension_risk is True


def test_normal_market_stays_quiet():
    signal = detect_asset_opportunity(
        "bitcoin",
        {
            "change_24h": 0.5,
            "change_3d": 1.0,
            "change_7d": 1.5,
            "change_30d": 2.0,
            "volume_ratio_20d": 1.0,
            "indicadores": {
                "preco_vs_sma50_pct": 1.0,
                "macd_histogram": 10.0,
                "rsi_14": 50.0,
            },
        },
    )
    assert signal.state == NORMAL
    assert signal.active is False


def test_market_breadth_fires_when_two_large_assets_jump_together():
    signals = [
        detect_asset_opportunity("bitcoin", {"change_24h": 7.1}),
        detect_asset_opportunity("ethereum", {"change_24h": 17.5}),
        detect_asset_opportunity("solana", {"change_24h": 10.8}),
    ]
    breadth = detect_market_breadth(signals)
    assert breadth.active is True
    assert breadth.direction == BULL
    assert breadth.count == 3
    assert breadth.assets == ("bitcoin", "ethereum", "solana")


def test_transition_notifies_first_signal_escalation_and_direction_flip_only():
    watch = detect_asset_opportunity(
        "bitcoin", {"change_7d": 6.0, "indicadores": {"macd_histogram": 1.0}}
    )
    strong = detect_asset_opportunity("bitcoin", {"change_3d": 9.0})
    persistent = detect_asset_opportunity(
        "bitcoin", {"change_30d": 20.0, "indicadores": {"preco_vs_sma50_pct": 5.0}}
    )
    bearish = detect_asset_opportunity("bitcoin", {"change_3d": -9.0})

    assert should_notify_transition(None, watch)
    assert should_notify_transition(watch.as_dict(), strong)
    assert not should_notify_transition(strong.as_dict(), persistent)
    assert should_notify_transition(persistent.as_dict(), bearish)
