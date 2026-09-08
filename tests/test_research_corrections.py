import gzip
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.audit_basis_sources import END, HOUR, START, rebuild
from scripts.plan_btc_hedge_v3 import saved_sources, validate_timing
from scripts.research_io import Ledger, encoded, exclusive, integer, sha, strict_json, write_atomic


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "123", None])
def test_bad_timestamp_rejected(value):
    meta = dict(status=200, request_start_ns=value, received_ns=value)
    with pytest.raises(ValueError):
        validate_timing(meta, meta)


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_strict_json_rejects_ambiguous_or_nonfinite_values(raw):
    with pytest.raises(ValueError):
        strict_json(raw)


def test_atomic_write_does_not_replace_valid_state_with_nan(tmp_path):
    path = tmp_path / "status.json"
    write_atomic(path, {"ok": 1})
    with pytest.raises(ValueError):
        write_atomic(path, {"bad": float("nan")})
    assert json.loads(path.read_bytes()) == {"ok": 1}


def test_ledger_rejects_duplicate_corruption_and_partial_tail(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger(path)
    ledger.append("DECISION", "a", {}, "now")
    with pytest.raises(ValueError):
        ledger.append("DECISION", "a", {}, "later")
    assert len(Ledger(path).rows) == 1
    original = path.read_bytes()
    path.write_bytes(original.replace(b'"now"', b'"bad"'))
    with pytest.raises(ValueError):
        Ledger(path)
    path.write_bytes(original[:-1])
    with pytest.raises(ValueError):
        Ledger(path)


def test_process_lock_prevents_overlap(tmp_path):
    with exclusive(tmp_path), pytest.raises(FileExistsError), exclusive(tmp_path):
        pass


def test_second_normalizer_strips_future_cutoff_and_converts_microseconds():
    row = [START * 1000, "10", "11", "9", "10", "100", (START + HOUR) * 1000 - 1, "1000"]
    result = rebuild([row, [END, "12", "999", "1", "999", "1", END + HOUR - 1, "999"]], "bars")
    assert result[0][0] == START and result[0][6] == START + HOUR - 1
    assert result[1] == [END, "12"]


@pytest.mark.parametrize("field", [5, 7])
def test_second_normalizer_rejects_nonfinite_volume(field):
    row = [START, "10", "11", "9", "10", "100", START + HOUR - 1, "1000"]
    row[field] = "NaN"
    with pytest.raises(ValueError):
        rebuild([row], "bars")


def test_integer_and_encoder_do_not_silently_coerce():
    assert integer(2) == 2
    with pytest.raises(ValueError):
        integer(2.0)
    assert encoded({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def saved_quote_fixture(directory):
    (directory / "raw").mkdir()
    info = {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "baseCommissionPrecision": 8,
                "filters": [
                    {
                        "filterType": "LOT_SIZE",
                        "stepSize": "0.001",
                        "minQty": "0.001",
                        "maxQty": "1000",
                    },
                    {"filterType": "MIN_NOTIONAL", "minNotional": "5"},
                ],
            }
        ]
    }
    book = {"bids": [["99.9", "100"]], "asks": [["100", "100"]]}
    record = {"snapshots": [{"index": 0, "freshness_pass": True}], "sources": []}
    for venue in ("spot", "future"):
        prefix = (
            "https://api.binance.com/api/v3/"
            if venue == "spot"
            else "https://fapi.binance.com/fapi/v1/"
        )
        for suffix, payload in (("info", info), ("00", book)):
            raw = encoded(payload)
            name = venue + "_" + suffix
            (directory / "raw" / (name + ".bin.gz")).write_bytes(gzip.compress(raw))
            record["sources"].append(
                {
                    "name": name,
                    "url": prefix
                    + ("exchangeInfo" if suffix == "info" else "depth?symbol=BTCUSDT&limit=100"),
                    "status": 200,
                    "sha256": sha(raw),
                    "request_start_ns": 1_000_000_000,
                    "received_ns": 1_100_000_000,
                }
            )
    (directory / "diagnostic.json").write_bytes(encoded(record))
    return record


@pytest.mark.parametrize("failure", ["duplicate", "path", "host", "missing", "sample_duplicate"])
def test_saved_quote_identity_failures_are_rejected(tmp_path, failure):
    record = saved_quote_fixture(tmp_path)
    if failure == "duplicate":
        record["sources"].append(record["sources"][0])
    elif failure == "path":
        record["sources"][0]["name"] = "../../outside"
    elif failure == "host":
        record["sources"][0]["url"] = "https://example.org/api/v3/exchangeInfo"
    elif failure == "missing":
        record["sources"].pop()
    else:
        record["snapshots"].append(record["snapshots"][0])
    (tmp_path / "diagnostic.json").write_bytes(encoded(record))
    with pytest.raises(ValueError):
        saved_sources(tmp_path)


def test_rejected_saved_quote_produces_nonzero_cli_status(tmp_path):
    record = saved_quote_fixture(tmp_path)
    record["snapshots"][0]["freshness_pass"] = False
    (tmp_path / "diagnostic.json").write_bytes(encoded(record))
    output = tmp_path / "result.json"
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.plan_btc_hedge_v3",
            "--diagnostic",
            str(tmp_path),
            "--output",
            str(output),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 1 and "REJECTED" in run.stdout
    assert strict_json(output.read_bytes())["plans"][0]["plan"] is None
