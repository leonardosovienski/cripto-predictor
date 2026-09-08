"""Testes da Fase 4 — COTAHIST, BCB (mock), point-in-time/vintage e ingestão de ações."""

import asyncio
from datetime import UTC, datetime, timedelta

from GarimpoInvestimentos.dpl import (
    AlignmentEngine,
    FeatureStore,
    SignalPoint,
    StocksDataProvider,
    ingest_stocks,
)
from GarimpoInvestimentos.dpl.providers.cotahist import (
    COTAHISTProvider,
    parse_cotahist_lines,
)

UTC = UTC


def _cotahist_line(
    date="20260102",
    codbdi="02",
    ticker="PETR4",
    tpmerc="010",
    o=3050,
    h=3100,
    lo=3000,
    c=3080,
    vol=10000000,
) -> str:
    """Monta uma linha COTAHIST tipo 01 (preços ×100, posições 1-indexadas)."""
    buf = [" "] * 245

    def put(start, end, text):
        buf[start - 1 : end] = list(text.rjust(end - start + 1)[: end - start + 1])

    put(1, 2, "01")
    put(3, 10, date)
    put(11, 12, codbdi)
    buf[12:24] = list(ticker.ljust(12))  # CODNEG é à esquerda
    put(25, 27, tpmerc)
    put(57, 69, str(o).zfill(13))
    put(70, 82, str(h).zfill(13))
    put(83, 95, str(lo).zfill(13))
    put(109, 121, str(c).zfill(13))
    put(171, 188, str(vol).zfill(18))
    return "".join(buf)


# --- COTAHIST parser ---------------------------------------------------------


def test_cotahist_parse_basico():
    pts = parse_cotahist_lines([_cotahist_line()])
    assert len(pts) == 1
    p = pts[0]
    assert p.symbol == "PETR4" and p.source == "cotahist"
    assert p.open == 30.50 and p.high == 31.00 and p.low == 30.00 and p.close == 30.80
    assert p.volume == 100000.0  # 10000000 / 100


def test_cotahist_published_at_apos_fechamento():
    p = parse_cotahist_lines([_cotahist_line()], publish_lag_hours=18)[0]
    assert p.published_at == p.timestamp + timedelta(hours=18)  # anti-lookahead


def test_cotahist_filtra_bdi_e_mercado():
    # CODBDI 96 (fracionário) e TPMERC 070 (opções) são descartados por padrão
    linhas = [_cotahist_line(codbdi="96"), _cotahist_line(tpmerc="070")]
    assert parse_cotahist_lines(linhas) == []


def test_cotahist_linha_invalida_nao_aborta_lote():
    erros = []
    linhas = [_cotahist_line(c=0), _cotahist_line(ticker="VALE3")]  # close<=0 inválido
    pts = parse_cotahist_lines(linhas, on_error=lambda l, w: erros.append(w))
    assert [p.symbol for p in pts] == ["VALE3"] and len(erros) == 1


def test_cotahist_provider_fetch(tmp_path):
    f = tmp_path / "COTAHIST.TXT"
    f.write_text(
        "\n".join([_cotahist_line(date="20260102"), _cotahist_line(date="20260103", c=3120)]),
        encoding="latin-1",
    )
    prov = COTAHISTProvider(f)
    pts = asyncio.run(prov.fetch_ohlcv("PETR4", limit=1))
    assert pts[-1].close == 31.20


# --- Point-in-time / vintage (o item de maior risco da Fase 4) ---------------


