"""Synthetic accounting/control tests; these are NOT strategy-performance evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from decimal import Decimal

import httpx
import pytest

from GarimpoInvestimentos.profit_research import (
    COST_NAMES,
    SOURCE,
    assess,
    capture_yields,
    compare,
    discover_yields,
    loads,
    main,
    number,
    transition,
    yield_return,
)


def case() -> dict:
    return {
        "id": "SYNTHETIC-ONLY",
        "family": "any-crypto-strategy",
        "asset": "SYNTHETIC",
        "venue": "SYNTHETIC",
        "currency": "USDT",
        "capital": "5000",
        "period_start": "2026-06-16T00:00:00Z",
        "period_end": "2026-09-08T00:00:00Z",
        "scenario": "SYNTHETIC",
        "evidence_kind": "SCENARIO",
        "evidence_ref": "Synthetic test fixture; no market data",
        "cashflows": {"funding": "17.22", "basis": "-0.12"},
        "costs": {
            "execution": "18.32",
            "financing": "0",
            "infrastructure": "5.75",
            "tax": "0",
            "conversion": "0",
            "other": "0",
        },
        "cost_notes": {k: "Synthetic assumption only; not a real fee estimate" for k in COST_NAMES},
        "risk_limit": "100",
        "stress_loss": "80",
        "risk_evidence": "Synthetic stress scenario, not calibrated",
        "execution_evidence": "Synthetic execution assumption, not measured",
    }


def pool(**overrides) -> dict:
    row = {
        "pool": "test-pool",
        "chain": "Test",
        "project": "test-project",
        "symbol": "USDC",
        "tvlUsd": 1000000,
        "apyBase": 5,
        "apyReward": 2,
    }
    row.update(overrides)
    return row


def snapshot(rows: list[dict]) -> dict:
    raw = json.dumps({"status": "success", "data": rows})
    return {
        "source": SOURCE,
        "retrieved_at": "2026-09-08T12:00:00Z",
        "sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "raw_json": raw,
    }


@pytest.mark.parametrize(
    "value", [True, False, None, "nan", "Infinity", float("nan"), float("inf"), {}, [], "bad"]
)
def test_invalid_numbers(value):
    with pytest.raises(ValueError):
        number(value)


def test_negative_funding_and_cost_break_even():
    row = assess(case())
    assert Decimal(row["net"]) == Decimal("-6.97")
    assert Decimal(row["break_even_execution_budget"]) == Decimal("11.35")
    assert Decimal(row["cost_reduction_to_break_even"]) == Decimal("6.97")
    assert row["research_status"] == "BLOCKED"
    assert not row["capital_permission"]


@pytest.mark.parametrize("category", COST_NAMES)
def test_unknown_cost_is_not_zero(category):
    c = case()
    c["costs"][category] = None
    result = assess(c)
    assert result["net"] is None
    assert "UNKNOWN_COST:" + category in result["blockers"]
    assert result["research_status"] == "BLOCKED"


def test_positive_arithmetic_is_not_capital_authorization():
    c = case()
    c["cashflows"]["funding"] = "100"
    result = assess(c)
    assert result["research_status"] == "CANDIDATE_FOR_VALIDATION"
    assert result["evidence_independently_verified"] is False
    assert result["capital_permission"] is False
    assert Decimal(result["return_pct"]) == Decimal("75.81") / 50


@pytest.mark.parametrize(
    "field,value",
    [
        ("stress_loss", None),
        ("stress_loss", "101"),
        ("risk_evidence", ""),
        ("execution_evidence", None),
    ],
)
def test_missing_or_excess_risk_blocks_positive_case(field, value):
    c = case()
    c["cashflows"]["funding"] = "100"
    c[field] = value
    assert assess(c)["research_status"] == "BLOCKED"


def test_unknown_cashflow_and_invalid_known_cashflow():
    c = case()
    c["cashflows"]["basis"] = None
    assert assess(c)["net"] is None
    c["cashflows"]["funding"] = "nan"
    with pytest.raises(ValueError):
        assess(c)


@pytest.mark.parametrize(
    "field,value",
    [
        ("capital", 0),
        ("risk_limit", "5001"),
        ("period_end", "2026-01-01T00:00:00Z"),
        ("period_start", "2026-06-16"),
        ("evidence_kind", "REAL_PROFIT"),
    ],
)
def test_invalid_case_contract(field, value):
    c = case()
    c[field] = value
    with pytest.raises(ValueError):
        assess(c)


def test_costs_must_be_complete_nonnegative_and_justified():
    c = case()
    c["costs"].pop("tax")
    with pytest.raises(ValueError):
        assess(c)
    c = case()
    c["costs"]["tax"] = -1
    with pytest.raises(ValueError):
        assess(c)
    c = case()
    c["cost_notes"]["tax"] = " "
    with pytest.raises(ValueError):
        assess(c)


@pytest.mark.parametrize(
    "field,value",
    [
        ("capital", "10000"),
        ("currency", "BRL"),
        ("period_start", "2026-06-17T00:00:00Z"),
        ("period_end", "2026-09-07T00:00:00Z"),
        ("scenario", "adverse"),
        ("evidence_kind", "ADAPTIVE_BACKTEST"),
    ],
)
def test_incomparable_cases_are_not_ranked(field, value):
    a, b = case(), case()
    b["id"], b[field] = "OTHER", value
    with pytest.raises(ValueError):
        compare([a, b])


def test_rank_any_asset_and_family_without_summing_capital():
    a, b, c = case(), case(), case()
    a["cashflows"]["funding"] = "100"
    b.update(id="OTHER", family="lending", asset="USDC")
    b["cashflows"]["funding"] = "90"
    c["id"] = "BLOCKED"
    result = compare([b, c, a])
    assert result["ranking"] == [a["id"], b["id"]]
    assert result["blocker_counts"]["NON_POSITIVE_NET"] == 1
    assert "total_profit" not in result
    with pytest.raises(ValueError):
        compare([a, copy.deepcopy(a)])


def transition_case() -> dict:
    return {
        "current_instrument": "venue:BTCUSDT:perp:USDT",
        "target_instrument": "venue:BTCUSDT:perp:USDT",
        "current_quantity": "-1",
        "target_quantity": "-1.2",
        "price": "100",
        "quantity_step": "0.1",
        "cost_bps": "10",
    }


@pytest.mark.parametrize(
    "target,delta,difference",
    [
        ("-1", "0", "0.20"),
        ("-1.2", "-0.2", "0.20"),
        ("-0.5", "0.5", "0.10"),
        ("0", "1", "0"),
        ("1", "2", "0"),
    ],
)
def test_turnover_adjust_hold_reduce_close_reverse(target, delta, difference):
    spec = transition_case()
    spec["target_quantity"] = target
    result = transition(spec)
    assert Decimal(result["signed_quantity_delta"]) == Decimal(delta)
    assert Decimal(result["modelled_cost_difference"]) == Decimal(difference)
    assert result["capital_permission"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_instrument", "another:venue"),
        ("quantity_step", "0"),
        ("target_quantity", "0.15"),
        ("price", "0"),
        ("cost_bps", "-1"),
    ],
)
def test_invalid_transition(field, value):
    spec = transition_case()
    spec[field] = value
    with pytest.raises(ValueError):
        transition(spec)


def test_yield_convention_and_units_are_explicit():
    assert yield_return("10", 365, "APY") == Decimal("0.1")
    assert yield_return("10", 365, "APR") == Decimal("0.1")
    assert yield_return("10", 30, "APY") < yield_return("10", 30, "APR")
    assert yield_return("-1", 30, "APR") < 0
    for args in [(10, 0, "APR"), (10, 30, "unknown"), (-100, 30, "APY")]:
        with pytest.raises(ValueError):
            yield_return(*args)


def test_discovery_keeps_stables_wrapped_and_unknown_assets():
    result = discover_yields(
        snapshot(
            [
                pool(pool=str(i), symbol=name)
                for i, name in enumerate(["USDC", "WSTETH", "UNKNOWN-TOKEN"])
            ]
        )
    )
    assert len(result["candidates"]) == 3
    assert result["source_freshness_verified"] is False
    assert all(not c["capital_permission"] for c in result["candidates"])
    assert result["candidates"][0]["apyBase"] == "5"
    assert result["candidates"][0]["apyReward"] == "2"


def test_missing_base_never_falls_back_to_aggregate_apy():
    row = discover_yields(snapshot([pool(apyBase=None, apy=999, apyReward=None)]))["candidates"][0]
    assert row["apyBase"] is None
    assert row["apyReward"] is None
    assert "BASE_YIELD" in row["needs"]


def test_invalid_and_all_duplicate_rows_are_reported_not_silently_selected():
    result = discover_yields(
        snapshot(
            [pool(), pool(apyBase=50), pool(pool="bad", tvlUsd=-1), pool(pool="nan", apyBase="nan")]
        )
    )
    assert len(result["rejected"]) == 4
    assert result["candidates"] == []
    assert result["input_count"] == 4


def test_snapshot_integrity_source_payload_and_timezone():
    s = snapshot([pool()])
    for field, value in [
        ("raw_json", "{}"),
        ("source", "https://other.invalid"),
        ("retrieved_at", "2026-09-08"),
    ]:
        changed = dict(s)
        changed[field] = value
        with pytest.raises(ValueError):
            discover_yields(changed)
    s["raw_json"] = '{"status":"error","data":[]}'
    s["sha256"] = hashlib.sha256(s["raw_json"].encode()).hexdigest()
    with pytest.raises(ValueError):
        discover_yields(s)


@pytest.mark.parametrize("raw", ['{"cost":0,"cost":10}', '{"cost":NaN}', '{"cost":Infinity}'])
def test_ambiguous_json_rejected(raw):
    with pytest.raises(ValueError):
        loads(raw)


def test_cli_and_file_hash(tmp_path, capsys):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps([case()]), encoding="utf-8")
    assert main(["evaluate", str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["input_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["cases"][0]["research_status"] == "BLOCKED"
    path.write_text("{}", encoding="utf-8")
    assert main(["evaluate", str(path)]) == 2
    assert not json.loads(capsys.readouterr().err)["capital_permission"]
    path.write_text(json.dumps(transition_case()), encoding="utf-8")
    assert main(["transition", str(path)]) == 0
    path.write_text(json.dumps(snapshot([pool()])), encoding="utf-8")
    assert main(["discover-yields", str(path)]) == 0


def test_capture_is_get_only_and_does_not_overwrite(tmp_path, monkeypatch):
    def handler(request):
        assert request.method == "GET" and str(request.url) == SOURCE
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"status": "success", "data": [pool()]})

    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    path = tmp_path / "snapshot.json"
    capture_yields(path)
    before = path.read_bytes()
    assert discover_yields(json.loads(before))["input_count"] == 1
    with pytest.raises(FileExistsError):
        capture_yields(path)
    assert path.read_bytes() == before


def test_network_failure_is_not_empty_success(tmp_path, monkeypatch, capsys):
    def handler(request):
        raise httpx.ConnectError("not a market response", request=request)

    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    path = tmp_path / "snapshot.json"
    assert main(["capture-yields", str(path)]) == 2
    assert not path.exists()
    assert "request failed" in capsys.readouterr().err
