"""
Binance Vision — Data Lake histórico público (a "Quarta Via").

PROBLEMA RESOLVIDO:
    O endpoint REST futures/data/openInterestHist só serve ~30 dias de Open Interest.
    Isso inviabiliza o WFA histórico (≥217 dias) e, portanto, o Go/No-Go da Fase 1.

SOLUÇÃO:
    A Binance arquiva TODOS os dados de microestrutura de graça em ZIPs em
    https://data.binance.vision/ — anos de histórico, sem API key, sem rate limit
    de dados valiosos. Este módulo baixa, valida (SHA256) e parseia esses arquivos,
    devolvendo EXATAMENTE os mesmos dataclasses dos coletores REST
    (FundingRecord / OIRecord / KlineRecord). O resto do pipeline não muda.

LAYOUT DO ARQUIVO (verificado em 2026-06-25):
    base = https://data.binance.vision/data/futures/um

    Funding (mensal):
        {base}/monthly/fundingRate/{SYM}/{SYM}-fundingRate-{YYYY-MM}.zip
        CSV: calc_time(ms), funding_interval_hours, last_funding_rate
        → NÃO traz mark_price (default 0.0).

    Klines (mensal):
        {base}/monthly/klines/{SYM}/{interval}/{SYM}-{interval}-{YYYY-MM}.zip
        CSV: open_time(ms), open, high, low, close, volume, close_time, ...

    Open Interest — dataset "metrics" (DIÁRIO, granularidade 5min, desde ~2021):
        {base}/daily/metrics/{SYM}/{SYM}-metrics-{YYYY-MM-DD}.zip
        CSV: create_time("YYYY-MM-DD HH:MM:SS" UTC), symbol,
             sum_open_interest, sum_open_interest_value, ...long/short ratios
        → NÃO existe versão mensal de metrics; iteramos por dia.

CACHE:
    ZIPs baixados ficam em data/v3/_vision_cache/ — re-execuções não re-baixam.
    Cada arquivo tem um .CHECKSUM (SHA256) no Vision; verificamos quando disponível.
"""

import csv
import hashlib
import io
import logging
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from GarimpoInvestimentos.core.paths import CACHE_DIR
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord
from GarimpoInvestimentos.v3.collectors.oi_collector import OIRecord
from GarimpoInvestimentos.v3.collectors.spot_collector import KlineRecord

logger = logging.getLogger(__name__)

_BASE = "https://data.binance.vision/data/futures/um"
_CACHE_DIR = CACHE_DIR / "v3" / "binance_vision"
_HTTP_TIMEOUT = 120.0


# ------------------------------------------------------------------ #
# Download + cache + checksum                                         #
# ------------------------------------------------------------------ #


def _cache_path(rel_url: str) -> Path:
    """Mapeia o caminho remoto para um arquivo local achatado e único."""
    safe = rel_url.replace("/", "__")
    return _CACHE_DIR / safe


def _verify_checksum(content: bytes, checksum_text: str) -> bool:
    """O .CHECKSUM do Vision tem formato 'SHA256HEX  filename'."""
    expected = checksum_text.strip().split()[0].lower()
    actual = hashlib.sha256(content).hexdigest().lower()
    return expected == actual


def _download_zip(rel_url: str, client: httpx.Client) -> bytes | None:
    """
    Baixa um ZIP do Vision (com cache local e verificação de checksum).
    Retorna os bytes do ZIP, ou None se o arquivo não existir (404).
    """
    cache = _cache_path(rel_url)
    if cache.exists():
        return cache.read_bytes()

    url = f"{_BASE}/{rel_url}"
    r = client.get(url)
    if r.status_code == 404:
        logger.debug("binance_vision: 404 (ausente) %s", rel_url)
        return None
    r.raise_for_status()
    content = r.content

    # Checksum best-effort (não falha o pipeline se o .CHECKSUM sumir)
    try:
        cr = client.get(f"{url}.CHECKSUM")
        if cr.status_code == 200 and not _verify_checksum(content, cr.text):
            raise OSError(f"Checksum SHA256 NÃO confere para {rel_url}")
    except httpx.HTTPError:
        logger.debug("binance_vision: checksum indisponível para %s", rel_url)

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(content)
    return content


def _read_csv_rows(zip_bytes: bytes) -> list[list[str]]:
    """Descompacta o ZIP (1 CSV dentro) e devolve as linhas, sem o header se houver."""
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    name = z.namelist()[0]
    text = z.read(name).decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    # Header presente se a 1ª célula não for numérica
    first = rows[0][0].strip().lower()
    has_header = not (
        first.isdigit() or first.replace("-", "").replace(":", "").replace(" ", "").isdigit()
    )
    return rows[1:] if has_header else rows


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
    return out


def load_klines_vision(
    symbol: str, start_ms: int, end_ms: int, interval: str = "1h"
) -> list[KlineRecord]:
    """Klines histórico (arquivos mensais)."""
    start = datetime.fromtimestamp(start_ms / 1000, tz=UTC)
    end = datetime.fromtimestamp(end_ms / 1000, tz=UTC)
    out: list[KlineRecord] = []
    with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
        for y, m in _months(start, end):
            rel = f"monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{y:04d}-{m:02d}.zip"
            zb = _download_zip(rel, client)
            if zb is None:
                continue
            for row in _read_csv_rows(zb):
                # open_time, open, high, low, close, volume, close_time, ...
                ts = int(row[0])
                if start_ms <= ts <= end_ms:
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
    return out


def load_oi_vision(symbol: str, start_ms: int, end_ms: int) -> list[OIRecord]:
    """
    Open Interest histórico via dataset 'metrics' (arquivos DIÁRIOS, 5min).
    create_time é string 'YYYY-MM-DD HH:MM:SS' em UTC.
    """
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
                if ts is None or not (start_ms <= ts <= end_ms):
                    continue
                try:
                    out.append(
                        OIRecord(
                            symbol=symbol,
                            timestamp_ms=ts,
                            oi_contracts=float(row[2]),
                            oi_notional_usd=float(row[3]),
                        )
                    )
                except (ValueError, IndexError):
                    continue
    out.sort(key=lambda r: r.timestamp_ms)
    if missing:
        logger.warning("binance_vision[%s]: %d dias de metrics ausentes no range", symbol, missing)
    logger.info("binance_vision[%s]: %d OI records (metrics 5min)", symbol, len(out))
    return out


def _parse_metrics_time(s: str) -> int | None:
    """'2024-01-15 00:05:00' (UTC) → epoch ms."""
    try:
        dt = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None
