"""Public, COLLECTION_ONLY Binance Spot microstructure collector.

This module has no order adapter and reads no credentials.  It reconstructs the
book with the algorithm documented by Binance: buffer diff events, obtain a REST
snapshot, discard old events, require the first applicable range to bridge
``lastUpdateId + 1``, and fail closed/resnapshot on every gap.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import signal
from collections import deque
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from GarimpoInvestimentos.trading.contracts import Instrument, ensure_utc
from GarimpoInvestimentos.trading.microstructure import (
    BinanceOrderBookCollector,
    CollectedOrderBook,
    DepthSequenceGap,
    DepthUpdate,
    LocalOrderBook,
)
from GarimpoInvestimentos.trading.store import SCIENTIFIC_STATE, TradingStore

VENUE = "binance_spot"
COLLECTOR_VERSION = "binance_spot_microstructure_v1"
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT")
WS_BASE = "wss://stream.binance.com:9443/stream?streams="
LOG = logging.getLogger(__name__)


def _utc_ms(value: Any, label: str) -> datetime:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{label} inválido")
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _levels(value: Any, label: str) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} precisa ser lista")
    try:
        return tuple((float(row[0]), float(row[1])) for row in value)
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"{label} inválido") from exc


@dataclass(frozen=True)
class TradeObservation:
    instrument: Instrument
    trade_id: int
    price: float
    quantity: float
    buyer_maker: bool
    exchange_trade_at: datetime
    event_at: datetime
    received_at: datetime
    session_id: str
    quality_flags: frozenset[str] = frozenset()


@dataclass(frozen=True)
class BboObservation:
    instrument: Instrument
    update_id: int | None
    bid_price: float
    bid_quantity: float
    ask_price: float
    ask_quantity: float
    received_at: datetime
    session_id: str
    quality_flags: frozenset[str] = frozenset({"no_exchange_event_time"})

    def __post_init__(self) -> None:
        if (
            min(self.bid_price, self.ask_price) <= 0
            or min(self.bid_quantity, self.ask_quantity) < 0
        ):
            raise ValueError("BBO contém preço/quantidade inválido")
        if self.bid_price >= self.ask_price:
            raise ValueError("BBO cruzado")


@dataclass(frozen=True)
class DepthObservation:
    update: DepthUpdate
    received_at: datetime
    session_id: str
    quality_flags: frozenset[str] = frozenset()


def parse_stream_message(
    message: str | bytes | dict[str, Any], *, received_at: datetime, session_id: str
) -> TradeObservation | BboObservation | DepthObservation:
    """Parse documented Binance combined-stream payloads without defaults."""
    ensure_utc(received_at, "received_at")
    payload = json.loads(message) if isinstance(message, (str, bytes)) else message
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise ValueError("payload Binance inválido")
    event = data.get("e")
    symbol = data.get("s")
    if not isinstance(symbol, str) or not symbol:
        raise ValueError("payload sem symbol")
    instrument = Instrument(symbol.upper(), VENUE, "crypto_spot")
    if event == "trade":
        price, qty = float(data["p"]), float(data["q"])
        if price <= 0 or qty <= 0 or not isinstance(data["m"], bool):
            raise ValueError("trade inválido")
        return TradeObservation(
            instrument,
            int(data["t"]),
            price,
            qty,
            data["m"],
            _utc_ms(data["T"], "T"),
            _utc_ms(data["E"], "E"),
            received_at,
            session_id,
        )
    if event == "depthUpdate":
        update = DepthUpdate(
            instrument=instrument,
            first_update_id=int(data["U"]),
            final_update_id=int(data["u"]),
            event_at=_utc_ms(data["E"], "E"),
            bids=_levels(data["b"], "bids"),
            asks=_levels(data["a"], "asks"),
            previous_final_update_id=int(data["pu"]) if "pu" in data else None,
        )
        return DepthObservation(update, received_at, session_id)
    # bookTicker payloads may omit e/E on the Spot stream.
    if event == "bookTicker" or {"u", "b", "B", "a", "A"} <= data.keys():
        return BboObservation(
            instrument,
            int(data["u"]) if data.get("u") is not None else None,
            float(data["b"]),
            float(data["B"]),
            float(data["a"]),
            float(data["A"]),
            received_at,
            session_id,
        )
    raise ValueError(f"tipo de evento Binance não suportado: {event!r}")


class DepthSynchronizer:
    """Bounded snapshot+buffer synchronizer. Invalid books are never exposed."""

    def __init__(
        self, instrument: Instrument, *, max_events: int = 20_000, max_age_seconds: float = 30.0
    ):
        if max_events <= 0 or max_age_seconds <= 0:
            raise ValueError("limites do buffer precisam ser positivos")
        self.instrument = instrument
        self.max_events = max_events
        self.max_age_seconds = max_age_seconds
        self._buffer: deque[DepthObservation] = deque()
        self.book: LocalOrderBook | None = None
        self.resyncs = 0

    def buffer(self, observation: DepthObservation) -> None:
        if observation.update.instrument != self.instrument:
            raise ValueError("instrumento/venue divergente")
        if self._buffer and observation.received_at < self._buffer[-1].received_at:
            raise ValueError("timestamps de recebimento fora de ordem")
        self._buffer.append(observation)
        age = (observation.received_at - self._buffer[0].received_at).total_seconds()
        if len(self._buffer) > self.max_events or age > self.max_age_seconds:
            self.invalidate()
            raise BufferError("buffer depth excedeu limite; resnapshot obrigatório")

    def install_snapshot(self, observation: CollectedOrderBook) -> LocalOrderBook:
        if observation.snapshot.instrument != self.instrument:
            raise ValueError("snapshot pertence a outro instrumento/venue")
        candidate = LocalOrderBook(observation.snapshot, last_update_id=observation.last_update_id)
        pending = [x for x in self._buffer if x.update.final_update_id > observation.last_update_id]
        if pending:
            expected = observation.last_update_id + 1
            first = pending[0].update
            if not (first.first_update_id <= expected <= first.final_update_id):
                self.invalidate()
                raise DepthSequenceGap("primeiro evento aplicável não cobre lastUpdateId + 1")
            for item in pending:
                candidate.apply(item.update)
        self.book = candidate
        self._buffer.clear()
        return candidate

    def apply(self, observation: DepthObservation) -> bool:
        if self.book is None:
            self.buffer(observation)
            return False
        try:
            applied = self.book.apply(observation.update)
            if applied:
                self.book.snapshot()  # validates empty/crossed book after every mutation
            return applied
        except (DepthSequenceGap, ValueError) as exc:
            self.invalidate()
            if isinstance(exc, DepthSequenceGap):
                raise
            raise DepthSequenceGap(f"book inválido após update: {exc}") from exc

    def invalidate(self) -> None:
        self.book = None
        self._buffer.clear()
        self.resyncs += 1


SnapshotFetcher = Callable[[str], Awaitable[CollectedOrderBook]]


class BinanceSpotCollector:
    """Supervised public collector; every reconnect creates a new session."""

    def __init__(
        self,
        store: TradingStore,
        symbols: Sequence[str] = DEFAULT_SYMBOLS,
        *,
        snapshot_fetcher: SnapshotFetcher | None = None,
        max_reconnects: int = 20,
    ):
        normalized = tuple(s.upper() for s in symbols)
        if not normalized or any(s not in DEFAULT_SYMBOLS for s in normalized):
            raise ValueError("somente BTCUSDT e ETHUSDT são permitidos")
        if max_reconnects <= 0:
            raise ValueError("max_reconnects precisa ser positivo")
        self.store = store
        self.symbols = normalized
        rest = BinanceOrderBookCollector()
        self.snapshot_fetcher = snapshot_fetcher or (
            lambda symbol: rest.fetch_observation(symbol, limit=1000)
        )
        self.synchronizers = {
            s: DepthSynchronizer(Instrument(s, VENUE, "crypto_spot")) for s in normalized
        }
        self.reconnects = 0
        self.max_reconnects = max_reconnects

    @property
    def stream_url(self) -> str:
        streams = [
            f"{s.lower()}@{kind}"
            for s in self.symbols
            for kind in ("trade", "bookTicker", "depth@100ms")
        ]
        return WS_BASE + "/".join(streams)

    async def resnapshot(self, symbol: str) -> None:
        observation = await self.snapshot_fetcher(symbol)
        self.store.append_collected_snapshot(observation, session_id=self.store.session_id)
        self.synchronizers[symbol].install_snapshot(observation)

    async def handle(self, raw: str | bytes, *, received_at: datetime | None = None) -> None:
        received = received_at or datetime.now(UTC)
        observation = parse_stream_message(
            raw, received_at=received, session_id=self.store.session_id
        )
        if isinstance(observation, TradeObservation):
            self.store.append_trade(observation)
        elif isinstance(observation, BboObservation):
            self.store.append_bbo(observation)
        else:
            self.store.append_depth(observation)
            sync = self.synchronizers[observation.update.instrument.symbol]
            try:
                sync.apply(observation)
            except DepthSequenceGap:
                self.store.record_health("gap", observation.update.instrument.symbol)
                await self.resnapshot(observation.update.instrument.symbol)

    async def run(self, shutdown: asyncio.Event) -> None:
        try:
            import websockets
        except ImportError as exc:  # pragma: no cover - packaging guard
            raise RuntimeError("dependência websockets ausente") from exc
        backoff = 1.0
        while not shutdown.is_set():
            self.store.new_session()
            try:
                async with websockets.connect(
                    self.stream_url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_queue=20_000,
                    open_timeout=20,
                ) as ws:
                    # Start consuming before snapshots so depth is buffered.
                    snapshots = asyncio.gather(*(self.resnapshot(s) for s in self.symbols))

                    async def consume() -> None:
                        async for message in ws:
                            await self.handle(message)
                            self.store.heartbeat()
                            if shutdown.is_set():
                                break

                    consumer = asyncio.create_task(consume())
                    await snapshots
                    backoff = 1.0
                    async with asyncio.timeout(23 * 60 * 60):
                        await consumer
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.reconnects += 1
                self.store.record_health("reconnect", "*", detail=type(exc).__name__)
                if self.reconnects >= self.max_reconnects:
                    raise RuntimeError("limite de reconnects excedido; coleta falhou") from exc
                if shutdown.is_set():
                    break
                await asyncio.sleep(min(60.0, backoff) * random.uniform(0.8, 1.2))
                backoff = min(60.0, backoff * 2)


def _default_db() -> Path:
    return Path("data") / "binance_spot_microstructure.sqlite3"


async def _async_main(args: argparse.Namespace) -> int:
    shutdown = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown.set)
        except NotImplementedError:  # Windows
            pass
    with TradingStore(args.db) as store:
        collector = BinanceSpotCollector(store, args.symbol)
        await collector.run(shutdown)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Binance Spot public COLLECTION_ONLY collector")
    parser.add_argument("--symbol", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--db", type=Path, default=_default_db())
    parser.add_argument("--scientific-state", default=SCIENTIFIC_STATE, choices=(SCIENTIFIC_STATE,))
    args = parser.parse_args(argv)
    try:
        return asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        return 0
    except Exception:
        LOG.exception("collector_failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
