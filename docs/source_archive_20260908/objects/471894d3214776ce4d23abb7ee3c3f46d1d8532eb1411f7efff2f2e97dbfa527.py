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
import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from predictor_core.net import get_http_client, with_retry
from predictor_core.obs import emit_event

from GarimpoInvestimentos.v3.circuit_breaker import CircuitBreaker

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
        records: list[FundingRecord] = []
        cursor = start_ms

        async with get_http_client() as client:
            while cursor < end_ms:
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
    """
    Grava registros no CSV em modo append, deduplicando por funding_time_ms.
    Retorna o número de registros novos efetivamente gravados.
    Idempotente: executar duas vezes com os mesmos registros não duplica linhas.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_keys: set[int] = set()
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                existing_keys.add(int(row["funding_time_ms"]))

    new_records = [r for r in records if r.funding_time_ms not in existing_keys]
    if not new_records:
        logger.debug("funding_collector: nenhum registro novo para %s", path)
        return 0

    write_header = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        if write_header:
            writer.writeheader()
        for r in new_records:
            writer.writerow(
                {
                    "symbol": r.symbol,
                    "funding_time_ms": r.funding_time_ms,
                    "funding_rate": r.funding_rate,
                    "mark_price": r.mark_price,
                }
            )

    logger.info("funding_collector: %d novos registros → %s", len(new_records), path)
    return len(new_records)


def load_funding_csv(path: Path) -> list[FundingRecord]:
    """Carrega CSV e retorna lista ordenada por funding_time_ms."""
    if not path.exists():
        return []
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(
                FundingRecord(
                    symbol=row["symbol"],
                    funding_time_ms=int(row["funding_time_ms"]),
                    funding_rate=float(row["funding_rate"]),
                    mark_price=float(row["mark_price"]),
                )
            )
    return sorted(rows, key=lambda r: r.funding_time_ms)
