"""Adversarial reproductions recorded before the audit expansion fixes."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.trading.contracts import (
    Direction,
    Fill,
    Instrument,
    Liquidity,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)
from GarimpoInvestimentos.trading.execution import (
    OrderBookLedger,
    OrderLifecycleError,
    SimulatedExchangeAdapter,
    apply_fill,
    reconcile,
)
from GarimpoInvestimentos.trading.microstructure import (
    DepthSequenceGap,
    DepthUpdate,
    LocalOrderBook,
    OrderBookLevel,
    OrderBookSnapshot,
    simulate_market_fill,
)
from GarimpoInvestimentos.trading.report import build_portfolio_report
from GarimpoInvestimentos.v3.collectors.funding_collector import (
    FundingRecord,
    load_funding_csv,
    save_funding_csv,
)
from GarimpoInvestimentos.v3.collectors.oi_collector import OIRecord, load_oi_csv, save_oi_csv
from GarimpoInvestimentos.v3.collectors.spot_collector import (
    KlineRecord,
    load_spot_csv,
    save_spot_csv,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
ASSET = Instrument("BTCUSDT", "binance_spot", "crypto_spot")


def order():
    return Order("o1", "i1", ASSET, OrderSide.BUY, OrderType.MARKET, 1.0, OrderStatus.ACCEPTED, T0)


def fill(qty=0.4):
    return Fill("f1", "o1", qty, 100.0, 0.04, Liquidity.TAKER, T0)


def book():
    return OrderBookSnapshot(ASSET, T0, (OrderBookLevel(99.0, 1.0),), (OrderBookLevel(101.0, 1.0),))


@pytest.mark.parametrize("qty", [0.4, 1.0])
def test_replayed_fill_is_idempotent_even_after_completion(qty):
    first = apply_fill(order(), fill(qty))
    assert apply_fill(first, fill(qty)) == first


def test_conflicting_fill_id_is_rejected():
    first = apply_fill(order(), fill())
    with pytest.raises(OrderLifecycleError):
        apply_fill(first, replace(fill(), price=200.0))


@pytest.mark.parametrize(
    "change",
    [
        {"price": 200.0},
        {"fee": 5.0},
        {"filled_at": T0 + timedelta(seconds=1)},
        {"fill_id": "other"},
    ],
)
def test_reconcile_detects_economic_or_identity_difference(change):
    local = apply_fill(order(), fill())
    adapter = SimulatedExchangeAdapter()
    adapter.record_fill(replace(fill(), **change))
    assert reconcile(local, adapter) is not None


def test_adapter_deduplicates_same_receipt():
    adapter = SimulatedExchangeAdapter()
    adapter.record_fill(fill())
    adapter.record_fill(fill())
    assert adapter.reported_fills("o1") == (fill(),)


def test_ledger_rejects_order_id_collision():
    ledger = OrderBookLedger()
    first = ledger.submit(order(), client_order_id="first")
    with pytest.raises(OrderLifecycleError):
        ledger.submit(replace(order(), qty=2.0), client_order_id="second")
    assert ledger.get("o1") == first


def test_ledger_rejects_client_id_with_changed_economics():
    ledger = OrderBookLedger()
    ledger.submit(order(), client_order_id="first")
    with pytest.raises(OrderLifecycleError):
        ledger.submit(replace(order(), order_id="o2", qty=2.0), client_order_id="first")


def test_order_rejects_receipt_predating_creation():
    with pytest.raises(ValueError):
        apply_fill(order(), replace(fill(), filled_at=T0 - timedelta(seconds=1)))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("field", ["qty", "price", "fee"])
def test_fill_rejects_nonfinite_numbers(field, value):
    with pytest.raises(ValueError):
        replace(fill(), **{field: value})


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_book_rejects_nonfinite_levels(value):
    with pytest.raises(ValueError):
        OrderBookLevel(value, 1.0)


def test_book_rejects_duplicate_price_liquidity():
    with pytest.raises(ValueError):
        replace(book(), asks=(OrderBookLevel(101.0, 1.0), OrderBookLevel(101.0, 1.0)))


def test_failed_depth_update_does_not_partially_mutate_book():
    local = LocalOrderBook(book(), last_update_id=10)
    bad = DepthUpdate(ASSET, 11, 11, T0 + timedelta(seconds=1), ((99.0, 0.0),), ())
    with pytest.raises(DepthSequenceGap):
        local.apply(bad)
    assert local.last_update_id == 10
    assert local.snapshot() == book()


def test_crossed_depth_update_is_rejected_atomically():
    local = LocalOrderBook(book(), last_update_id=10)
    bad = DepthUpdate(ASSET, 11, 11, T0 + timedelta(seconds=1), ((102.0, 1.0),), ())
    with pytest.raises(DepthSequenceGap):
        local.apply(bad)
    assert local.snapshot() == book()


def test_tiny_positive_quantity_is_not_a_phantom_fill():
    result = simulate_market_fill(book(), OrderSide.BUY, 1e-13)
    assert result.filled_qty == pytest.approx(1e-13, abs=1e-25)
    assert result.vwap_price == pytest.approx(101.0)


def test_portfolio_sums_lots_for_the_same_instrument():
    positions = [Position(ASSET, Direction.LONG, qty, 100.0, T0) for qty in (1.0, 2.0)]
    result = build_portfolio_report(positions, {ASSET.key: 100.0}, equity=1000.0)
    assert result.gross_notional == pytest.approx(300.0)
    assert result.gross_leverage == pytest.approx(result.gross_notional / 1000.0)


CSV_CASES = [
    (
        save_funding_csv,
        load_funding_csv,
        FundingRecord("BTCUSDT", 1000, 0.001, 100.0),
        "funding_rate",
    ),
    (save_oi_csv, load_oi_csv, OIRecord("BTCUSDT", 1000, 1.0, 100.0), "oi_contracts"),
    (save_spot_csv, load_spot_csv, KlineRecord("BTCUSDT", 1000, 100.0, 1.0), "close"),
]


@pytest.mark.parametrize("save,load,record,field", CSV_CASES)
def test_csv_deduplicates_within_single_batch(tmp_path, save, load, record, field):
    target = tmp_path / "data.csv"
    assert save([record, record], target) == 1
    assert load(target) == [record]


@pytest.mark.parametrize("save,load,record,field", CSV_CASES)
def test_csv_conflicting_observation_preserves_original(tmp_path, save, load, record, field):
    target = tmp_path / "data.csv"
    save([record], target)
    original = target.read_bytes()
    with pytest.raises(ValueError):
        save([replace(record, **{field: 999.0})], target)
    assert target.read_bytes() == original


@pytest.mark.parametrize("length,offset", [(0, 1), (2, 3), (2, 5)])
def test_factor_lag_preserves_timeline_length(length, offset):
    from GarimpoInvestimentos.analyzers.factor_dsl import evaluate, feature, lag

    assert evaluate(lag(feature("x"), offset), {"x": [1.0] * length}) == [None] * length


@pytest.mark.parametrize(
    "recipe",
    [
        {"op": "add", "args": [1, 2]},
        {"op": "feature", "args": [[]]},
        {"op": "lag", "args": [{"op": "feature", "args": ["x"]}, 1.5]},
        {"op": [], "args": []},
        {"op": "const", "args": [float("nan")]},
    ],
)
def test_malformed_factor_fails_during_construction(recipe):
    from GarimpoInvestimentos.analyzers.factor_dsl import RecipeError, from_recipe

    with pytest.raises(RecipeError):
        from_recipe(recipe)


def test_harness_spearman_does_not_invent_rank_for_ties():
    from GarimpoInvestimentos.analyzers.ground_truth_harness import spearman_of

    rows = [{"score": 50.0, "var_d7_pct": float(i)} for i in range(4)]
    assert spearman_of(rows, 7) is None


def test_harness_duplicate_does_not_hide_a_missing_prediction(tmp_path):
    from GarimpoInvestimentos.analyzers.ground_truth_harness import PlantedWorld, compare_to_truth

    truth = {("a", T0): 1.0, ("b", T0): 1.0}
    world = PlantedWorld(tmp_path / "unused.db", truth, 2, 7)
    row = {"ativo": "a", "pred_date": T0, "var_d7_pct": 1.0}
    with pytest.raises(ValueError):
        compare_to_truth([row, row], world)


def test_pbo_rejects_nonfinite_observations():
    from GarimpoInvestimentos.analyzers.pbo import PBOError, probability_of_backtest_overfitting

    with pytest.raises(PBOError):
        probability_of_backtest_overfitting(
            {"a": [float("nan")] * 8, "b": [1.0, 2.0] * 4}, n_splits=2
        )


def test_equivalence_cannot_pass_without_comparisons():
    from GarimpoInvestimentos.analyzers.equivalence import report

    assert report({"btc": {"skipped": "unavailable"}}) is False


@pytest.mark.parametrize("kind", ["proposals", "evaluations"])
def test_append_scientific_trace_refuses_corrupt_history(tmp_path, kind):
    from GarimpoInvestimentos.analyzers.hypothesis_loop import append_proposals
    from GarimpoInvestimentos.analyzers.hypothesis_loop_runner import append_evaluations

    path = tmp_path / "trace.json"
    path.write_text('[{"original":', encoding="utf-8")
    original = path.read_bytes()
    with pytest.raises(ValueError):
        (append_proposals if kind == "proposals" else append_evaluations)([], path)
    assert path.read_bytes() == original


def test_proposal_evaluation_refuses_misaligned_target():
    from GarimpoInvestimentos.analyzers.hypothesis_loop import ACCEPTED, Proposal, evaluate_proposal

    p = Proposal(
        "p", T0.isoformat(), "synthetic", {"op": "feature", "args": ["x"]}, 7, "test", ACCEPTED
    )
    with pytest.raises(ValueError):
        evaluate_proposal(p, {"x": [1.0, 2.0, 3.0]}, [1.0])


def test_dense_store_refuses_unsupported_venue(tmp_path):
    from GarimpoInvestimentos.trading.binance_spot_collector import TradeObservation
    from GarimpoInvestimentos.trading.store import TradingStore

    obs = TradeObservation(
        Instrument("BTCUSDT", "other", "crypto_spot"), 1, 100.0, 1.0, False, T0, T0, T0, "abc"
    )
    with TradingStore(tmp_path / "store.db") as store, pytest.raises(ValueError):
        store.append_trade(obs)


def test_dense_store_preserves_short_session_identifier(tmp_path):
    from GarimpoInvestimentos.trading.binance_spot_collector import TradeObservation
    from GarimpoInvestimentos.trading.store import TradingStore

    obs = TradeObservation(ASSET, 1, 100.0, 1.0, False, T0, T0, T0, "abc")
    with TradingStore(tmp_path / "store.db") as store:
        store.append_trade(obs)
        assert store.latest_microstructure()[0]["session_id"] == "abc"


@pytest.mark.parametrize("event,field", [("trade", "p"), ("bookTicker", "b")])
def test_stream_parser_refuses_nonfinite_prices(event, field):
    from GarimpoInvestimentos.trading.binance_spot_collector import parse_stream_message

    payload = {
        "e": event,
        "s": "BTCUSDT",
        "p": "100",
        "q": "1",
        "m": False,
        "t": 1,
        "T": 1,
        "E": 1,
        "u": 1,
        "b": "99",
        "B": "1",
        "a": "101",
        "A": "1",
    }
    payload[field] = "NaN"
    with pytest.raises(ValueError):
        parse_stream_message(payload, received_at=T0, session_id="abc")
