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
from datetime import UTC, datetime, timedelta
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
    (
        "0006_dense_provenance",
        """
        ALTER TABLE microstructure_events_v3 ADD COLUMN session_text TEXT;
        ALTER TABLE microstructure_events_v3 ADD COLUMN collector_version TEXT NOT NULL
            DEFAULT 'binance_spot_microstructure_v1';
    """,
    ),
]


def _canonical(payload: dict[str, Any]) -> tuple[str, str]:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _dt(value: datetime, label: str) -> str:
    return ensure_utc(value, label).isoformat()


def _micros(value: datetime) -> int:
    delta = ensure_utc(value, "timestamp") - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def _from_micros(value: int | None) -> str | None:
    return (
        (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=value)).isoformat()
        if value is not None
        else None
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
            "SELECT payload_hash,event_at FROM trading_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if existing:
            if existing["payload_hash"] != digest or existing["event_at"] != event_iso:
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
        if venue != "binance_spot" or symbol not in _SYMBOL_CODES or kind not in _KIND_CODES:
            raise ValueError("dense store suporta apenas BTC/ETH Binance Spot")
        if not session_id:
            raise ValueError("session_id vazio")
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
                   WHERE venue=? AND symbol=? AND kind=? AND observation_id=?""",
                (*dense_key, *key, *key),
            ).fetchall()
            if existing:
                if any(row["payload_hash"].lower() != digest for row in existing):
                    raise ValueError("observation ID já existe com hash conflitante")
                return False
            self._conn.execute(
                """INSERT INTO microstructure_events_v3
                (kind_code,symbol_code,observation_id,sequence_id,event_us,received_us,
                 ingested_us,session_blob,payload_hash_blob,payload_zlib,quality_flags,session_text)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    _KIND_CODES[kind],
                    _SYMBOL_CODES[symbol],
                    observation_id,
                    sequence_id,
                    _micros(event) if event else None,
                    _micros(received),
                    _micros(ingested),
                    session_id.encode("utf-8"),
                    bytes.fromhex(digest),
                    zlib.compress(encoded.encode("utf-8"), level=6),
                    json.dumps(sorted(quality_flags)),
                    session_id,
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
                    datetime.now(UTC).isoformat(),
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
        rows = self._decoded_rows(latest_only=True)
        latest: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in rows:
            key = (row["venue"], row["symbol"], row["kind"])
            if key not in latest or row["received_at"] > latest[key]["received_at"]:
                latest[key] = row
        return list(latest.values())

    def quality_rows(self, start: datetime, end: datetime) -> list[Any]:
        return self._decoded_rows(
            "WHERE received_at>=? AND received_at<?",
            (_dt(start, "start"), _dt(end, "end")),
        )

    def _decoded_rows(
        self, where: str = "", params: tuple[Any, ...] = (), *, latest_only: bool = False
    ) -> list[dict[str, Any]]:
        columns = (
            "kind,observation_id,venue,symbol,sequence_id,event_at,received_at,ingested_at,"
            "session_id,collector_version,payload_hash,quality_flags,scientific_state"
        )
        if latest_only:
            where = "WHERE (venue,symbol,kind,observation_id) IN (SELECT venue,symbol,kind,observation_id FROM (SELECT venue,symbol,kind,observation_id,ROW_NUMBER() OVER (PARTITION BY venue,symbol,kind ORDER BY received_at DESC,observation_id DESC) AS rn FROM {table}) WHERE rn=1)"
        result: list[dict[str, Any]] = []
        for row in self._conn.execute(
            f"SELECT {columns},payload_json,NULL payload_zlib FROM microstructure_events {where.format(table='microstructure_events')}",
            params,
        ):
            result.append(dict(row))
        for row in self._conn.execute(
            f"SELECT {columns},NULL payload_json,payload_zlib FROM microstructure_events_v2 {where.format(table='microstructure_events_v2')}",
            params,
        ):
            item = dict(row)
            item["payload_json"] = zlib.decompress(item.pop("payload_zlib")).decode("utf-8")
            result.append(item)
        dense_where = ""
        dense_params: tuple[Any, ...] = ()
        if latest_only:
            dense_where = "WHERE (symbol_code,kind_code,observation_id) IN (SELECT symbol_code,kind_code,observation_id FROM (SELECT symbol_code,kind_code,observation_id,ROW_NUMBER() OVER (PARTITION BY symbol_code,kind_code ORDER BY received_us DESC,observation_id DESC) AS rn FROM microstructure_events_v3) WHERE rn=1)"
        elif where:
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
                    "session_id": item["session_text"]
                    if item["session_text"] is not None
                    else (
                        item["session_blob"].hex()
                        if len(item["session_blob"]) == 16
                        else item["session_blob"].decode("utf-8")
                    ),
                    "collector_version": item["collector_version"],
                    "payload_hash": item["payload_hash_blob"].hex(),
                    "quality_flags": item["quality_flags"],
                    "scientific_state": SCIENTIFIC_STATE,
                    "payload_json": zlib.decompress(item["payload_zlib"]).decode("utf-8"),
                }
            )
        result.sort(key=lambda item: item["received_at"])
        return result

    def compact_microstructure_v1(self, *, batch_size: int = 10_000) -> dict[str, int]:
        """Verify every field and payload before deleting each copied row.

        Offline maintenance only; preserve a backup before calling.
        """
        return self._compact(1, batch_size)

    def compact_microstructure_v2(self, *, batch_size: int = 10_000) -> dict[str, int]:
        """Copy v2 to dense storage without losing session/version provenance."""
        return self._compact(2, batch_size)

    def _compact(self, version: int, batch_size: int) -> dict[str, int]:
        if batch_size <= 0:
            raise ValueError("batch_size precisa ser positivo")
        source = "microstructure_events" if version == 1 else "microstructure_events_v2"
        target = "microstructure_events_v2" if version == 1 else "microstructure_events_v3"
        before = self._conn.execute(f"SELECT COUNT(*) FROM {source}").fetchone()[0]
        processed = 0
        while True:
            rows = self._conn.execute(
                f"SELECT * FROM {source} ORDER BY rowid LIMIT ?", (batch_size,)
            ).fetchall()
            if not rows:
                break
            with self._conn:
                for raw in rows:
                    row = dict(raw)
                    content = (
                        row["payload_json"].encode("utf-8")
                        if version == 1
                        else zlib.decompress(row["payload_zlib"])
                    )
                    if hashlib.sha256(content).hexdigest() != row["payload_hash"]:
                        raise ValueError("compactacao: hash original nao corresponde ao payload")
                    source_key = (row["venue"], row["symbol"], row["kind"], row["observation_id"])
                    if version == 1:
                        copied = {key: value for key, value in row.items() if key != "payload_json"}
                        copied["payload_zlib"] = zlib.compress(content, 6)
                        predicate = "venue=? AND symbol=? AND kind=? AND observation_id=?"
                        key = source_key
                    else:
                        if (
                            row["venue"] != "binance_spot"
                            or row["symbol"] not in _SYMBOL_CODES
                            or row["kind"] not in _KIND_CODES
                            or row["scientific_state"] != SCIENTIFIC_STATE
                        ):
                            raise ValueError(
                                "compactacao: proveniencia nao representavel no layout denso"
                            )
                        copied = {
                            "kind_code": _KIND_CODES[row["kind"]],
                            "symbol_code": _SYMBOL_CODES[row["symbol"]],
                            "observation_id": row["observation_id"],
                            "sequence_id": row["sequence_id"],
                            "event_us": _micros(datetime.fromisoformat(row["event_at"]))
                            if row["event_at"]
                            else None,
                            "received_us": _micros(datetime.fromisoformat(row["received_at"])),
                            "ingested_us": _micros(datetime.fromisoformat(row["ingested_at"])),
                            "session_blob": row["session_id"].encode("utf-8"),
                            "session_text": row["session_id"],
                            "collector_version": row["collector_version"],
                            "payload_hash_blob": bytes.fromhex(row["payload_hash"]),
                            "payload_zlib": row["payload_zlib"],
                            "quality_flags": row["quality_flags"],
                        }
                        predicate = "symbol_code=? AND kind_code=? AND observation_id=?"
                        key = (copied["symbol_code"], copied["kind_code"], copied["observation_id"])
                    existing = self._conn.execute(
                        f"SELECT * FROM {target} WHERE {predicate}", key
                    ).fetchone()
                    if existing is not None:
                        target_row = dict(existing)
                        if zlib.decompress(target_row["payload_zlib"]) != content:
                            raise ValueError("compactacao: payload conflitante no destino")
                        if version == 2 and target_row["session_text"] is None:
                            blob = target_row["session_blob"]
                            target_row["session_text"] = (
                                blob.hex() if len(blob) == 16 else blob.decode("utf-8")
                            )
                        if any(
                            target_row[k] != v
                            for k, v in copied.items()
                            if k not in {"payload_zlib", "session_blob"}
                        ):
                            raise ValueError("compactacao: metadados conflitantes no destino")
                    else:
                        self._conn.execute(
                            f"INSERT INTO {target} ({','.join(copied)}) VALUES ({','.join('?' for _ in copied)})",
                            tuple(copied.values()),
                        )
                    self._conn.execute(
                        f"DELETE FROM {source} WHERE venue=? AND symbol=? AND kind=? AND observation_id=?",
                        source_key,
                    )
            processed += len(rows)
        return {f"v{version}_before": before, "processed": processed, f"v{version}_after": 0}
