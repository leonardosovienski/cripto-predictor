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
from datetime import datetime, timedelta
from pathlib import Path

from predictor_core import infra

from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.migrations import ADDITIVE_MIGRATIONS
from GarimpoInvestimentos.dpl.signals import SignalPoint

# Versão do schema da Feature Store (base 0001-0004 + aditivas em dpl/migrations/).
SCHEMA_VERSION = 8

# Guard de integridade temporal na INSERÇÃO (auditoria jul/2026) — duas pontas:
#   published_at <  timestamp            → look-ahead de rotulagem (publicou antes
#                                          de observar — vazamento na origem);
#   published_at >  timestamp + este teto → staleness/rotulagem anômala.
# Teto default folgado (macro BCB mensal publica ~M+1; candles publicam no próprio
# ts nos providers atuais). Ajustável por instância para domínios de lag maior.
MAX_PUBLICATION_LAG = timedelta(days=45)

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
    # NOTA: 0002 mantém o schema ORIGINAL (PK source,name,ts). A evolução para o
    # schema com vintage/reference_date é feita pela migração ADITIVA 0005 (ver
    # dpl/migrations/) — nunca alterando esta migração in-place (ADR-017 / auditoria C-04).
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
    ("0004_ingestion_provenance", """
        CREATE TABLE IF NOT EXISTS ingestion_provenance (
            run_id       TEXT,
            source       TEXT NOT NULL,
            entity       TEXT NOT NULL,
            origin       TEXT,
            vintage      TEXT,
            n_rows       INTEGER NOT NULL,
            ingested_at  TEXT NOT NULL,
            code_version TEXT
        );
    """),
]


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


