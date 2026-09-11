import copy
import hashlib
import json
import random
from decimal import Decimal
from fractions import Fraction

import pytest

from GarimpoInvestimentos.research.__main__ import demo_config, evaluate, main
from GarimpoInvestimentos.research.factors import analyze_panel, residualize
from GarimpoInvestimentos.research.registry import RunStore
from GarimpoInvestimentos.research.simulation import ScenarioLedger, SpotContract
from GarimpoInvestimentos.research.universe import Rule, select_universe
from GarimpoInvestimentos.research.validation import LabelInterval, walk_forward


def contract(venue="A"):
    return SpotContract("asset@" + venue, venue, "BTC", "USDT", "BTC", "USDT/BTC", "USDT")


def test_panel_differential_scipy_with_ties_and_group_adjustment():
    stats = pytest.importorskip("scipy.stats")
    rng = random.Random(5126)
    for n in [3, 5, 17, 101]:
        rows = [
            {
                "date": 1,
                "asset": str(i),
                "factor": rng.randrange(5),
                "label": rng.random(),
                "group": str(i % 2),
            }
            for i in range(n)
        ]
        for adjust in [False, True]:
            result = analyze_panel(rows, group_adjust=adjust)
            labels = [r["label"] for r in rows]
            if adjust:
                labels = [
                    r["label"]
                    - sum(x["label"] for x in rows if x["group"] == r["group"])
                    / sum(x["group"] == r["group"] for x in rows)
                    for r in rows
                ]
            expected = stats.spearmanr([r["factor"] for r in rows], labels).statistic
            assert result["dates"][0]["rank_ic"] == pytest.approx(expected, abs=1e-12)


def test_ties_turnover_and_empty_bins():
    rows = [
        {"date": d, "asset": a, "factor": x, "label": x / 10}
        for d, a, x in [
            (1, "A", 1),
            (1, "B", 1),
            (1, "C", 3),
            (1, "D", 4),
            (2, "B", 1),
            (2, "E", 1),
            (2, "C", 3),
            (2, "D", 4),
        ]
    ]
    result = analyze_panel(rows, quantiles=2)["dates"]
    assert result[0]["quantiles"]["1"]["members"] == ["A", "B"]
    assert result[1]["quantiles"]["1"]["turnover"] == 0.5
    constant = analyze_panel([{**r, "factor": 1} for r in rows], quantiles=5)["dates"][0]
    assert constant["rank_ic"] is None
    assert sum(q["mean_label"] is None for q in constant["quantiles"].values()) == 4


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "1"])
def test_factor_rejects_invalid(bad):
    with pytest.raises(ValueError):
        analyze_panel([{"date": 1, "asset": "a", "factor": bad, "label": 0}])


def test_panel_duplicate_and_missing_group_rejected():
    row = {"date": 1, "asset": "a", "factor": 1, "label": 0}
    with pytest.raises(ValueError):
        analyze_panel([row, row])
    with pytest.raises(ValueError):
        analyze_panel([row], group_adjust=True)


def test_residual_differential_closed_form_and_orthogonality():
    pytest.importorskip("numpy")
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [2.0, 4.0, 5.0, 8.0, 10.0]
    mx, my = sum(x) / 5, sum(y) / 5
    slope = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / sum(
        (a - mx) ** 2 for a in x
    )
    expected = [b - (my - slope * mx) - slope * a for a, b in zip(x, y, strict=True)]
    observed = residualize(y, [[v] for v in x])
    assert observed == pytest.approx(expected, abs=1e-12)
    assert sum(observed) == pytest.approx(0, abs=1e-12)
    with pytest.raises(ValueError):
        residualize(y, [[v, v] for v in x])


def test_universe_versions_no_resurrection_or_symbol_inference():
    rows = [
        {"instrument_id": "A", "known_at": 1, "active": True, "kind": "spot"},
        {"instrument_id": "A", "known_at": 3, "active": False, "kind": "spot"},
        {"instrument_id": "B", "known_at": 4, "active": True},
        {"instrument_id": "C", "known_at": 1, "active": True},
    ]
    original = copy.deepcopy(rows)
    result = select_universe(
        rows, [Rule("active", "eq", True), Rule("kind", "not_in", ["stable"])], cutoff=3
    )
    assert result["selected"] == []
    assert result["rejected"] == {"A": "FILTER:active", "C": "UNKNOWN:kind"}
    assert result["future_versions_excluded"] == 1
    assert rows == original
    with pytest.raises(ValueError):
        select_universe([rows[0], {**rows[0], "active": False}], [], cutoff=2)


