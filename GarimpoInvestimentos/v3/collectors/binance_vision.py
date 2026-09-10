"""Public Binance archives with mandatory checksum and explicit market identity.

Spot klines use /data/spot; funding and OI use /data/futures/um.
Spot archive timestamps from 2025-01-01 are microseconds, normalized to ms.
Cached archives are immutable observed versions, not historical availability proof.
Official schema: https://github.com/binance/binance-public-data/blob/master/README.md
"""

import csv
import hashlib
import io
import json
import logging
import re
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from GarimpoInvestimentos.core.paths import CACHE_DIR
from GarimpoInvestimentos.durable_io import atomic_write, file_lock
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord
from GarimpoInvestimentos.v3.collectors.oi_collector import OIRecord
from GarimpoInvestimentos.v3.collectors.record_io import unique_records, validate_observation
from GarimpoInvestimentos.v3.collectors.spot_collector import KlineRecord

logger = logging.getLogger(__name__)

_BASE = "https://data.binance.vision/data/futures/um"
_CACHE_DIR = CACHE_DIR / "v3" / "binance_vision"
_HTTP_TIMEOUT = 120.0


# ------------------------------------------------------------------ #
# Download + cache + checksum                                         #
# ------------------------------------------------------------------ #


def _cache_path(rel_url: str, market: str = "futures/um") -> Path:
    if (
        market not in {"futures/um", "spot"}
        or ".." in rel_url
        or "\\" in rel_url
        or rel_url.startswith("/")
    ):
        raise ValueError("caminho de arquivo Vision invalido")
    return _CACHE_DIR / "verified_v2" / market.replace("/", "_") / rel_url.replace("/", "__")


def _verify_checksum(content: bytes, checksum_text: str) -> bool:
    fields = checksum_text.strip().split()
    return bool(
        fields
        and re.fullmatch(r"[a-fA-F0-9]{64}", fields[0])
        and fields[0].lower() == hashlib.sha256(content).hexdigest()
    )


def _download_zip(
    rel_url: str, client: httpx.Client, *, market: str = "futures/um"
) -> bytes | None:
    cache = _cache_path(rel_url, market)
    checksum = cache.with_suffix(cache.suffix + ".CHECKSUM")
    url = f"https://data.binance.vision/data/{market}/{rel_url}"
    with file_lock(cache):
        if cache.exists():
            content = cache.read_bytes()
            if not checksum.exists() or not _verify_checksum(
                content, checksum.read_text(encoding="utf-8")
            ):
                raise OSError(f"Cache Vision sem checksum valido: {cache}")
            return content
        response = client.get(url)
        if response.status_code == 404:
            logger.warning("Arquivo Vision ausente: %s", url)
            return None
        response.raise_for_status()
        content = response.content
        cr = client.get(f"{url}.CHECKSUM")
        cr.raise_for_status()
        if not _verify_checksum(content, cr.text):
            raise OSError(f"Checksum SHA256 nao confere para {url}")
        # Publish data last: a data file always has its source/checksum receipt.
        atomic_write(checksum, cr.text.encode("utf-8"))
        receipt = {
            "url": url,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "sha256": hashlib.sha256(content).hexdigest(),
            "historical_availability_verified": False,
        }
        atomic_write(
            cache.with_suffix(".receipt.json"), json.dumps(receipt, sort_keys=True).encode("utf-8")
        )
        atomic_write(cache, content)
        return content