class FeatureStore:
    def __init__(self, db_path: Path | str, *,
                 max_publication_lag: timedelta = MAX_PUBLICATION_LAG):
        self._conn = infra.connect(db_path)
        self._max_publication_lag = max_publication_lag
        # Schema base (0001-0004) + migrações aditivas (0005+, em dpl/migrations/).
        # run_migrations é idempotente por nome → seguro para DBs em qualquer versão.
        infra.run_migrations(self._conn, _MIGRATIONS + ADDITIVE_MIGRATIONS)

    def _check_temporal(self, label: str, timestamp: datetime,
                        published_at: datetime) -> None:
        """Fail-fast bidirecional (ver MAX_PUBLICATION_LAG). Lança ValueError —
        dado com carimbo temporal impossível NUNCA entra na store."""
        if published_at < timestamp:
            raise ValueError(
                f"integridade temporal [{label}]: published_at ({published_at}) < "
                f"timestamp ({timestamp}) — look-ahead de rotulagem na origem")
        if published_at > timestamp + self._max_publication_lag:
            raise ValueError(
                f"integridade temporal [{label}]: published_at ({published_at}) excede "
                f"timestamp + {self._max_publication_lag} — rotulagem anômala/stale "
                "(se o lag é legítimo, ajuste max_publication_lag da instância)")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "FeatureStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- Ingestão (escrita) --------------------------------------------------

    def write_raw(self, points: list[MarketDataPoint]) -> int:
        """Upsert idempotente de candles OHLCV. Retorna nº de linhas escritas."""
        for p in points:
            self._check_temporal(f"{p.source}/{p.symbol}", p.timestamp, p.published_at)
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
        """Upsert de sinais. A PK inclui `vintage`, então revisões (mesmo ts, vintage
        distinto) COEXISTEM — base do point-in-time. Sem vintage → '' (ex.: Fear&Greed).
        """
        for s in signals:
            self._check_temporal(f"{s.source}/{s.name}", s.timestamp, s.published_at)
        rows = [
            (s.source, s.name, _iso(s.timestamp),
             _iso(s.reference_date) if s.reference_date else None,
             s.value, _iso(s.published_at),
             _iso(s.vintage) if s.vintage else "")
            for s in signals
        ]
        self._conn.executemany(
            """INSERT INTO raw_signals
               (source, name, ts, reference_date, value, published_at, vintage)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(source, name, ts, vintage) DO UPDATE SET
                 reference_date=excluded.reference_date, value=excluded.value,
                 published_at=excluded.published_at""",
            rows,
        )
        self._conn.commit()
        return len(rows)

    def read_signals(self, source: str, name: str) -> list[SignalPoint]:
        """Lê todos os pontos (incl. todas as vintages) de um sinal, ordenados por ts."""
        cur = self._conn.execute(
            """SELECT * FROM raw_signals WHERE source=? AND name=? ORDER BY ts, vintage""",
            (source, name),
        )
        return [
            SignalPoint(
                name=r["name"], timestamp=_parse(r["ts"]), value=r["value"],
                source=r["source"], published_at=_parse(r["published_at"]),
                reference_date=_parse(r["reference_date"]) if r["reference_date"] else None,
                vintage=_parse(r["vintage"]) if r["vintage"] else None,
            )
            for r in cur
        ]

    def write_provenance(self, *, source: str, entity: str, n_rows: int,
                         ingested_at, run_id: str | None = None, origin: str | None = None,
                         vintage=None, code_version: str | None = None) -> None:
        """Registra a origem de um lote ingerido (auditoria origem→feature→modelo)."""
        self._conn.execute(
            """INSERT INTO ingestion_provenance
               (run_id, source, entity, origin, vintage, n_rows, ingested_at, code_version)
               VALUES (?,?,?,?,?,?,?,?)""",
            (run_id, source, entity, origin,
             _iso(vintage) if vintage else None, n_rows, _iso(ingested_at), code_version),
        )
        self._conn.commit()

    def write_features(self, symbol: str, interval: str,
                       rows: list[dict], *, feature_version: str = "v1") -> int:
        """Materializa features alinhadas. Cada row: {ts: datetime, <feat>: value}.
        Valores NaN/None viram NULL (serving os reconstrói como NaN).

        `feature_version` (migração 0007): mudar a LÓGICA de cálculo de uma feature
        exige uma versão nova — versões coexistem na PK, então um backfill com
        lógica nova nunca sobrescreve o histórico que experimentos passados leram.
        Reexecutar a MESMA lógica na mesma versão continua sendo upsert idempotente.
        """
        flat = []
        for row in rows:
            ts = _iso(row["ts"])
            for feat, val in row.items():
                if feat == "ts":
                    continue
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    val = None
                flat.append((symbol, interval, ts, feat, val, feature_version))
        self._conn.executemany(
            """INSERT INTO features_aligned (symbol, interval, ts, feature, value, feature_version)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(symbol, interval, ts, feature, feature_version) DO UPDATE SET
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

    def read_features(self, symbol: str, interval: str, *,
                      feature_version: str = "v1") -> list[dict]:
        """Retorna a matriz alinhada em formato LARGO, ordenada por ts.
        NULL volta como float('nan'). Cada dict: {ts, <feature>: value, ...}.
        Lê UMA versão de features (default 'v1') — experimentos fixam a sua.
        """
        cur = self._conn.execute(
            """SELECT ts, feature, value FROM features_aligned
               WHERE symbol=? AND interval=? AND feature_version=? ORDER BY ts""",
            (symbol, interval, feature_version),
        )
        wide: dict[str, dict] = {}
        for r in cur:
            row = wide.setdefault(r["ts"], {"ts": _parse(r["ts"])})
            row[r["feature"]] = float("nan") if r["value"] is None else r["value"]
        return [wide[k] for k in sorted(wide)]

    def latest_features(self, symbol: str, interval: str) -> dict | None:
        """Linha alinhada mais recente (formato largo) ou None se não houver dados.

        É o ponto de entrada do serving para o pipeline de previsão: devolve preço,
        sentimento e indicadores já materializados, sem tocar a rede.
        """
        rows = self.read_features(symbol, interval)
        return rows[-1] if rows else None

    # --- Histórico oficial de previsões (passo 4 — aposenta o CSV) -----------

    PREDICTION_FIELDS = ("ativo", "ts", "score", "sentimento", "resumo",
                         "price_usd", "juiz", "divergencia", "fonte",
                         "input_degradado", "llm_fallback", "news_provider",
                         "news_degraded_reason", "collection_policy")

    def write_predictions(self, rows: list[dict]) -> int:
        """Upsert de previsões. PK (ativo, ts): reexecução/cache hit não infla o n
        do backtest (mesma semântica do dedup do CSV legado).
        `input_degradado` (0008): 1 = LLM pontuou com input empobrecido; 0 =
        completo; NULL = linha pré-flag (legado) — o backtest estratifica.
        `llm_fallback` (0009): 1 = o LLM falhou e a linha é o fallback neutro
        (score 50, sem análise real); NULL = pré-flag (o backtest cobre o legado
        pelo marcador no resumo)."""
        data = [tuple(r.get(f) for f in self.PREDICTION_FIELDS) for r in rows]
        self._conn.executemany(
            """INSERT INTO predictions
               (ativo, ts, score, sentimento, resumo, price_usd, juiz, divergencia,
                fonte, input_degradado, llm_fallback, news_provider, news_degraded_reason,
                collection_policy)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(ativo, ts) DO UPDATE SET
                 score=excluded.score, sentimento=excluded.sentimento,
                 resumo=excluded.resumo, price_usd=excluded.price_usd,
                 juiz=excluded.juiz, divergencia=excluded.divergencia,
                 fonte=excluded.fonte, input_degradado=excluded.input_degradado,
                 llm_fallback=excluded.llm_fallback,
                 news_provider=excluded.news_provider,
                 news_degraded_reason=excluded.news_degraded_reason,
                 collection_policy=excluded.collection_policy""",
            data,
        )
        self._conn.commit()
        return len(data)

    def read_predictions(self) -> list[dict]:
        """Todas as previsões em ORDEM TEMPORAL (o block bootstrap depende disso)."""
        cur = self._conn.execute(
            "SELECT * FROM predictions ORDER BY ts, ativo")
        return [dict(r) for r in cur]

    def predictions_on(self, day_utc: str) -> list[tuple[str, str]]:
        """Pares (ativo, juiz) com previsão REAL (não-fallback) gravada no dia UTC
        (prefixo YYYY-MM-DD do ts). API pública da idempotência da coleta diária
        (garimpo_fase1): linha de fallback (llm_fallback=1) não conta como coletada."""
        cur = self._conn.execute(
            """SELECT ativo, juiz FROM predictions
               WHERE ts LIKE ? AND COALESCE(llm_fallback, 0) = 0""",
            (f"{day_utc}%",),
        )
        return [(r["ativo"], r["juiz"] or "") for r in cur]

    def last_prediction_ts_by_asset(self) -> dict[str, str]:
        """MAX(ts) da previsão REAL (não-fallback) por ativo (chave minúscula).
        Usado para ordenar o universo quando o api_guard corta: quem está há mais
        tempo sem previsão vai primeiro — o corte se distribui em vez de furar
        sempre os mesmos ativos do fim da lista."""
        cur = self._conn.execute(
            """SELECT ativo, MAX(ts) FROM predictions
               WHERE COALESCE(llm_fallback, 0) = 0 GROUP BY ativo""")
        return {(r[0] or "").lower(): r[1] for r in cur}

    def list_symbols(self, interval: str = "1d") -> list[str]:
        """Símbolos com features materializadas — universo default da análise quando
        não há --assets (ADR do merge, D3)."""
        cur = self._conn.execute(
            """SELECT DISTINCT symbol FROM features_aligned
               WHERE interval=? ORDER BY symbol""",
            (interval,),
        )
        return [r["symbol"] for r in cur]

    def close_on(self, symbol: str, interval: str, day: datetime, *,
                 prefer_consensus: bool = False) -> tuple[float, str] | None:
        """Fecho do candle bruto do DIA (YYYY-MM-DD) — régua OFFLINE do backtest.

        Motivação (auditoria jul/2026): medir o retorno realizado numa fonte
        diferente da que gerou a previsão adiciona ruído (a equivalência mediu
        até 7.8pp de diff entre fontes). Se múltiplas fontes têm o dia, prefere
        a que casa com a política da previsão (consenso ou provider único).
        Retorna (close, source) ou None se a store não tem o dia."""
        cur = self._conn.execute(
            """SELECT close, source FROM raw_market_data
               WHERE symbol=? AND interval=? AND substr(ts,1,10)=?""",
            (symbol, interval, day.strftime("%Y-%m-%d")),
        )
        rows = [(r["close"], r["source"]) for r in cur]
        if not rows:
            return None
        # candidatas que casam com a política primeiro; empate → ordem alfabética
        # de source (determinístico entre execuções).
        rows.sort(key=lambda cs: (cs[1].startswith("consensus") != prefer_consensus,
                                  cs[1]))
        return rows[0]

    def latest_source(self, symbol: str, interval: str = "1d") -> str | None:
        """`source` do candle bruto mais recente do símbolo — insumo do carimbo
        Fonte (ADR do merge, D2). None se o símbolo não existe na store."""
        cur = self._conn.execute(
            """SELECT source FROM raw_market_data
               WHERE symbol=? AND interval=? ORDER BY ts DESC LIMIT 1""",
            (symbol, interval),
        )
        row = cur.fetchone()
        return row["source"] if row else None


def fonte_label(source: str | None) -> str:
    """Carimbo Fonte (ADR do merge, D2) a partir do `source` bruto do candle.

    Valores: 'dpl:consensus' (candle fundido pela agregação), 'dpl:fallback'
    (candle de um provider único via router) ou 'direct' (sem dado na store —
    só ocorre em linhas legadas pré-DPL; o backtest lê coluna vazia como direct).
    O rótulo registra a POLÍTICA; o provider exato fica em raw_market_data.source
    e na telemetria — não duplicar."""
    if not source:
        return "direct"
    return "dpl:consensus" if source.startswith("consensus") else "dpl:fallback"
