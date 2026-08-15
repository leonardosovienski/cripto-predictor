"""Portfólio (trading/portfolio.py) — matemática pura, sem I/O."""

from datetime import UTC, datetime

import pytest

from GarimpoInvestimentos.trading.contracts import Direction, Instrument, Position
from GarimpoInvestimentos.trading.portfolio import (
    BalanceReconciliationBreak,
    DrawdownTracker,
    aggregate_leverage,
    beta,
    concentration_hhi,
    correlation,
    correlation_matrix,
    exchange_exposure,
    liquidation_distance_pct,
    reconcile_balance,
    volatility_target_size,
)

T0 = datetime(2026, 8, 14, tzinfo=UTC)
BTC_BINANCE = Instrument("BTCUSDT", "binance_futures")
ETH_KRAKEN = Instrument("ETHUSD", "kraken")


# --- beta / correlation ------------------------------------------------------------


def test_beta_of_series_with_itself_is_one():
    series = [0.01, -0.02, 0.03, 0.015, -0.005]
    assert beta(series, series) == pytest.approx(1.0)


def test_beta_scaled_series():
    benchmark = [0.01, -0.02, 0.03, 0.015, -0.005]
    asset = [2 * x for x in benchmark]
    assert beta(asset, benchmark) == pytest.approx(2.0)


def test_beta_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="mesmo tamanho"):
        beta([0.01, 0.02], [0.01])


def test_beta_rejects_too_few_observations():
    with pytest.raises(ValueError, match="ao menos 2"):
        beta([0.01], [0.01])


def test_beta_rejects_zero_variance_benchmark():
    with pytest.raises(ValueError, match="variância"):
        beta([0.01, 0.02, 0.03], [0.05, 0.05, 0.05])


def test_correlation_perfect_positive():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [2.0, 4.0, 6.0, 8.0]
    assert correlation(a, b) == pytest.approx(1.0)


def test_correlation_perfect_negative():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [8.0, 6.0, 4.0, 2.0]
    assert correlation(a, b) == pytest.approx(-1.0)


def test_correlation_matrix_diagonal_is_one_and_symmetric():
    returns = {"BTC": [0.01, -0.02, 0.03], "ETH": [0.02, -0.01, 0.025]}
    matrix = correlation_matrix(returns)
    assert matrix[("BTC", "BTC")] == pytest.approx(1.0)
    assert matrix[("ETH", "ETH")] == pytest.approx(1.0)
    assert matrix[("BTC", "ETH")] == pytest.approx(matrix[("ETH", "BTC")])


# --- concentration_hhi --------------------------------------------------------------


def test_hhi_equal_split_two_assets():
    hhi = concentration_hhi({"BTC": 50_000.0, "ETH": 50_000.0})
    assert hhi == pytest.approx(0.5)


def test_hhi_all_in_one_asset_is_one():
    hhi = concentration_hhi({"BTC": 100_000.0, "ETH": 0.0})
    assert hhi == pytest.approx(1.0)


def test_hhi_rejects_zero_total():
    with pytest.raises(ValueError, match="deve ser > 0"):
        concentration_hhi({"BTC": 0.0})


# --- exposure / leverage -------------------------------------------------------------


def _positions():
    return [
        Position(BTC_BINANCE, Direction.LONG, 1.0, 60_000.0, T0),
        Position(ETH_KRAKEN, Direction.SHORT, 10.0, 3_000.0, T0),
    ]


def test_exchange_exposure_signed_by_direction():
    marks = {"binance_futures:BTCUSDT": 61_000.0, "kraken:ETHUSD": 2_900.0}
    exposure = exchange_exposure(_positions(), marks)
    assert exposure["binance_futures"] == pytest.approx(61_000.0)
    assert exposure["kraken"] == pytest.approx(-29_000.0)


def test_exchange_exposure_missing_mark_price_raises():
    with pytest.raises(ValueError, match="mark price"):
        exchange_exposure(_positions(), {"binance_futures:BTCUSDT": 61_000.0})


def test_aggregate_leverage():
    marks = {"binance_futures:BTCUSDT": 60_000.0, "kraken:ETHUSD": 3_000.0}
    # notional bruto = 60_000 + 30_000 = 90_000; equity = 45_000 -> leverage 2x
    lev = aggregate_leverage(_positions(), marks, equity=45_000.0)
    assert lev == pytest.approx(2.0)


def test_aggregate_leverage_rejects_nonpositive_equity():
    with pytest.raises(ValueError, match="equity"):
        aggregate_leverage(_positions(), {}, equity=0.0)


# --- volatility_target_size ---------------------------------------------------------


def test_volatility_target_size_scales_down_high_vol_asset():
    size = volatility_target_size(target_vol=0.02, asset_vol=0.04, capital=100_000.0)
    assert size == pytest.approx(50_000.0)


def test_volatility_target_size_caps_at_full_capital():
    size = volatility_target_size(target_vol=0.10, asset_vol=0.01, capital=100_000.0)
    assert size == pytest.approx(100_000.0)  # nunca alavanca implicitamente


def test_volatility_target_size_rejects_zero_asset_vol():
    with pytest.raises(ValueError, match="asset_vol"):
        volatility_target_size(0.02, 0.0, 100_000.0)


# --- DrawdownTracker -----------------------------------------------------------------


def test_drawdown_tracker_tracks_peak_and_max():
    tracker = DrawdownTracker()
    assert tracker.update(100_000.0) == pytest.approx(0.0)
    assert tracker.update(110_000.0) == pytest.approx(0.0)  # novo pico
    assert tracker.update(88_000.0) == pytest.approx(0.2)  # -20% do pico de 110k
    assert tracker.max_drawdown == pytest.approx(0.2)
    tracker.update(99_000.0)  # recupera parcialmente
    assert tracker.current_drawdown == pytest.approx(0.1)
    assert tracker.max_drawdown == pytest.approx(0.2)  # máximo não regride


def test_drawdown_tracker_rejects_nonpositive_equity():
    tracker = DrawdownTracker()
    with pytest.raises(ValueError, match="equity"):
        tracker.update(0.0)


# --- liquidation_distance_pct ---------------------------------------------------------


def test_liquidation_distance_pct_higher_leverage_is_closer():
    low_lev = liquidation_distance_pct(Direction.LONG, leverage=2.0, maintenance_margin_rate=0.005)
    high_lev = liquidation_distance_pct(
        Direction.LONG, leverage=10.0, maintenance_margin_rate=0.005
    )
    assert high_lev < low_lev


def test_liquidation_distance_pct_rejects_already_liquidatable():
    with pytest.raises(ValueError, match="já estaria liquidável"):
        liquidation_distance_pct(Direction.LONG, leverage=100.0, maintenance_margin_rate=0.02)


def test_liquidation_distance_pct_rejects_bad_leverage():
    with pytest.raises(ValueError, match="leverage"):
        liquidation_distance_pct(Direction.LONG, leverage=0.0, maintenance_margin_rate=0.01)


# --- reconcile_balance ---------------------------------------------------------------


def test_reconcile_balance_matches_returns_none():
    assert reconcile_balance("binance", 1000.0, 1000.0000001) is None


def test_reconcile_balance_divergence_returns_break():
    result = reconcile_balance("binance", 1000.0, 950.0)
    assert isinstance(result, BalanceReconciliationBreak)
    assert result.delta == pytest.approx(50.0)
