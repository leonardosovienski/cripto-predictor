import gzip

import httpx
import pytest

from scripts.carry_public import PublicSource, verify_sources
from scripts.research_io import strict_json


def source(tmp_path, handler):
    value = PublicSource(tmp_path)
    value.client.close()
    value.client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    return value


@pytest.mark.parametrize(
    "name,params",
    [("order", {}), ("spot_book", {"symbol": "ETHUSDT"}), ("spot_time", {"apiKey": "unused"})],
)
def test_unregistered_endpoint_symbol_and_parameter_never_reach_network(tmp_path, name, params):
    calls = []
    value = source(tmp_path, lambda r: calls.append(r))
    try:
        with pytest.raises(ValueError):
            value.get(name, params)
        assert not calls and value.requests == 0
    finally:
        value.close()


def test_public_capture_is_get_only_persisted_and_tamper_evident(tmp_path):
    def reply(request):
        assert request.method == "GET" and not request.content
        assert "authorization" not in request.headers and "x-mbx-apikey" not in request.headers
        return httpx.Response(200, json={"serverTime": 123})

    value = source(tmp_path, reply)
    try:
        result, meta = value.get("spot_time")
        assert result == {"serverTime": 123}
        verify_sources(tmp_path, [meta])
        (tmp_path / meta["raw_file"]).write_bytes(gzip.compress(b"{}"))
        with pytest.raises(ValueError, match="Changed"):
            verify_sources(tmp_path, [meta])
    finally:
        value.close()


@pytest.mark.parametrize("status", [302, 429, 500])
def test_failed_http_response_is_saved_without_retry(tmp_path, status):
    value = source(tmp_path, lambda r: httpx.Response(status, json={"error": "failure"}))
    try:
        with pytest.raises(httpx.HTTPStatusError):
            value.get("spot_time")
        assert value.requests == 1
        assert value.records[0]["status"] == status
        verify_sources(tmp_path, value.records)
    finally:
        value.close()


def test_actual_stream_bytes_cannot_exceed_budget(tmp_path):
    value = source(tmp_path, lambda r: httpx.Response(200, content=b"1234567890"))
    value.bytes = 19_999_995
    try:
        with pytest.raises(ValueError, match="budget"):
            value.get("spot_time")
        assert value.bytes == 20_000_000
        meta = value.records[0]
        assert not meta["complete_response"]
        assert gzip.decompress((tmp_path / meta["raw_file"]).read_bytes()) == b"12345"
        with pytest.raises(ValueError, match="budget"):
            value.get("future_time")
        assert value.requests == 1
    finally:
        value.close()


def test_request_count_and_saved_metadata_identity_are_enforced(tmp_path):
    value = source(tmp_path, lambda r: httpx.Response(200, json={"serverTime": 123}))
    try:
        _, meta = value.get("spot_time")
        path = tmp_path / "raw" / (meta["id"] + ".json")
        changed = strict_json(path.read_bytes())
        changed["status"] = 201
        import json

        path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(ValueError, match="Changed"):
            verify_sources(tmp_path, [meta])
        value.requests = 16
        with pytest.raises(ValueError, match="budget"):
            value.get("spot_time")
    finally:
        value.close()
