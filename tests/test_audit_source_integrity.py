"""Source identity, observed vintages and immutable archive regression tests."""

import asyncio
import hashlib
import io
import zipfile
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from GarimpoInvestimentos.dpl.providers.dxy import DXYProvider
from GarimpoInvestimentos.v3.collectors import binance_vision as vision
from GarimpoInvestimentos.v3.macro_features import build_dxy_return, load_dxy_availability


def zipped(text):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("data.csv", text)
    return stream.getvalue()


@pytest.mark.parametrize("year,multiplier", [(2024, 1), (2025, 1000)])
def test_vision_uses_spot_market_and_normalizes_archive_units(monkeypatch, year, multiplier):
    ts = int(datetime(year, 1, 1, tzinfo=UTC).timestamp() * 1000)
    calls = []

    def download(url, _client, *, market):
        calls.append((url, market))
        return zipped(f"{ts * multiplier},99,101,99,100,7,{(ts + 3600000) * multiplier - 1}\n")

    monkeypatch.setattr(vision, "_download_zip", download)
    rows = vision.load_klines_vision("BTCUSDT", ts, ts + 3600000)
    assert [(row.open_ms, row.close, row.volume) for row in rows] == [(ts, 100, 7)]
    assert calls[0][1] == "spot"
    assert vision._cache_path(calls[0][0], "spot") != vision._cache_path(calls[0][0], "futures/um")


def test_vision_rejects_corrupt_cached_archive_without_overwriting_it(tmp_path, monkeypatch):
    monkeypatch.setattr(vision, "_CACHE_DIR", tmp_path)
    archive = zipped("1,2\n")

    def response(request):
        body = (
            hashlib.sha256(archive).hexdigest().encode() + b"  data.zip"
            if str(request.url).endswith(".CHECKSUM")
            else archive
        )
        return httpx.Response(200, content=body, request=request)

    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        assert vision._download_zip("data.zip", client, market="spot") == archive
        target = vision._cache_path("data.zip", "spot")
        target.write_bytes(b"corruption")
        with pytest.raises(OSError, match="checksum"):
            vision._download_zip("data.zip", client, market="spot")
        assert target.read_bytes() == b"corruption"


def test_archive_without_source_checksum_never_becomes_valid_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(vision, "_CACHE_DIR", tmp_path)
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    404 if str(req.url).endswith(".CHECKSUM") else 200,
                    content=zipped("1,2\n"),
                    request=req,
                )
            )
        ) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        vision._download_zip("data.zip", client)
    assert not vision._cache_path("data.zip").exists()


def test_current_fred_csv_cannot_backdate_a_revised_value(monkeypatch):
    async def csv(_self):
        return "observation_date,DTWEXBGS\n2026-08-31,118.5679\n2026-09-01,118.6568\n"

    monkeypatch.setattr(DXYProvider, "_get_csv", csv)
    before = datetime.now(UTC)
    points = asyncio.run(DXYProvider(publish_lag_days=0).fetch())
    after = datetime.now(UTC)
    assert all(before <= point.published_at <= after for point in points)
    assert all(point.vintage == point.published_at for point in points)
    assert all("publication_history_unverified" in point.quality_flags for point in points)


def test_weekly_fed_release_uses_actual_time_and_holiday_delay():
    # H.10/FRED publication observed 2026-09-08, after the Monday holiday.
    release = datetime(2026, 9, 8, 20, 16, tzinfo=UTC)
    closes = {date(2026, 9, 3): 118.1270, date(2026, 9, 4): 118.0732}
    before = SimpleNamespace(
        timestamp_exchange_ms=int((release - timedelta(milliseconds=1)).timestamp() * 1000)
    )
    after = SimpleNamespace(timestamp_exchange_ms=int(release.timestamp() * 1000))
    with pytest.raises(ValueError, match="available_at"):
        build_dxy_return([before, after], closes)
    values = build_dxy_return(
        [before, after], closes, available_at={day: release for day in closes}
    )
    assert values == pytest.approx([0, (118.0732 / 118.1270 - 1) * 100])


def test_two_column_dxy_csv_is_not_publication_evidence(tmp_path):
    target = tmp_path / "dxy.csv"
    target.write_text("date,close\n2026-09-03,118\n", encoding="utf-8")
    with pytest.raises(ValueError, match="published_at"):
        load_dxy_availability(target)
