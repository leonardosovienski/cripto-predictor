"""Feature Store local (SQLite) — repositório offline de dados de mercado.

Separa INGESTÃO (escrita de dados brutos + materialização de features) de SERVING
(leitura pelo domínio). Três tabelas (ver docs/DOSSIE_PLATAFORMA.md §5.9):

  - raw_market_data : OHLCV bruto, uma linha por (source, symbol, interval, ts).
                      Tabelas "brutas por fonte" via a coluna `source`.
  - raw_signals     : sinais de baixa frequência (ex.: fear_greed), shape não-OHLCV.
  - features_aligned: matriz materializada pelo Alignment Engine (formato longo:
                      uma linha por feature). `value` NULL == NaN (stale/ausente).

Construída sobre predictor_core.infra (WAL + migração idempotente). O domínio nunca
acessa APIs externas: lê apenas daqui.
"""
from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from predictor_core import infra

from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.signals import SignalPoint

_MIGRATIONS = [
    ("0001_raw_market_data", """
        CREATE TABLE IF NOT EXISTS raw_market_data (
            source       TEXT NOT NULL,
            symbol       TEXT NOT NULL,
            interval     TEXT NOT NULL,
            ts           TEXT NOT NULL,
            open         REAL NOT NULL,
            high         REAL NOT NULL,
            low          REAL NOT NULL,
            close        REAL NOT NULL,
            volume       REAL NOT NULL,
            published_at TEXT NOT NULL,
            PRIMARY KEY (source, symbol, interval, ts)
        );
    """),
    ("0002_raw_signals", """
        CREATE TABLE IF NOT EXISTS raw_signals (
            source       TEXT NOT NULL,
            name         TEXT NOT NULL,
            ts           TEXT NOT NULL,
            value        REAL NOT NULL,
            published_at TEXT NOT NULL,
            PRIMARY KEY (source, name, ts)
        );
    """),
    ("0003_features_aligned", """
        CREATE TABLE IF NOT EXISTS features_aligned (
            symbol   TEXT NOT NULL,
            interval TEXT NOT NULL,
            ts       TEXT NOT NULL,
            feature  TEXT NOT NULL,
            value    REAL,
            PRIMARY KEY (symbol, interval, ts, feature)
        );
    """),
]


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


class FeatureStore:
    def __init__(self, db_path: Path | str):
        self._conn = infra.connect(db_path)
        infra.run_migrations(self._conn, _MIGRATIONS)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "FeatureStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- Ingestão (escrita) --------------------------------------------------

    def write_raw(self, points: list[MarketDataPoint]) -> int:
        """Upsert idempotente de candles OHLCV. Retorna nº de linhas escritas."""
        rows = [
            (p.source, p.symbol, p.interval, _iso(p.timestamp),
             p.open, p.high, p.low, p.close, p.volume, _iso(p.published_at))
            for p in points
        ]
        self._conn.executemany(
            """INSERT INTO raw_market_data
               (source, symbol, interval, ts, open, high, low, close, volume, published_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source, symbol, interval, ts) DO UPDATE SET
                 open=excluded.open, high=excluded.high, low=excluded.low,
                 close=excluded.close, volume=excluded.volume,
                 published_at=excluded.published_at""",
            rows,
        )
        self._conn.commit()
        return len(rows)

    def write_signals(self, signals: list[SignalPoint]) -> int:
        rows = [
            (s.source, s.name, _iso(s.timestamp), s.value, _iso(s.published_at))
            for s in signals
        ]
        self._conn.executemany(
            """INSERT INTO raw_signals (source, name, ts, value, published_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(source, name, ts) DO UPDATE SET
                 value=excluded.value, published_at=excluded.published_at""",
            rows,
        )
        self._conn.commit()
        return len(rows)

    def write_features(self, symbol: str, interval: str,
                       rows: list[dict]) -> int:
        """Materializa features alinhadas. Cada row: {ts: datetime, <feat>: value}.
        Valores NaN/None viram NULL (serving os reconstrói como NaN).
        """
        flat = []
        for row in rows:
            ts = _iso(row["ts"])
            for feat, val in row.items():
                if feat == "ts":
                    continue
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    val = None
                flat.append((symbol, interval, ts, feat, val))
        self._conn.executemany(
            """INSERT INTO features_aligned (symbol, interval, ts, feature, value)
               VALUES (?,?,?,?,?)
               ON CONFLICT(symbol, interval, ts, feature) DO UPDATE SET
                 value=excluded.value""",
            flat,
        )
        self._conn.commit()
        return len(flat)

    # --- Serving (leitura) ---------------------------------------------------

    def read_raw(self, symbol: str, interval: str,
                 source: str | None = None) -> list[MarketDataPoint]:
        sql = ("SELECT * FROM raw_market_data WHERE symbol=? AND interval=?")
        params: list = [symbol, interval]
        if source:
            sql += " AND source=?"
            params.append(source)
        sql += " ORDER BY ts"
        return [
            MarketDataPoint(
                symbol=r["symbol"], timestamp=_parse(r["ts"]),
                open=r["open"], high=r["high"], low=r["low"], close=r["close"],
                volume=r["volume"], source=r["source"], interval=r["interval"],
                published_at=_parse(r["published_at"]),
            )
            for r in self._conn.execute(sql, params)
        ]

    def read_features(self, symbol: str, interval: str) -> list[dict]:
        """Retorna a matriz alinhada em formato LARGO, ordenada por ts.
        NULL volta como float('nan'). Cada dict: {ts, <feature>: value, ...}.
        """
        cur = self._conn.execute(
            """SELECT ts, feature, value FROM features_aligned
               WHERE symbol=? AND interval=? ORDER BY ts""",
            (symbol, interval),
        )
        wide: dict[str, dict] = {}
        for r in cur:
            row = wide.setdefault(r["ts"], {"ts": _parse(r["ts"])})
            row[r["feature"]] = float("nan") if r["value"] is None else r["value"]
        return [wide[k] for k in sorted(wide)]