def test_universe_sort_currency_ties_limit_and_unknown():
    rows = [
        {"instrument_id": a, "known_at": 1, "volume": 10, "volume_unit": "USDT"} for a in ["B", "A"]
    ]
    assert select_universe(rows, [], cutoff=1, sort_field="volume", limit=1)["selected"] == ["A"]
    assert select_universe(rows, [], cutoff=1, limit=0)["selected"] == []
    with pytest.raises(ValueError):
        select_universe(
            [rows[0], {**rows[1], "volume_unit": "USD"}], [], cutoff=1, sort_field="volume"
        )
    with pytest.raises(ValueError):
        select_universe([{**rows[0], "volume_unit": None}], [], cutoff=1, sort_field="volume")


def test_irregular_label_intervals_and_delayed_availability():
    labels = [
        LabelInterval(0, 1, 1),
        LabelInterval(1, 9, 9),
        LabelInterval(2, 3, 10),
        LabelInterval(4, 5, 5),
        LabelInterval(5, 6, 6),
        LabelInterval(8, 12, 12),
    ]
    result = walk_forward(labels, [(5, 8)])[0]
    assert result["train"] == [0]
    assert result["test"] == [4]
    assert result["excluded"]["1"] == "LABEL_OVERLAP_OR_GAP"
    assert result["excluded"]["2"] == "LABEL_NOT_AVAILABLE"
    assert result["excluded"]["3"] == "LABEL_OVERLAP_OR_GAP"
    with pytest.raises(ValueError):
        walk_forward(labels, [(5, 9), (8, 10)])


def test_forward_property_reference_enumeration():
    rng = random.Random(776)
    labels = [
        LabelInterval(i, i + (span := rng.randrange(8)), i + span + rng.randrange(4))
        for i in range(100)
    ]
    for gap in [0, 1, 4]:
        for split in walk_forward(labels, [(30, 40), (60, 70)], gap=gap):
            expected = [
                i
                for i, l in enumerate(labels)
                if l.end < split["start"] - gap and l.available < split["start"]
            ]
            assert split["train"] == expected
            assert not set(split["train"]) & set(split["test"])


def test_partial_fill_reservations_cancel_idempotence_fraction_oracle():
    ledger = ScenarioLedger({("A", "USDT"): "1000", ("B", "USDT"): "0"}, synthetic=True)
    ledger.submit("buy", contract(), "BUY", "2", "100", at=0, latency=10, fee_rate="0.001")
    assert ledger.free("A", "USDT") == Decimal("799.8")
    before = ledger.snapshot()
    with pytest.raises(ValueError):
        ledger.fill("early", "buy", "1", "99", at=9)
    assert ledger.snapshot() == before
    assert ledger.fill("f1", "buy", "0.5", "99", at=10)
    assert ledger.orders["buy"].state == "PARTIALLY_FILLED"
    assert not ledger.fill("f1", "buy", "0.5", "99", at=10)
    with pytest.raises(ValueError):
        ledger.fill("f1", "buy", "0.6", "99", at=10)
    ledger.cancel("buy", at=11)
    expected = Fraction(1000) - Fraction(1, 2) * 99 * Fraction(1001, 1000)
    assert Fraction(ledger.free("A", "USDT")) == expected
    assert ledger.free("A", "BTC") == Decimal("0.5")
    with pytest.raises(ValueError):
        ledger.fill("late", "buy", "1", "99", at=12)
    with pytest.raises(ValueError):
        ledger.submit("other", contract("B"), "BUY", "1", "100", at=12)
    ledger.submit("sell", contract(), "SELL", "0.5", "101", at=12)
    with pytest.raises(ValueError):
        ledger.submit("double", contract(), "SELL", "0.1", "101", at=12)
    ledger.fill("f2", "sell", "0.5", "102", at=13)
    assert ledger.orders["sell"].state == "FILLED"
    assert ledger.free("A", "BTC") == 0
    assert Fraction(ledger.free("A", "USDT")) == expected + 51


@pytest.mark.parametrize("qty,price", [("0", "1"), ("-1", "1"), ("NaN", "1"), ("1", "Infinity")])
def test_invalid_orders_are_atomic(qty, price):
    ledger = ScenarioLedger({("A", "USDT"): "100"}, synthetic=True)
    before = ledger.snapshot()
    with pytest.raises(ValueError):
        ledger.submit("bad", contract(), "BUY", qty, price, at=0)
    assert ledger.snapshot() == before


def test_simulation_contract_and_live_rejection():
    with pytest.raises(ValueError):
        ScenarioLedger({}, synthetic=False)
    with pytest.raises(ValueError):
        SpotContract("x", "v", "BTC", "USDT", "contract", "USDT/BTC", "USDT")


