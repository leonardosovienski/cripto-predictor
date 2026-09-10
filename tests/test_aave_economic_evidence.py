"""Reconcile the published research with original RPC responses and cash flows."""

import hashlib
import json
from fractions import Fraction
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parents[1] / "docs/evidence/aave_validation_20260910"
RAY = 10**27
POOL = "0x794a61358d6845594f94dc1db02a252b5b4814ad"
ASSET = "0xaf88d065e77c8cc2239327c5edb3a432268e5831"


def read(name):
    return json.loads((EVIDENCE / name).read_bytes())


def floor(value):
    return value.numerator // value.denominator


def test_public_aave_research_bytes_match_original_manifests():
    for name, digest in read("MANIFEST.json")["files"].items():
        path = (EVIDENCE / name).resolve()
        assert path.is_relative_to(EVIDENCE.resolve()), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    for section in (
        "history",
        "funded_costs",
        "execution_attempt01",
        "execution_receipts",
        "conversion_quote",
    ):
        for name, digest in read(f"{section}/manifest.json").items():
            assert hashlib.sha256((EVIDENCE / section / name).read_bytes()).hexdigest() == digest


def test_funded_cashflows_reconcile_to_original_rpc_income_indices():
    records = [
        json.loads(path.read_bytes()) for path in sorted((EVIDENCE / "history/raw").glob("*.json"))
    ]
    protocol = read("history/protocol.json")
    assert protocol["capital_permission"] is False
    signatures = {
        bytes.fromhex(row["request"]["params"][0][2:]).decode(): row["response"]["result"][:10]
        for row in records
        if row["request"]["method"] == "web3_sha3"
    }
    income_data = signatures["getReserveNormalizedIncome(address)"] + ASSET[2:].rjust(64, "0")
    indices = {}
    for point in read("history/history.json"):
        matches = [
            r
            for r in records
            if r["request"]["method"] == "eth_call"
            and r["request"]["params"] == [{"to": POOL, "data": income_data}, hex(point["number"])]
        ]
        assert len(matches) == 1
        raw_index = int(matches[0]["response"]["result"], 16)
        assert raw_index == int(point["normalized_income_ray"])
        assert abs(raw_index - int(point["reconstructed_income_ray"])) <= 1
        indices[point["boundary_utc"]] = raw_index
    assert list(indices) == protocol["boundaries_utc"]
    result = read("funded_costs/results.json")
    assert result["personal_profit_validated"] is False
    assert result["future_profit_validated"] is False
    for row in result["cases"]:
        initial = row["total_capital_usdc"] * 10**6
        exact_cost = Fraction(
            row["execution_cost_usdc"] + row["additional_cost_scenario_usdc"]
        ) + Fraction(25 * row["days"], 365)
        reserve = -floor(-exact_cost * 10**6)
        lent = initial - reserve
        scaled = floor(Fraction(lent * RAY, indices[row["start"]]))
        final = floor(Fraction(scaled * indices[row["end"]], RAY))
        assert Fraction(row["reserved_costs_usdc"]) == Fraction(reserve, 10**6)
        assert Fraction(row["lent_principal_usdc"]) == Fraction(lent, 10**6)
        assert Fraction(row["gross_interest_usdc"]) == Fraction(final - lent, 10**6)
        assert Fraction(row["final_equity_usdc"]) == Fraction(final, 10**6)
        assert Fraction(row["net_after_registered_costs_usdc"]) == Fraction(final - initial, 10**6)
    assert len(result["cases"]) == result["cashflow_reconciliations"] == 1728
