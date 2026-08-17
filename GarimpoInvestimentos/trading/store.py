"""Persistência append-only da camada de trading, sempre COLLECTION_ONLY.

Ordens e books não podem existir apenas em memória se forem usados para avaliar
executabilidade. Esta store preserva eventos imutáveis com hash de conteúdo e os
três tempos relevantes: evento no venue, recebimento e ingestão. Ela não envia
ordens e não autoriza capital.
"""

from __future__ import annotations

import hashlib
import json
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