def test_registry_immutable_compare_hash_and_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIPTO_ROOT", str(tmp_path))
    store = RunStore(tmp_path / "runs")
    common = {
        "artifacts": {"results": {"valid": True}},
        "inputs": {"data": "a" * 64},
        "code_version": "abc",
    }
    p = store.create({"n": 1}, {"score": 1}, run_id="one", **common)
    store.create({"n": 2}, {"score": 2}, run_id="two", **common)
    assert store.verify("one")["economic_validation"] is False
    assert len(store.list_runs()) == 2
    assert store.compare("one", "two")["score"] == {"left": 1, "right": 2}
    with pytest.raises(FileExistsError):
        store.create({}, {}, run_id="one", **common)
    with pytest.raises(ValueError):
        store.create({}, {"score": float("nan")}, run_id="bad", **common)
    assert not (store.root / "bad").exists()
    (p / "metrics.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        store.verify("one")


def test_registry_paths_and_reserved_names(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIPTO_ROOT", str(tmp_path))
    store = RunStore(tmp_path)
    with pytest.raises(ValueError):
        store.create({}, {}, artifacts={"config": {}}, inputs={}, code_version="v")
    with pytest.raises(ValueError):
        store.create({}, {}, artifacts={"../escape": {}}, inputs={}, code_version="v")
    with pytest.raises(ValueError):
        store.verify("../escape")


def test_cli_composition_with_registered_artifacts(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CRIPTO_ROOT", str(tmp_path))
    main(["demo", "--store", str(tmp_path / "runs"), "--run-id", "demo"])
    out = json.loads(capsys.readouterr().out)
    assert out["metrics"]["capability_outputs"] == 4
    manifest = RunStore(tmp_path / "runs").verify("demo")
    assert manifest["inputs"]["config"]
    payload = json.loads((tmp_path / "runs/demo/results.json").read_text())
    assert payload["simulation"]["orders"]["one"]["state"] == "CANCELED"
    assert payload["universe"]["selected"] == ["SIM:A/USD"]
    assert evaluate(demo_config()) == payload


def test_existing_cli_dispatches_research_without_pipeline(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CRIPTO_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "sys.argv", ["cripto-predictor", "research", "list", "--store", str(tmp_path / "none")]
    )
    from GarimpoInvestimentos.cli import main as entry

    entry()
    assert json.loads(capsys.readouterr().out) == []


def test_registry_input_hash_tracks_exact_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CRIPTO_ROOT", str(tmp_path))
    raw = json.dumps(demo_config(), separators=(",", ":")).encode()
    path = tmp_path / "input.json"
    path.write_bytes(raw)
    main(["run", "--input", str(path), "--store", str(tmp_path / "runs"), "--run-id", "input"])
    capsys.readouterr()
    assert (
        RunStore(tmp_path / "runs").verify("input")["inputs"]["config"]
        == hashlib.sha256(raw).hexdigest()
    )


def test_scenario_common_transitions_agree_with_native_execution():
    from datetime import UTC, datetime, timedelta

    from GarimpoInvestimentos.trading import execution
    from GarimpoInvestimentos.trading.contracts import (
        Fill,
        Instrument,
        Liquidity,
        Order,
        OrderSide,
        OrderStatus,
        OrderType,
    )

    now = datetime(2026, 1, 1, tzinfo=UTC)
    native = execution.accept(
        Order(
            "one",
            "scenario",
            Instrument("BTCUSDT", "A", "spot"),
            OrderSide.BUY,
            OrderType.LIMIT,
            2,
            OrderStatus.NEW,
            now,
            limit_price=100,
        ),
        accepted_at=now,
    )
    ledger = ScenarioLedger({("A", "USDT"): "1000"}, synthetic=True)
    ledger.submit("one", contract(), "BUY", "2", "100", at=0)
    fill = Fill("f1", "one", 0.5, 99, 0, Liquidity.TAKER, now + timedelta(seconds=1))
    native = execution.apply_fill(native, fill)
    ledger.fill("f1", "one", "0.5", "99", at=1)
    assert native.status.value.upper() == ledger.orders["one"].state
    assert native.filled_qty == float(ledger.orders["one"].filled)
    assert execution.apply_fill(native, fill) == native
    assert ledger.fill("f1", "one", "0.5", "99", at=1) is False
    native = execution.cancel(native, cancelled_at=now + timedelta(seconds=2))
    ledger.cancel("one", at=2)
    assert native.status is OrderStatus.CANCELLED
    assert ledger.orders["one"].state == "CANCELED"
    assert ledger.free("A", "USDT") == Decimal("950.5")
