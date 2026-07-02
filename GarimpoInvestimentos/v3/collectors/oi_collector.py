"""
Coletor de Open Interest histórico — Binance Futures REST.

Endpoint: GET /futures/data/openInterestHist
Period  : "1h" — granularidade válida da Binance (NÃO existe "8h" neste endpoint;
          períodos aceitos: 5m,15m,30m,1h,2h,4h,6h,12h,1d). Pontos de 1h batem
          EXATAMENTE nos timestamps de funding (00:00/08:00/16:00 UTC), então o
          join por timestamp no feature_builder é exato.

LIMITAÇÃO CRÍTICA DA BINANCE:
    Este endpoint só retorna os ÚLTIMOS ~30 DIAS. startTime > 30 dias atrás → HTTP 400
    (code -1130, "startTime is invalid"). Logo um WFA histórico (≥217 dias) NÃO é
    possível só com este feed. Para validação longa: coletar OI ao vivo diariamente
    (acumular) ou usar provedor pago (Coinalyze/Amberdata/Tardis).

Contrato de saída (OIRecord):
    symbol              str
    timestamp_ms        int   ← timestamp_exchange_ms (início do período 8h)
    oi_contracts        float ← soma dos contratos abertos (sumOpenInterest)
    oi_notional_usd     float ← valor nocional em USD (sumOpenInterestValue)

Nota: a Binance retorna OI em contratos (BTC) e em valor nocional (USD).
O feature_builder usa oi_notional_usd (invariante à flutuação de preço unitário).
"""
import asyncio
import csv
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from predictor_core.net import get_http_client, with_retry
from predictor_core.obs import emit_event

from GarimpoInvestimentos.v3.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

_FUTURES_BASE = "https://fapi.binance.com"
_OI_HIST_PATH = "/futures/data/openInterestHist"
_PERIOD = "1h"         # "8h" é INVÁLIDO neste endpoint (erro -1130); 1h alinha nos funding times
_MAX_OI_HISTORY_DAYS = 30   # Binance só serve os últimos ~30 dias de OI histórico
_MAX_PER_PAGE = 500    # limite da Binance para este endpoint
_PAGE_SLEEP_S = 0.5


# ------------------------------------------------------------------ #
# Contrato de dado                                                     #
# ------------------------------------------------------------------ #

@dataclass(frozen=True)
class OIRecord:
    symbol: str
    timestamp_ms: int           # início do período — usado como chave de join
    oi_contracts: float
    oi_notional_usd: float


# ------------------------------------------------------------------ #
# Coletor                                                              #
# ------------------------------------------------------------------ #

class OICollector:
    """
    Coleta histórico de Open Interest em granularidade 8h.

    Uso:
        cb = CircuitBreaker("oi_BTCUSDT")
        collector = OICollector("BTCUSDT", cb)
        records = await collector.fetch_range(start_ms, end_ms)
    """

    def __init__(self, symbol: str, circuit_breaker: CircuitBreaker) -> None:
        self.symbol = symbol
        self._cb = circuit_breaker

    async def fetch_range(
        self,
        start_ms: int,
        end_ms: int,
    ) -> list[OIRecord]:
        records: list[OIRecord] = []

        # Clamp ao limite de ~30 dias: pedir mais antigo retorna HTTP 400 (-1130).
        floor_ms = int(time.time() * 1000) - _MAX_OI_HISTORY_DAYS * 86_400_000
        if start_ms < floor_ms:
            emit_event(
                "v3_cripto", "oi_range_clamped",
                metrics={"clamped_days": float(_MAX_OI_HISTORY_DAYS)},
                metadata={
                    "symbol": self.symbol,
                    "requested_start_ms": start_ms,
                    "effective_start_ms": floor_ms,
                    "reason": "binance_oi_hist_30d_limit",
                },
            )
            logger.warning(
                "oi_collector [%s]: start ajustado para -%dd (limite Binance OI). "
                "Histórico de OI mais antigo exige feed pago.",
                self.symbol, _MAX_OI_HISTORY_DAYS,
            )
            start_ms = floor_ms
        cursor = start_ms

        async with get_http_client() as client:
            while cursor < end_ms:
                if not self._cb.can_attempt():
                    emit_event(
                        "v3_cripto",
                        "circuit_open",
                        metrics={"data_quality_score": 0.0},
                        metadata={"collector": "oi", "symbol": self.symbol},
                    )
                    raise RuntimeError(
                        f"CircuitBreaker OPEN para oi/{self.symbol}"
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
                            "collector": "oi",
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
                last_ts = page[-1].timestamp_ms

                if last_ts >= end_ms or len(page) < _MAX_PER_PAGE:
                    break

                cursor = last_ts + 1
                await asyncio.sleep(_PAGE_SLEEP_S)

        emit_event(
            "v3_cripto",
            "oi_collected",
            metrics={"n_records": len(records)},
            metadata={"symbol": self.symbol, "start_ms": start_ms, "end_ms": end_ms},
        )
        logger.info(
            "oi_collector [%s]: %d registros coletados", self.symbol, len(records)
        )
        return records

    @with_retry(attempts=4, base_delay=2.0, max_delay=30.0)
    async def _fetch_page(
        self,
        client,
        start_ms: int,
        end_ms: int,
    ) -> list[OIRecord]:
        params = {
            "symbol": self.symbol,
            "period": _PERIOD,
            "limit": _MAX_PER_PAGE,
            "startTime": start_ms,
            "endTime": end_ms,
        }
        resp = await client.get(f"{_FUTURES_BASE}{_OI_HIST_PATH}", params=params)
        resp.raise_for_status()
        return [_parse_oi(item) for item in resp.json()]


def _parse_oi(item: dict) -> OIRecord:
    return OIRecord(
        symbol=item["symbol"],
        timestamp_ms=int(item["timestamp"]),
        oi_contracts=float(item["sumOpenInterest"]),
        oi_notional_usd=float(item["sumOpenInterestValue"]),
    )


# ------------------------------------------------------------------ #
# Persistência                                                         #
# ------------------------------------------------------------------ #

_FIELDNAMES = ["symbol", "timestamp_ms", "oi_contracts", "oi_notional_usd"]


def save_oi_csv(records: list[OIRecord], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_keys: set[int] = set()
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                existing_keys.add(int(row["timestamp_ms"]))

    new_records = [r for r in records if r.timestamp_ms not in existing_keys]
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
                "timestamp_ms": r.timestamp_ms,
                "oi_contracts": r.oi_contracts,
                "oi_notional_usd": r.oi_notional_usd,
            })

    logger.info("oi_collector: %d novos registros → %s", len(new_records), path)
    return len(new_records)


def load_oi_csv(path: Path) -> list[OIRecord]:
    if not path.exists():
        return []
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(OIRecord(
                symbol=row["symbol"],
                timestamp_ms=int(row["timestamp_ms"]),
                oi_contracts=float(row["oi_contracts"]),
                oi_notional_usd=float(row["oi_notional_usd"]),
            ))
    return sorted(rows, key=lambda r: r.timestamp_ms)
