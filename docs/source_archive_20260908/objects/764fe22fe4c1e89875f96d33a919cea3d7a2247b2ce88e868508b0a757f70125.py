"""Persistência append-only da camada de trading, sempre COLLECTION_ONLY.

Ordens e books não podem existir apenas em memória se forem usados para avaliar
executabilidade. Esta store preserva eventos imutáveis com hash de conteúdo e os
três tempos relevantes: evento no venue, recebimento e ingestão. Ela não envia
ordens e não autoriza capital.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
import zlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from predictor_core import infra

from GarimpoInvestimentos.trading.contracts import Order, ensure_utc
from GarimpoInvestimentos.trading.microstructure import OrderBookSnapshot

SCIENTIFIC_STATE = "COLLECTION_ONLY"
_KIND_CODES = {"trade": 1, "bbo": 2, "depth": 3, "snapshot": 4}
_KIND_NAMES = {value: key for key, value in _KIND_CODES.items()}
_SYMBOL_CODES = {"BTCUSDT": 1, "ETHUSDT": 2}
_SYMBOL_NAMES = {value: key for key, value in _SYMBOL_CODES.items()}

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
    (
        "0004_compressed_microstructure",
        """
        CREATE TABLE IF NOT EXISTS microstructure_events_v2 (
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
            payload_zlib BLOB NOT NULL,
            quality_flags TEXT NOT NULL,
            scientific_state TEXT NOT NULL CHECK(scientific_state='COLLECTION_ONLY'),
            PRIMARY KEY(venue, symbol, kind, observation_id)
        );
        CREATE INDEX IF NOT EXISTS idx_microstructure_v2_instrument_time
            ON microstructure_events_v2(venue, symbol, kind, received_at);
        CREATE INDEX IF NOT EXISTS idx_microstructure_v2_sequence
            ON microstructure_events_v2(venue, symbol, kind, sequence_id);
        """,
    ),
    (
        "0005_dense_microstructure",
        """
        CREATE TABLE IF NOT EXISTS microstructure_events_v3 (
            kind_code INTEGER NOT NULL CHECK(kind_code BETWEEN 1 AND 4),
            symbol_code INTEGER NOT NULL CHECK(symbol_code IN (1,2)),
            observation_id TEXT NOT NULL,
            sequence_id INTEGER,
            event_us INTEGER,
            received_us INTEGER NOT NULL,
            ingested_us INTEGER NOT NULL,
            session_blob BLOB NOT NULL,
            payload_hash_blob BLOB NOT NULL CHECK(length(payload_hash_blob)=32),
            payload_zlib BLOB NOT NULL,
            quality_flags TEXT NOT NULL,
            PRIMARY KEY(symbol_code, kind_code, observation_id)
        ) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS idx_microstructure_v3_time
            ON microstructure_events_v3(symbol_code, kind_code, received_us);
        CREATE INDEX IF NOT EXISTS idx_microstructure_v3_sequence
            ON microstructure_events_v3(symbol_code, kind_code, sequence_id);
        """,
    ),
]


def _canonical(payload: dict[str, Any]) -> tuple[str, str]:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _dt(value: datetime, label: str) -> str:
    return ensure_utc(value, label).isoformat()


def _micros(value: datetime) -> int:
    return int(ensure_utc(value, "timestamp").timestamp() * 1_000_000)


def _from_micros(value: int | None) -> str | None:
    return (
        datetime.fromtimestamp(value / 1_000_000, tz=UTC).isoformat() if value is not None else None
    )


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
        self._last_heartbeat_monotonic: float | None = None

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
            key = (venue, symbol, kind, observation_id)
            dense_key = (_SYMBOL_CODES[symbol], _KIND_CODES[kind], observation_id)
            existing = self._conn.execute(
                """SELECT hex(payload_hash_blob) payload_hash FROM microstructure_events_v3
                   WHERE symbol_code=? AND kind_code=? AND observation_id=?
                   UNION ALL
                   SELECT payload_hash FROM microstructure_events_v2
                   WHERE venue=? AND symbol=? AND kind=? AND observation_id=?
                   UNION ALL
                   SELECT payload_hash FROM microstructure_events
                   WHERE venue=? AND symbol=? AND kind=? AND observation_id=? LIMIT 1""",
                (*dense_key, *key, *key),
            ).fetchone()
            if existing:
                if existing["payload_hash"].lower() != digest:
                    raise ValueError("observation ID já existe com hash conflitante")
                return False
            self._conn.execute(
                """INSERT INTO microstructure_events_v3
                (kind_code,symbol_code,observation_id,sequence_id,event_us,received_us,
                 ingested_us,session_blob,payload_hash_blob,payload_zlib,quality_flags)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    _KIND_CODES[kind],
                    _SYMBOL_CODES[symbol],
                    observation_id,
                    sequence_id,
                    _micros(event) if event else None,
                    _micros(received),
                    _micros(ingested),
                    bytes.fromhex(session_id) if len(session_id) == 32 else session_id.encode(),
                    bytes.fromhex(digest),
                    zlib.compress(encoded.encode("utf-8"), level=6),
                    json.dumps(sorted(quality_flags)),
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
            observation_id=(f"{observation.last_update_id}:{observation.requested_at.isoformat()}"),
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

    def heartbeat(self, *, min_interval_seconds: float = 5.0) -> bool:
        if min_interval_seconds <= 0:
            raise ValueError("min_interval_seconds precisa ser positivo")
        now = time.monotonic()
        if (
            self._last_heartbeat_monotonic is not None
            and now - self._last_heartbeat_monotonic < min_interval_seconds
        ):
            return False
        self.record_health("heartbeat", "*")
        self._last_heartbeat_monotonic = now
        return True

    def latest_microstructure(self) -> list[Any]:
        rows = self._decoded_rows()
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (row["symbol"], row["kind"])
            if key not in latest or row["received_at"] > latest[key]["received_at"]:
                latest[key] = row
        return list(latest.values())

    def quality_rows(self, start: datetime, end: datetime) -> list[Any]:
        return self._decoded_rows(
            "WHERE received_at>=? AND received_at<?",
            (_dt(start, "start"), _dt(end, "end")),
        )

    def _decoded_rows(self, where: str = "", params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        columns = (
            "kind,observation_id,venue,symbol,sequence_id,event_at,received_at,ingested_at,"
            "session_id,collector_version,payload_hash,quality_flags,scientific_state"
        )
        result: list[dict[str, Any]] = []
        for row in self._conn.execute(
            f"SELECT {columns},payload_json,NULL payload_zlib FROM microstructure_events {where}",
            params,
        ):
            result.append(dict(row))
        for row in self._conn.execute(
            f"SELECT {columns},NULL payload_json,payload_zlib FROM microstructure_events_v2 {where}",
            params,
        ):
            item = dict(row)
            item["payload_json"] = zlib.decompress(item.pop("payload_zlib")).decode("utf-8")
            result.append(item)
        dense_where = ""
        dense_params: tuple[Any, ...] = ()
        if where:
            start, end = params
            dense_where = "WHERE received_us>=? AND received_us<?"
            dense_params = (
                _micros(datetime.fromisoformat(start)),
                _micros(datetime.fromisoformat(end)),
            )
        for row in self._conn.execute(
            f"SELECT * FROM microstructure_events_v3 {dense_where}", dense_params
        ):
            item = dict(row)
            result.append(
                {
                    "kind": _KIND_NAMES[item["kind_code"]],
                    "observation_id": item["observation_id"],
                    "venue": "binance_spot",
                    "symbol": _SYMBOL_NAMES[item["symbol_code"]],
                    "sequence_id": item["sequence_id"],
                    "event_at": _from_micros(item["event_us"]),
                    "received_at": _from_micros(item["received_us"]),
                    "ingested_at": _from_micros(item["ingested_us"]),
                    "session_id": item["session_blob"].hex(),
                    "collector_version": "binance_spot_microstructure_v1",
                    "payload_hash": item["payload_hash_blob"].hex(),
                    "quality_flags": item["quality_flags"],
                    "scientific_state": SCIENTIFIC_STATE,
                    "payload_json": zlib.decompress(item["payload_zlib"]).decode("utf-8"),
                }
            )
        result.sort(key=lambda item: item["received_at"])
        return result

    def compact_microstructure_v1(self, *, batch_size: int = 10_000) -> dict[str, int]:
        """Copy v1 rows losslessly to compressed v2, verify, then remove redundancy.

        Call only while the collector is stopped. A filesystem backup must be made by
        the operator before this maintenance operation.
        """
        if batch_size <= 0:
            raise ValueError("batch_size precisa ser positivo")
        before = self._conn.execute("SELECT COUNT(*) FROM microstructure_events").fetchone()[0]
        copied = 0
        while True:
            rows = self._conn.execute(
                "SELECT * FROM microstructure_events ORDER BY rowid LIMIT ?", (batch_size,)
            ).fetchall()
            if not rows:
                break
            with self._conn:
                for row in rows:
                    self._conn.execute(
                        """INSERT INTO microstructure_events_v2
                        (kind,observation_id,venue,symbol,sequence_id,event_at,received_at,
                         ingested_at,session_id,collector_version,payload_hash,payload_zlib,
                         quality_flags,scientific_state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(venue,symbol,kind,observation_id) DO NOTHING""",
                        (
                            row["kind"],
                            row["observation_id"],
                            row["venue"],
                            row["symbol"],
                            row["sequence_id"],
                            row["event_at"],
                            row["received_at"],
                            row["ingested_at"],
                            row["session_id"],
                            row["collector_version"],
                            row["payload_hash"],
                            zlib.compress(row["payload_json"].encode("utf-8"), 6),
                            row["quality_flags"],
                            row["scientific_state"],
                        ),
                    )
                    copied += 1
                # Delete only rows proven present in v2 with the same content hash.
                self._conn.execute(
                    """DELETE FROM microstructure_events AS old WHERE EXISTS (
                       SELECT 1 FROM microstructure_events_v2 AS new
                       WHERE new.venue=old.venue AND new.symbol=old.symbol
                         AND new.kind=old.kind AND new.observation_id=old.observation_id
                         AND new.payload_hash=old.payload_hash)"""
                )
            # DELETE removes the entire verified batch (and any previously verified rows).
        remaining = self._conn.execute("SELECT COUNT(*) FROM microstructure_events").fetchone()[0]
        if remaining:
            raise RuntimeError(f"compactação incompleta: {remaining} linhas v1 restantes")
        return {"v1_before": before, "processed": copied, "v1_after": remaining}

    def compact_microstructure_v2(self, *, batch_size: int = 10_000) -> dict[str, int]:
        """Move verified compressed v2 rows into the dense WITHOUT ROWID layout."""
        if batch_size <= 0:
            raise ValueError("batch_size precisa ser positivo")
        before = self._conn.execute("SELECT COUNT(*) FROM microstructure_events_v2").fetchone()[0]
        processed = 0
        while True:
            rows = self._conn.execute(
                "SELECT * FROM microstructure_events_v2 ORDER BY rowid LIMIT ?", (batch_size,)
            ).fetchall()
            if not rows:
                break
            with self._conn:
                for row in rows:
                    self._conn.execute(
                        """INSERT INTO microstructure_events_v3
                        (kind_code,symbol_code,observation_id,sequence_id,event_us,received_us,
                         ingested_us,session_blob,payload_hash_blob,payload_zlib,quality_flags)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(symbol_code,kind_code,observation_id) DO NOTHING""",
                        (
                            _KIND_CODES[row["kind"]],
                            _SYMBOL_CODES[row["symbol"]],
                            row["observation_id"],
                            row["sequence_id"],
                            _micros(datetime.fromisoformat(row["event_at"]))
                            if row["event_at"]
                            else None,
                            _micros(datetime.fromisoformat(row["received_at"])),
                            _micros(datetime.fromisoformat(row["ingested_at"])),
                            bytes.fromhex(row["session_id"])
                            if len(row["session_id"]) == 32
                            else row["session_id"].encode(),
                            bytes.fromhex(row["payload_hash"]),
                            row["payload_zlib"],
                            row["quality_flags"],
                        ),
                    )
                    processed += 1
                self._conn.execute(
                    """DELETE FROM microstructure_events_v2 AS old WHERE EXISTS (
                       SELECT 1 FROM microstructure_events_v3 AS new
                       WHERE new.symbol_code=CASE old.symbol WHEN 'BTCUSDT' THEN 1 ELSE 2 END
                         AND new.kind_code=CASE old.kind WHEN 'trade' THEN 1 WHEN 'bbo' THEN 2
                           WHEN 'depth' THEN 3 ELSE 4 END
                         AND new.observation_id=old.observation_id
                         AND lower(hex(new.payload_hash_blob))=old.payload_hash)"""
                )
        remaining = self._conn.execute("SELECT COUNT(*) FROM microstructure_events_v2").fetchone()[
            0
        ]
        if remaining:
            raise RuntimeError(f"compactação v2 incompleta: {remaining} linhas restantes")
        return {"v2_before": before, "processed": processed, "v2_after": remaining}