def _candle(day, close):
    from GarimpoInvestimentos.dpl import MarketDataPoint

    ts = datetime(2026, day // 100, day % 100, tzinfo=UTC)
    return MarketDataPoint(
        symbol="PETR4",
        timestamp=ts,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=0,
        source="cotahist",
        interval="1d",
        published_at=ts + timedelta(hours=18),
    )


def test_alignment_point_in_time_nao_usa_revisao_futura():
    """IPCA de março: v1 (0.40, público 10/abr) e revisão v2 (0.43, público 15/mai).
    Backtest em 20/abr deve ver 0.40; em 20/mai, 0.43 — sem lookahead."""
    ref = datetime(2026, 3, 31, tzinfo=UTC)
    v1 = SignalPoint(
        "ipca",
        ref,
        0.40,
        "bcb_sgs",
        datetime(2026, 4, 10, tzinfo=UTC),
        reference_date=ref,
        vintage=datetime(2026, 4, 10, tzinfo=UTC),
    )
    v2 = SignalPoint(
        "ipca",
        ref,
        0.43,
        "bcb_sgs",
        datetime(2026, 5, 15, tzinfo=UTC),
        reference_date=ref,
        vintage=datetime(2026, 5, 15, tzinfo=UTC),
    )
    candles = [_candle(420, 100), _candle(520, 110)]  # 20/abr, 20/mai
    rows = AlignmentEngine().align(candles, {"ipca": [v1, v2]})
    assert rows[0]["ipca"] == 0.40  # 20/abr vê só a v1
    assert rows[1]["ipca"] == 0.43  # 20/mai já vê a revisão


def test_feature_store_vintages_coexistem(tmp_path):
    ref = datetime(2026, 3, 31, tzinfo=UTC)
    v1 = SignalPoint(
        "ipca",
        ref,
        0.40,
        "bcb_sgs",
        datetime(2026, 4, 10, tzinfo=UTC),
        vintage=datetime(2026, 4, 10, tzinfo=UTC),
    )
    v2 = SignalPoint(
        "ipca",
        ref,
        0.43,
        "bcb_sgs",
        datetime(2026, 5, 15, tzinfo=UTC),
        vintage=datetime(2026, 5, 15, tzinfo=UTC),
    )
    with FeatureStore(tmp_path / "fs.db") as fs:
        fs.write_signals([v1, v2])
        got = fs.read_signals("bcb_sgs", "ipca")
    assert len(got) == 2 and {g.value for g in got} == {0.40, 0.43}


# --- BCBProvider (httpx mockado) ---------------------------------------------


def test_bcb_provider_parse_e_published_at(monkeypatch):
    from GarimpoInvestimentos.dpl.providers import bcb

    class _Resp:
        def raise_for_status(self): ...
        def json(self):
            return [{"data": "31/03/2026", "valor": "0.40"}]

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a): ...
        async def get(self, url, params=None):
            return _Resp()

    monkeypatch.setattr(bcb, "get_http_client", lambda *a, **k: _Client())
    prov = bcb.BCBProvider(433, "ipca", publish_lag_days=11)
    pts = asyncio.run(prov.fetch(limit=1, collected_at=datetime(2026, 4, 12, tzinfo=UTC)))
    assert pts[0].value == 0.40
    assert pts[0].reference_date == datetime(2026, 3, 31, tzinfo=UTC)
    assert pts[0].published_at == datetime(2026, 4, 11, tzinfo=UTC)  # ref + 11 dias
    assert pts[0].vintage == datetime(2026, 4, 12, tzinfo=UTC)


# --- Ingestão de ações (fim-a-fim, offline) ----------------------------------


def test_ingest_stocks_materializa_e_registra_proveniencia(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(tmp_path / "ev.jsonl"))
    f = tmp_path / "COTAHIST.TXT"
    f.write_text(
        "\n".join(
            [_cotahist_line(date="20260102", c=3050), _cotahist_line(date="20260103", c=3120)]
        ),
        encoding="latin-1",
    )

    from GarimpoInvestimentos.dpl.signals import SignalProvider

    class _FakeSelic(SignalProvider):
        name = "selic"

        async def fetch(self, limit=30, **kw):
            ts = datetime(2026, 1, 1, tzinfo=UTC)
            return [SignalPoint("selic", ts, 11.25, "bcb_sgs", ts, reference_date=ts, vintage=ts)]

    facade = StocksDataProvider.from_cotahist(f, signal_providers=[_FakeSelic()])
    with FeatureStore(tmp_path / "fs.db") as fs:
        aligned = asyncio.run(
            ingest_stocks(
                fs, facade, "PETR4", limit=10, ingested_at=datetime(2026, 1, 4, tzinfo=UTC)
            )
        )
        served = fs.read_features("PETR4", "1d")
        prov = fs._conn.execute("SELECT * FROM ingestion_provenance").fetchall()
    assert len(aligned) == 2
    assert served[-1]["selic"] == 11.25  # macro alinhado ao candle
    assert served[-1]["close"] == 31.20
    assert len(prov) == 1 and prov[0]["entity"] == "PETR4" and prov[0]["source"] == "stocks"
