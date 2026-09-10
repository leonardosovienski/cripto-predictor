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
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from predictor_core.net import get_http_client, with_retry
from predictor_core.obs import emit_event

from GarimpoInvestimentos.v3.circuit_breaker import CircuitBreaker
from GarimpoInvestimentos.v3.collectors.record_io import (
    load_records,
    save_records,
    validate_observation,
    validate_page,
)

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
    open_ms: int  # open_time — chave canônica
    close: float
    volume: float

    def __post_init__(self) -> None:
        validate_observation(
            self.symbol, self.open_ms, {"close": self.close, "volume": self.volume}
        )
        if self.close <= 0 or self.volume < 0:
            raise ValueError("close deve ser positivo e volume nao negativo")


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
        if start_ms > end_ms or start_ms < 0:
            raise ValueError("intervalo invalido")
        records: list[KlineRecord] = []
        # Freeze availability at request start. Never cache an unfinished candle.
        available_at_ms = min(end_ms, int(time.time() * 1000))
        cursor = start_ms

        async with get_http_client() as client:
            while cursor <= end_ms:
                if not self._cb.can_attempt():
                    emit_event(
                        "v3_cripto",
                        "circuit_open",
                        metrics={"data_quality_score": 0.0},
                        metadata={"collector": "spot", "symbol": self.symbol},
                    )
                    raise RuntimeError(f"CircuitBreaker OPEN para spot/{self.symbol}")

                try:
                    page = await self._fetch_page(client, cursor, end_ms)
                    validate_page(page, self.symbol, "open_ms", cursor, end_ms)
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
        logger.info("spot_collector [%s]: %d registros coletados", self.symbol, len(records))
        return [r for r in records if r.open_ms + 3_600_000 <= available_at_ms]

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
    """Add unique observations atomically; reject changed values for existing keys."""
    return save_records(records, path, _FIELDNAMES, load_spot_csv, "open_ms")


def load_spot_csv(path: Path) -> list[KlineRecord]:
    return load_records(
        path,
        _FIELDNAMES,
        lambda row: KlineRecord(
            row["symbol"], int(row["open_ms"]), float(row["close"]), float(row["volume"])
        ),
        "open_ms",
    )
