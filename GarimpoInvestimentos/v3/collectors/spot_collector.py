"""
Coletor de klines (OHLCV) do spot Binance — base para features do HMM.

Endpoint : GET https://api.binance.com/api/v3/klines
Intervalo: 1h (downsampled para 8h no feature_builder via alinhamento de timestamps)

Retornamos closes horárias; o feature_builder calcula:
- log return 1h  : ln(close_t / close_{t-1})
- realized vol 24h: std(log_returns últimas 24h)
- log return 8h  : ln(close_no_timestamp_funding / close_8h_atrás)

Contrato de saída (KlineRecord):
    symbol      str
    open_ms     int   ← open_time em ms (timestamp_exchange_ms)
    close       float
    volume      float
"""
import asyncio
import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from predictor_core.net import get_http_client, with_retry
from predictor_core.obs import emit_event

from GarimpoInvestimentos.v3.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

_SPOT_BASE = "https://api.binance.com"
_KLINES_PATH = "/api/v3/klines"
_INTERVAL = "1h"
_MAX_PER_PAGE = 1000
_PAGE_SLEEP_S = 0.3


# ------------------------------------------------------------------ #
# Contrato de dado                                                     #
# ------------------------------------------------------------------ #

@dataclass(frozen=True)
class KlineRecord:
    symbol: str
    open_ms: int     # open_time — chave canônica
    close: float
    volume: float


# ------------------------------------------------------------------ #
# Coletor                                                              #
# ------------------------------------------------------------------ #

class SpotCollector:
    """
    Coleta klines horárias do spot Binance.

    Uso:
        cb = CircuitBreaker("spot_BTCUSDT")
        collector = SpotCollector("BTCUSDT", cb)
        records = await collector.fetch_range(start_ms, end_ms)
    """

    def __init__(self, symbol: str, circuit_breaker: CircuitBreaker) -> None:
        self.symbol = symbol
        self._cb = circuit_breaker

    async def fetch_range(
        self,
        start_ms: int,
        end_ms: int,
    ) -> list[KlineRecord]:
        records: list[KlineRecord] = []
        cursor = start_ms

        async with get_http_client() as client:
            while cursor < end_ms:
                if not self._cb.can_attempt():
                    emit_event(
                        "v3_cripto",
                        "circuit_open",
                        metrics={"data_quality_score": 0.0},
                        metadata={"collector": "spot", "symbol": self.symbol},
                    )
                    raise RuntimeError(
                        f"CircuitBreaker OPEN para spot/{self.symbol}"
                    )

                try:
                    page = await self._fetch_page(client, cursor, end_ms)
                except Exception as exc:
                    self._cb.record_failure()
                    emit_event(
                        "v3_cripto",
                        "collector_error",
                        metrics={"data_quality_score": 0.0},
                        metadata={
                            "collector": "spot",
                            "symbol": self.symbol,
                            "error": type(exc).__name__,
                            "detail": str(exc)[:200],
                        },
                    )
                    raise

                self._cb.record_success()

                if not page:
                    break

                records.extend(page)
                last_ts = page[-1].open_ms

                if last_ts >= end_ms or len(page) < _MAX_PER_PAGE:
                    break

                # Próxima página: avança 1h (3_600_000ms) a partir do último open
                cursor = last_ts + 3_600_000
                await asyncio.sleep(_PAGE_SLEEP_S)

        emit_event(
            "v3_cripto",
            "spot_collected",
            metrics={"n_records": len(records)},
            metadata={"symbol": self.symbol, "start_ms": start_ms, "end_ms": end_ms},
        )
        logger.info(
            "spot_collector [%s]: %d registros coletados", self.symbol, len(records)
        )
        return records

    @with_retry(attempts=4, base_delay=2.0, max_delay=30.0)
    async def _fetch_page(
        self,
        client,
        start_ms: int,
        end_ms: int,
    ) -> list[KlineRecord]:
        params = {
            "symbol": self.symbol,
            "interval": _INTERVAL,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": _MAX_PER_PAGE,
        }
        resp = await client.get(f"{_SPOT_BASE}{_KLINES_PATH}", params=params)
        resp.raise_for_status()
        return [_parse_kline(self.symbol, item) for item in resp.json()]


def _parse_kline(symbol: str, item: list) -> KlineRecord:
    # Binance kline: [open_time, open, high, low, close, volume, close_time, ...]
    return KlineRecord(
        symbol=symbol,
        open_ms=int(item[0]),
        close=float(item[4]),
        volume=float(item[5]),
    )


# ------------------------------------------------------------------ #
# Persistência                                                         #
# ------------------------------------------------------------------ #

_FIELDNAMES = ["symbol", "open_ms", "close", "volume"]


def save_spot_csv(records: list[KlineRecord], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_keys: set[int] = set()
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                existing_keys.add(int(row["open_ms"]))

    new_records = [r for r in records if r.open_ms not in existing_keys]
    if not new_records:
        return 0

    write_header = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        if write_header:
            writer.writeheader()
        for r in new_records:
            writer.writerow({
                "symbol": r.symbol,
                "open_ms": r.open_ms,
                "close": r.close,
                "volume": r.volume,
            })

    logger.info("spot_collector: %d novos registros → %s", len(new_records), path)
    return len(new_records)


def load_spot_csv(path: Path) -> list[KlineRecord]:
    if not path.exists():
        return []
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(KlineRecord(
                symbol=row["symbol"],
                open_ms=int(row["open_ms"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            ))
    return sorted(rows, key=lambda r: r.open_ms)
