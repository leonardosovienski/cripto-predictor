"""Persistência append-only da camada de trading, sempre COLLECTION_ONLY.

Ordens e books não podem existir apenas em memória se forem usados para avaliar
executabilidade. Esta store preserva eventos imutáveis com hash de conteúdo e os
três tempos relevantes: evento no venue, recebimento e ingestão. Ela não envia
ordens e não autoriza capital.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from predictor_core import infra

from GarimpoInvestimentos.trading.contracts import Order, ensure_utc
from GarimpoInvestimentos.trading.microstructure import OrderBookSnapshot

SCIENTIFIC_STATE = "COLLECTION_ONLY"

_MIGRATIONS = [
    (
        "0001_trading_events",
        """
        CREATE TABLE IF NOT EXISTS trading_events (
            event_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            intent_id TEXT NOT NULL,
            venue TEXT NOT NULL,
            symbol TEXT NOT NULL,
            status TEXT NOT NULL,
            event_at TEXT NOT NULL,
            received_at TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            scientific_state TEXT NOT NULL CHECK(scientific_state='COLLECTION_ONLY')
        );
        CREATE INDEX IF NOT EXISTS idx_trading_events_order
            ON trading_events(order_id, event_at);
        """,
    ),
    (
        "0002_order_book_snapshots",
        """
        CREATE TABLE IF NOT EXISTS order_book_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            venue TEXT NOT NULL,
            symbol TEXT NOT NULL,
            event_at TEXT NOT NULL,
            received_at TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            sequence_id INTEGER,
            payload_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            scientific_state TEXT NOT NULL CHECK(scientific_state='COLLECTION_ONLY')
        );
        CREATE INDEX IF NOT EXISTS idx_order_books_instrument
            ON order_book_snapshots(venue, symbol, event_at);
        """,
    ),
    (
        "0003_public_microstructure",
        """
        CREATE TABLE IF NOT EXISTS microstructure_events (
            kind TEXT NOT NULL,
            observation_id TEXT NOT NULL,
            venue TEXT NOT NULL,
            symbol TEXT NOT NULL,
            sequence_id INTEGER,
            event_at TEXT,
            received_at TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            session_id TEXT NOT NULL,
            collector_version TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            quality_flags TEXT NOT NULL,
            scientific_state TEXT NOT NULL CHECK(scientific_state='COLLECTION_ONLY'),
            PRIMARY KEY(venue, symbol, kind, observation_id)
        );
        CREATE INDEX IF NOT EXISTS idx_microstructure_instrument_time
            ON microstructure_events(venue, symbol, kind, received_at);
        CREATE INDEX IF NOT EXISTS idx_microstructure_sequence
            ON microstructure_events(venue, symbol, kind, sequence_id);
        CREATE TABLE IF NOT EXISTS collector_health (
            health_id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric TEXT NOT NULL,
            symbol TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            session_id TEXT NOT NULL,
            detail TEXT,
            scientific_state TEXT NOT NULL CHECK(scientific_state='COLLECTION_ONLY')
        );
        CREATE INDEX IF NOT EXISTS idx_collector_health_time
            ON collector_health(metric, symbol, recorded_at);
        """,
    ),
]


def _canonical(payload: dict[str, Any]) -> tuple[str, str]:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _dt(value: datetime, label: str) -> str:
    return ensure_utc(value, label).isoformat()


@dataclass(frozen=True)
class StoredTradingEvent:
    event_id: str
    order_id: str
    status: str
    event_at: str
    received_at: str
    ingested_at: str
    payload_hash: str
    payload: dict[str, Any]
    scientific_state: str


class TradingStore:
    def __init__(self, db_path: Path | str):
        self._conn = infra.connect(db_path)
        infra.run_migrations(self._conn, _MIGRATIONS)
        self.session_id = uuid.uuid4().hex

    def new_session(self) -> str:
        self.session_id = uuid.uuid4().hex
        return self.session_id

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> TradingStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def append_order_event(
        self,
        *,
        event_id: str,
        order: Order,
        event_at: datetime,
        received_at: datetime,
        ingested_at: datetime,
    ) -> bool:
        event_iso = _dt(event_at, "event_at")
        received_iso = _dt(received_at, "received_at")
        ingested_iso = _dt(ingested_at, "ingested_at")
        if received_iso < event_iso or ingested_iso < received_iso:
            raise ValueError("tempos precisam obedecer event_at <= received_at <= ingested_at")
        payload = asdict(order)
        payload["instrument"] = asdict(order.instrument)
        payload["side"] = order.side.value
        payload["order_type"] = order.order_type.value
        payload["status"] = order.status.value
        payload["created_at"] = order.created_at.isoformat()
        for name in ("submitted_at", "accepted_at", "terminal_at", "last_reconciled_at"):
            value = getattr(order, name)
            payload[name] = value.isoformat() if value else None
        payload["fills"] = [
            {
                **asdict(fill),
                "liquidity": fill.liquidity.value,
                "filled_at": fill.filled_at.isoformat(),
            }
            for fill in order.fills
        ]
        encoded, digest = _canonical(payload)
        existing = self._conn.execute(
            "SELECT payload_hash FROM trading_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if existing:
            if existing["payload_hash"] != digest:
                raise ValueError("event_id já existe com conteúdo diferente")
            return False
        self._conn.execute(
            """INSERT INTO trading_events
               (event_id, order_id, intent_id, venue, symbol, status, event_at,
                received_at, ingested_at, payload_hash, payload_json, scientific_state)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event_id,
                order.order_id,
                order.intent_id,
                order.instrument.venue,
                order.instrument.symbol,
                order.status.value,
                event_iso,
                received_iso,
                ingested_iso,
                digest,
                encoded,
                SCIENTIFIC_STATE,
            ),
        )
        self._conn.commit()
        return True

    def append_order_book(
        self,
        *,
        snapshot_id: str,
        snapshot: OrderBookSnapshot,
        received_at: datetime,
        ingested_at: datetime,
        sequence_id: int | None = None,
    ) -> bool:
        event_iso = _dt(snapshot.timestamp, "snapshot.timestamp")
        received_iso = _dt(received_at, "received_at")
        ingested_iso = _dt(ingested_at, "ingested_at")
        if received_iso < event_iso or ingested_iso < received_iso:
            raise ValueError("tempos precisam obedecer event_at <= received_at <= ingested_at")
        payload = {
            "instrument": asdict(snapshot.instrument),
            "timestamp": event_iso,
            "sequence_id": sequence_id,
            "bids": [asdict(level) for level in snapshot.bids],
            "asks": [asdict(level) for level in snapshot.asks],
        }
        encoded, digest = _canonical(payload)
        existing = self._conn.execute(
            "SELECT payload_hash FROM order_book_snapshots WHERE snapshot_id=?", (snapshot_id,)
        ).fetchone()
        if existing:
            if existing["payload_hash"] != digest:
                raise ValueError("snapshot_id já existe com conteúdo diferente")
            return False
        self._conn.execute(
            """INSERT INTO order_book_snapshots
               (snapshot_id, venue, symbol, event_at, received_at, ingested_at,
                sequence_id, payload_hash, payload_json, scientific_state)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                snapshot_id,
                snapshot.instrument.venue,
                snapshot.instrument.symbol,
                event_iso,
                received_iso,
                ingested_iso,
                sequence_id,
                digest,
                encoded,
                SCIENTIFIC_STATE,
            ),
        )
        self._conn.commit()
        return True

    def order_events(self, order_id: str) -> list[StoredTradingEvent]:
        rows = self._conn.execute(
            """SELECT * FROM trading_events WHERE order_id=?
               ORDER BY event_at, event_id""",
            (order_id,),
        )
        return [
            StoredTradingEvent(
                event_id=row["event_id"],
                order_id=row["order_id"],
                status=row["status"],
                event_at=row["event_at"],
                received_at=row["received_at"],
                ingested_at=row["ingested_at"],
                payload_hash=row["payload_hash"],
                payload=json.loads(row["payload_json"]),
                scientific_state=row["scientific_state"],
            )
            for row in rows
        ]

    def _append_microstructure(
        self,
        *,
        kind: str,
        observation_id: str,
        venue: str,
        symbol: str,
        sequence_id: int | None,
        event_at: datetime | None,
        received_at: datetime,
        session_id: str,
        payload: dict[str, Any],
        quality_flags: frozenset[str],
    ) -> bool:
        received = ensure_utc(received_at, "received_at")
        event = ensure_utc(event_at, "event_at") if event_at else None
        if event is not None and event > received:
            quality_flags = quality_flags | {"event_after_received"}
        ingested = datetime.now(received.tzinfo)
        encoded, digest = _canonical(payload)
        with self._conn:
            existing = self._conn.execute(
                """SELECT payload_hash FROM microstructure_events
                   WHERE venue=? AND symbol=? AND kind=? AND observation_id=?""",
                (venue, symbol, kind, observation_id),
            ).fetchone()
            if existing:
                if existing["payload_hash"] != digest:
                    raise ValueError("observation ID já existe com hash conflitante")
                return False
            self._conn.execute(
                """INSERT INTO microstructure_events
                (kind,observation_id,venue,symbol,sequence_id,event_at,received_at,ingested_at,
                 session_id,collector_version,payload_hash,payload_json,quality_flags,scientific_state)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    kind,
                    observation_id,
                    venue,
                    symbol,
                    sequence_id,
                    event.isoformat() if event else None,
                    received.isoformat(),
                    ingested.isoformat(),
                    session_id,
                    "binance_spot_microstructure_v1",
                    digest,
                    encoded,
                    json.dumps(sorted(quality_flags)),
                    SCIENTIFIC_STATE,
                ),
            )
        return True

    def append_trade(self, observation: Any) -> bool:
        payload = {
            "trade_id": observation.trade_id,
            "price": observation.price,
            "quantity": observation.quantity,
            "buyer_maker": observation.buyer_maker,
            "exchange_trade_at": observation.exchange_trade_at.isoformat(),
            "event_at": observation.event_at.isoformat(),
        }
        return self._append_microstructure(
            kind="trade",
            observation_id=str(observation.trade_id),
            venue=observation.instrument.venue,
            symbol=observation.instrument.symbol,
            sequence_id=observation.trade_id,
            event_at=observation.event_at,
            received_at=observation.received_at,
            session_id=observation.session_id,
            payload=payload,
            quality_flags=observation.quality_flags,
        )

    def append_bbo(self, observation: Any) -> bool:
        payload = {
            "update_id": observation.update_id,
            "bid_price": observation.bid_price,
            "bid_quantity": observation.bid_quantity,
            "ask_price": observation.ask_price,
            "ask_quantity": observation.ask_quantity,
        }
        observation_id = (
            str(observation.update_id)
            if observation.update_id is not None
            else hashlib.sha256(
                (
                    observation.instrument.key + observation.received_at.isoformat() + repr(payload)
                ).encode()
            ).hexdigest()
        )
        return self._append_microstructure(
            kind="bbo",
            observation_id=observation_id,
            venue=observation.instrument.venue,
            symbol=observation.instrument.symbol,
            sequence_id=observation.update_id,
            event_at=None,
            received_at=observation.received_at,
            session_id=observation.session_id,
            payload=payload,
            quality_flags=observation.quality_flags,
        )

    def append_depth(self, observation: Any) -> bool:
        update = observation.update
        payload = {
            "first_update_id": update.first_update_id,
            "final_update_id": update.final_update_id,
            "previous_final_update_id": update.previous_final_update_id,
            "bids": update.bids,
            "asks": update.asks,
            "event_at": update.event_at.isoformat(),
        }
        return self._append_microstructure(
            kind="depth",
            observation_id=f"{update.first_update_id}:{update.final_update_id}",
            venue=update.instrument.venue,
            symbol=update.instrument.symbol,
            sequence_id=update.final_update_id,
            event_at=update.event_at,
            received_at=observation.received_at,
            session_id=observation.session_id,
            payload=payload,
            quality_flags=observation.quality_flags,
        )

    def append_collected_snapshot(self, observation: Any, *, session_id: str) -> bool:
        snapshot = observation.snapshot
        payload = {
            "lastUpdateId": observation.last_update_id,
            "bids": [(x.price, x.qty) for x in snapshot.bids],
            "asks": [(x.price, x.qty) for x in snapshot.asks],
            "requested_at": observation.requested_at.isoformat(),
            "exchange_event_time": None,
        }
        return self._append_microstructure(
            kind="snapshot",
            observation_id=str(observation.last_update_id),
            venue=snapshot.instrument.venue,
            symbol=snapshot.instrument.symbol,
            sequence_id=observation.last_update_id,
            event_at=None,
            received_at=observation.received_at,
            session_id=session_id,
            payload=payload,
            quality_flags=observation.quality_flags,
        )

    def record_health(self, metric: str, symbol: str, detail: str | None = None) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO collector_health(metric,symbol,recorded_at,session_id,detail,scientific_state) VALUES (?,?,?,?,?,?)",
                (
                    metric,
                    symbol,
                    datetime.now().astimezone().isoformat(),
                    self.session_id,
                    detail,
                    SCIENTIFIC_STATE,
                ),
            )

    def heartbeat(self) -> None:
        self.record_health("heartbeat", "*")

    def latest_microstructure(self) -> list[Any]:
        return list(
            self._conn.execute(
                """SELECT m.* FROM microstructure_events m JOIN (
               SELECT kind,symbol,MAX(received_at) received_at FROM microstructure_events
               GROUP BY kind,symbol) x USING(kind,symbol,received_at)"""
            )
        )

    def quality_rows(self, start: datetime, end: datetime) -> list[Any]:
        return list(
            self._conn.execute(
                "SELECT * FROM microstructure_events WHERE received_at>=? AND received_at<? ORDER BY received_at",
                (_dt(start, "start"), _dt(end, "end")),
            )
        )