def _read_csv_rows(zip_bytes: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        if (
            len(files) != 1
            or not files[0].filename.lower().endswith(".csv")
            or files[0].file_size > 64 * 1024 * 1024
        ):
            raise ValueError("Vision ZIP exige um CSV de ate 64 MiB")
        text = archive.read(files[0]).decode("utf-8-sig")
    rows = [row for row in csv.reader(io.StringIO(text)) if row]
    if rows and rows[0][0].strip().lower() in {"calc_time", "open_time", "create_time"}:
        rows = rows[1:]
    return rows


# ------------------------------------------------------------------ #
# Iteradores de período                                               #
# ------------------------------------------------------------------ #


def _months(start: datetime, end: datetime):
    """Gera (ano, mês) de start até end inclusive."""
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def _days(start: datetime, end: datetime):
    """Gera datas (date) de start até end inclusive."""
    d = start.date()
    last = end.date()
    while d <= last:
        yield d
        d += timedelta(days=1)


# ------------------------------------------------------------------ #
# Loaders públicos — devolvem os dataclasses canônicos                #
# ------------------------------------------------------------------ #


def load_funding_vision(symbol: str, start_ms: int, end_ms: int) -> list[FundingRecord]:
    """Funding rate histórico (arquivos mensais)."""
    validate_observation(symbol, start_ms, {})
    if end_ms < start_ms:
        raise ValueError("intervalo Vision invalido")
    start = datetime.fromtimestamp(start_ms / 1000, tz=UTC)
    end = datetime.fromtimestamp(end_ms / 1000, tz=UTC)
    out: list[FundingRecord] = []
    with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
        for y, m in _months(start, end):
            rel = f"monthly/fundingRate/{symbol}/{symbol}-fundingRate-{y:04d}-{m:02d}.zip"
            zb = _download_zip(rel, client)
            if zb is None:
                continue
            for row in _read_csv_rows(zb):
                # calc_time, funding_interval_hours, last_funding_rate
                ts = int(row[0])
                if start_ms <= ts <= end_ms:
                    out.append(
                        FundingRecord(
                            symbol=symbol,
                            funding_time_ms=ts,
                            funding_rate=float(row[2]),
                            mark_price=0.0,  # Vision não fornece mark_price no funding
                        )
                    )
    out.sort(key=lambda r: r.funding_time_ms)
    logger.info("binance_vision[%s]: %d funding records", symbol, len(out))
    return unique_records(out, "funding_time_ms")


def load_klines_vision(
    symbol: str, start_ms: int, end_ms: int, interval: str = "1h"
) -> list[KlineRecord]:
    """Klines histórico (arquivos mensais)."""
    validate_observation(symbol, start_ms, {})
    if end_ms < start_ms:
        raise ValueError("intervalo Vision invalido")
    if interval != "1h":
        raise ValueError("KlineRecord deste pipeline representa somente 1h")
    available_at_ms = min(end_ms, int(datetime.now(UTC).timestamp() * 1000))
    start = datetime.fromtimestamp(start_ms / 1000, tz=UTC)
    end = datetime.fromtimestamp(end_ms / 1000, tz=UTC)
    out: list[KlineRecord] = []
    with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
        for y, m in _months(start, end):
            rel = f"monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{y:04d}-{m:02d}.zip"
            zb = _download_zip(rel, client, market="spot")
            if zb is None:
                continue
            for row in _read_csv_rows(zb):
                # open_time, open, high, low, close, volume, close_time, ...
                raw_ts = int(row[0])
                ts = raw_ts // 1000 if y >= 2025 else raw_ts
                if y >= 2025 and raw_ts % 1000:
                    raise ValueError("open_time nao alinhado em ms")
                if start_ms <= ts and ts + 3_600_000 <= available_at_ms:
                    out.append(
                        KlineRecord(
                            symbol=symbol,
                            open_ms=ts,
                            close=float(row[4]),
                            volume=float(row[5]),
                        )
                    )
    out.sort(key=lambda r: r.open_ms)
    logger.info("binance_vision[%s]: %d klines (%s)", symbol, len(out), interval)
    return unique_records(out, "open_ms")


def load_oi_vision(symbol: str, start_ms: int, end_ms: int) -> list[OIRecord]:
    """
    Open Interest histórico via dataset 'metrics' (arquivos DIÁRIOS, 5min).
    create_time é string 'YYYY-MM-DD HH:MM:SS' em UTC.
    """
    validate_observation(symbol, start_ms, {})
    if end_ms < start_ms:
        raise ValueError("intervalo Vision invalido")
    start = datetime.fromtimestamp(start_ms / 1000, tz=UTC)
    end = datetime.fromtimestamp(end_ms / 1000, tz=UTC)
    out: list[OIRecord] = []
    missing = 0
    with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
        for d in _days(start, end):
            rel = f"daily/metrics/{symbol}/{symbol}-metrics-{d.isoformat()}.zip"
            zb = _download_zip(rel, client)
            if zb is None:
                missing += 1
                continue
            for row in _read_csv_rows(zb):
                # create_time, symbol, sum_open_interest, sum_open_interest_value, ...
                ts = _parse_metrics_time(row[0])
                if ts is None or row[1] != symbol:
                    raise ValueError("metrics Vision com data/symbol divergente")
                if not start_ms <= ts <= end_ms:
                    continue
                out.append(OIRecord(symbol, ts, float(row[2]), float(row[3])))
    out.sort(key=lambda r: r.timestamp_ms)
    if missing:
        logger.warning("binance_vision[%s]: %d dias de metrics ausentes no range", symbol, missing)
    logger.info("binance_vision[%s]: %d OI records (metrics 5min)", symbol, len(out))
    return unique_records(out, "timestamp_ms")


def _parse_metrics_time(s: str) -> int | None:
    """'2024-01-15 00:05:00' (UTC) → epoch ms."""
    try:
        dt = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None
