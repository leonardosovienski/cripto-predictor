import copy
from pathlib import Path

import httpx
import pytest

from scripts.audit_immediate_decimal import rebuild
from scripts.immediate_public import Source
from scripts.research_io import strict_json
from scripts.run_immediate_audit import DAY, HOUR, daily_rows, historical, stamps


def inputs():
    p = strict_json(
        (
            Path(__file__).resolve().parents[1]
            / "docs/evidence/immediate_audit_20260908/protocol.json"
        ).read_bytes()
    )
    start, stop = stamps(p)
    spot = [
        [t, "100", "101", "99", "100", "10", t + DAY - 1, "1000"]
        for t in range(start, stop + DAY, DAY)
    ]
    future = [
        [t, "102", "103", "101", "102", "10", t + DAY - 1, "1000"]
        for t in range(start, stop + DAY, DAY)
    ]
    marks = [
        [t, "102", "103", "101", "102", "0", t + HOUR - 1, "0"] for t in range(start, stop, HOUR)
    ]
    fund = [
        {"symbol": "BTCUSDT", "fundingTime": t, "fundingRate": ".0001", "markPrice": "102"}
        for t in range(start + 8 * HOUR, stop, 8 * HOUR)
    ]
    fund[0]["fundingRate"] = "-.0001"
    return p, spot, future, fund, marks


def test_separate_decimal_accounting_matches_float_and_charges_costs():
    p, s, f, funding, marks = inputs()
    actual = historical(p, s, f, funding, marks)
    q, expected = rebuild(
        p, {"spot_daily": s, "future_daily": f, "funding": funding, "mark": marks}
    )
    assert actual["quantity_btc"] == float(q)
    for name in p["costs"]:
        for key, value in expected[name].items():
            if isinstance(value, list):
                assert actual["cases"][name][key] == pytest.approx(
                    list(map(float, value)), abs=1e-7
                )
            else:
                assert actual["cases"][name][key] == pytest.approx(float(value), abs=1e-7)
    assert (
        actual["cases"]["stress"]["profit_usdt"]
        < actual["cases"]["adverse"]["profit_usdt"]
        < actual["cases"]["base"]["profit_usdt"]
    )


@pytest.mark.parametrize("kind", ["missing", "duplicate", "nan", "bad_close"])
def test_daily_data_errors_do_not_become_valid_profit(kind):
    p, rows, *_ = inputs()
    if kind == "missing":
        rows.pop(2)
    elif kind == "duplicate":
        rows.append(rows[1])
    elif kind == "nan":
        rows[0][4] = "NaN"
    else:
        rows[0][6] -= 1
    with pytest.raises(ValueError):
        daily_rows(rows, *stamps(p))


def test_unclosed_cutoff_candle_cannot_leak_high_low_close():
    p, s, f, fund, marks = inputs()
    original = historical(p, s, f, fund, marks)
    altered = copy.deepcopy(s)
    altered[-1][2:6] = ["NaN", "99999999", "0", "NaN"]
    assert original == historical(p, altered, f, fund, marks)


def test_public_collector_saves_get_only_and_rejects_private_endpoint(tmp_path):
    source = Source(tmp_path)
    source.client.close()
    calls = []

    def reply(request):
        calls.append(request)
        assert (
            request.method == "GET"
            and "authorization" not in request.headers
            and "x-mbx-apikey" not in request.headers
        )
        return httpx.Response(200, json={"serverTime": 123})

    source.client = httpx.Client(transport=httpx.MockTransport(reply), trust_env=False)
    try:
        row, meta = source.get("spot_time")
        assert row["serverTime"] == 123 and not meta["error"]
        assert (tmp_path / meta["raw_file"]).exists()
        with pytest.raises(ValueError):
            source.get("order", {"symbol": "BTCUSDT"})
        assert len(calls) == 1
    finally:
        source.client.close()


def test_public_http_failure_is_retained_and_never_retried(tmp_path):
    source = Source(tmp_path)
    source.client.close()
    source.client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(429, json={"error": "rate limit"}))
    )
    try:
        with pytest.raises(httpx.HTTPStatusError):
            source.get("spot_time")
        assert source.requests == 1 and source.records[0]["status"] == 429
        assert source.records[0]["error"]
    finally:
        source.client.close()
