"""
Coletor de Funding Rate histórico — Binance Futures REST.

Estratégia:
- Paginação por cursor (startTime / endTime) com MAX_PER_PAGE = 1000.
- Retry via predictor_core.net.with_retry (backoff exp + jitter).
- Circuit Breaker próprio para distinguir falha transitória de indisponibilidade persistente.
- Saída: CSV append-only deduplicado por funding_time_ms (idempotente).

Funding rate pago a cada 8h (00:00 / 08:00 / 16:00 UTC).
NÃO usa WebSocket — polling suficiente para dados 8h.
NÃO recria retry/backoff do predictor_core.

Contrato de saída (FundingRecord):
    symbol             str
    funding_time_ms    int   ← timestamp_exchange_ms canônico
    funding_rate       float ← decimal (ex.: 0.0001 = 0.01%)
    mark_price         float ← preço mark no momento do funding
"""

import asyncio
import logging
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

_FUTURES_BASE = "https://fapi.binance.com"
_FUNDING_PATH = "/fapi/v1/fundingRate"
_MAX_PER_PAGE = 1000
_PAGE_SLEEP_S = 0.5  # 500ms entre páginas — Binance free tier (2 400 req/min para dados públicos)


# ------------------------------------------------------------------ #
# Contrato de dado                                                     #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class FundingRecord:
    symbol: str
    funding_time_ms: int
    funding_rate: float
    mark_price: float

    def __post_init__(self) -> None:
        validate_observation(
            self.symbol,
            self.funding_time_ms,
            {"funding_rate": self.funding_rate, "mark_price": self.mark_price},
        )
        if self.mark_price < 0:
            raise ValueError(
                "mark_price nao pode ser negativo; zero significa ausente no arquivo Vision"
            )


# ------------------------------------------------------------------ #
# Coletor                                                              #
# ------------------------------------------------------------------ #


class FundingCollector:
    """
    Coleta o histórico completo de funding rate para um símbolo.

    Uso:
        cb = CircuitBreaker("funding_BTCUSDT")
        collector = FundingCollector("BTCUSDT", cb)
        records = await collector.fetch_range(start_ms, end_ms)
    """

    def __init__(self, symbol: str, circuit_breaker: CircuitBreaker) -> None:
        self.symbol = symbol
        self._cb = circuit_breaker

    async def fetch_range(
        self,
        start_ms: int,
        end_ms: int,
    ) -> list[FundingRecord]:
        """
        Retorna todos os FundingRecord no intervalo [start_ms, end_ms].
        Levanta RuntimeError se o Circuit Breaker estiver OPEN.
        Levanta a exceção original da API em caso de falha não-transitória.
        """
        if start_ms > end_ms or start_ms < 0:
            raise ValueError("intervalo invalido")
        records: list[FundingRecord] = []
        cursor = start_ms

        async with get_http_client() as client:
            while cursor <= end_ms:
                if not self._cb.can_attempt():
                    emit_event(
                        "v3_cripto",
                        "circuit_open",
                        metrics={"data_quality_score": 0.0},
                        metadata={
                            "collector": "funding",
                            "symbol": self.symbol,
                            "cb_state": self._cb.state,
                        },
                    )
                    raise RuntimeError(
                        f"CircuitBreaker OPEN para funding/{self.symbol} — "
                        f"aguardando {self._cb.reset_timeout}s para probe."
                    )

                try:
                    page = await self._fetch_page(client, cursor, end_ms)
                    validate_page(page, self.symbol, "funding_time_ms", cursor, end_ms)
                except Exception as exc:
                    self._cb.record_failure()
                    emit_event(
                        "v3_cripto",
                        "collector_error",
                        metrics={"data_quality_score": 0.0},
                        metadata={
                            "collector": "funding",
                            "symbol": self.symbol,
                            "error": type(exc).__name__,
                            "detail": str(exc)[:200],
                            "cb_state": self._cb.state,
                        },
                    )
                    raise

                self._cb.record_success()

                if not page:
                    break

                records.extend(page)
                last_ts = page[-1].funding_time_ms

                if last_ts >= end_ms or len(page) < _MAX_PER_PAGE:
                    break

                cursor = last_ts + 1  # próxima página começa depois do último registro
                await asyncio.sleep(_PAGE_SLEEP_S)

        emit_event(
            "v3_cripto",
            "funding_collected",
            metrics={"n_records": len(records)},
            metadata={"symbol": self.symbol, "start_ms": start_ms, "end_ms": end_ms},
        )
        logger.info(
            "funding_collector [%s]: %d registros coletados (%s → %s)",
            self.symbol,
            len(records),
            start_ms,
            end_ms,
        )
        return records

    @with_retry(attempts=4, base_delay=2.0, max_delay=30.0)
    async def _fetch_page(
        self,
        client,
        start_ms: int,
        end_ms: int,
    ) -> list[FundingRecord]:
        """Busca uma página de até MAX_PER_PAGE registros. Decorado com with_retry."""
        params = {
            "symbol": self.symbol,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": _MAX_PER_PAGE,
        }
        resp = await client.get(f"{_FUTURES_BASE}{_FUNDING_PATH}", params=params)
        resp.raise_for_status()
        return [_parse_record(item) for item in resp.json()]


def _parse_record(item: dict) -> FundingRecord:
    return FundingRecord(
        symbol=item["symbol"],
        funding_time_ms=int(item["fundingTime"]),
        funding_rate=float(item["fundingRate"]),
        mark_price=float(item.get("markPrice") or 0.0),
    )


# ------------------------------------------------------------------ #
# Persistência                                                         #
# ------------------------------------------------------------------ #

_FIELDNAMES = ["symbol", "funding_time_ms", "funding_rate", "mark_price"]


def save_funding_csv(records: list[FundingRecord], path: Path) -> int:
    """Add unique observations atomically; reject changed values for existing keys."""
    return save_records(records, path, _FIELDNAMES, load_funding_csv, "funding_time_ms")


def load_funding_csv(path: Path) -> list[FundingRecord]:
    return load_records(
        path,
        _FIELDNAMES,
        lambda row: FundingRecord(
            row["symbol"],
            int(row["funding_time_ms"]),
            float(row["funding_rate"]),
            float(row["mark_price"]),
        ),
        "funding_time_ms",
    )
