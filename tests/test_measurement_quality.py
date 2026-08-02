"""Qualidade de medição (jul/2026) — 4 melhorias aditivas:

1. Preço realizado OFFLINE-FIRST: o backtest mede o retorno na MESMA família de
   fontes da previsão (Feature Store), caindo para CoinGecko só sem dado local.
2. Flag input_degradado persistido na previsão (migração 0008) — estratificável.
3. series_quality na ingestão: gaps e saltos overnight nunca entram em silêncio.
4. utc_stamp: previsões carimbadas em UTC (fim da ambiguidade local vs UTC).

Tudo offline e determinístico.
"""

import sqlite3
from datetime import UTC, datetime, timedelta, timezone

import pytest

from GarimpoInvestimentos.analyzers import backtest
from GarimpoInvestimentos.core.history import to_prediction_rows, utc_stamp
from GarimpoInvestimentos.dpl import FeatureStore, MarketDataPoint
from GarimpoInvestimentos.dpl.ingest import series_quality

UTC = UTC
DAY = datetime(2026, 7, 1, tzinfo=UTC)


def _candle(ts, close, source="binance"):
    return MarketDataPoint(
        symbol="bitcoin",
        timestamp=ts,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=100.0,
        source=source,
        interval="1d",
        published_at=ts,
    )


@pytest.fixture
def store(tmp_path):
    with FeatureStore(tmp_path / "fs.db") as s:
        yield s


# --- 1a. close_on: régua offline -----------------------------------------------


def test_close_on_retorna_fecho_e_fonte(store):
    store.write_raw([_candle(DAY, 100.0)])
    assert store.close_on("bitcoin", "1d", DAY) == (100.0, "binance")


def test_close_on_prefere_a_politica_da_previsao(store):
    store.write_raw(
        [
            _candle(DAY, 100.0, source="binance"),
            _candle(DAY, 101.0, source="consensus_binance_kraken"),
        ]
    )
    close, src = store.close_on("bitcoin", "1d", DAY, prefer_consensus=True)
    assert src.startswith("consensus")
    close, src = store.close_on("bitcoin", "1d", DAY, prefer_consensus=False)
    assert src == "binance"


def test_close_on_sem_dado_no_dia_e_none(store):
    store.write_raw([_candle(DAY, 100.0)])
    assert store.close_on("bitcoin", "1d", DAY + timedelta(days=1)) is None


# --- 1b. _realized_price: offline-first, rede só no fallback --------------------


async def _boom(*a, **k):
    raise AssertionError("rede usada com dado disponível na store")


def test_preco_realizado_usa_store_sem_tocar_rede(store, monkeypatch):
    import asyncio

    monkeypatch.setattr(backtest, "_price_on", _boom)  # rede = falha do teste
    store.write_raw([_candle(DAY, 100.0)])
    price, medida = asyncio.run(
        backtest._realized_price(
            store, client=None, ativo="bitcoin", fonte="dpl:fallback", day=DAY.replace(tzinfo=None)
        )
    )
    assert price == 100.0
    assert medida == "store:binance"  # carimbo da régua usada


def test_preco_realizado_cai_para_coingecko_sem_dado_local(store, monkeypatch):
    import asyncio

    async def fake_price(client, coin_id, day):
        return 123.0

    async def no_sleep(_):
        return None

    monkeypatch.setattr(backtest, "_price_on", fake_price)
    monkeypatch.setattr(backtest.asyncio, "sleep", no_sleep)
    price, medida = asyncio.run(
        backtest._realized_price(
            store, client=None, ativo="bitcoin", fonte="direct", day=DAY.replace(tzinfo=None)
        )
    )
    assert (price, medida) == (123.0, "coingecko")


# --- 2. input_degradado: persistência e semântica NULL --------------------------


def test_flag_degradado_mapeado_e_persistido(store):
    rows = to_prediction_rows(
        [
            {"ativo": "bitcoin", "data": "2026-07-01 10:00:00", "score": 70, "input_degradado": 1},
            {"ativo": "solana", "data": "2026-07-01 10:00:00", "score": 60, "input_degradado": 0},
            {"ativo": "cardano", "data": "2026-07-01 10:00:00", "score": 50},  # legado
        ]
    )
    store.write_predictions(rows)
    got = {r["ativo"]: r["input_degradado"] for r in store.read_predictions()}
    assert got == {"BITCOIN": 1, "SOLANA": 0, "CARDANO": None}


def test_migration_0008_deixa_linhas_antigas_como_null(tmp_path):
    """Linha pré-0008 lê NULL ('não medido na época'), NUNCA 0 ('completo')."""
    from GarimpoInvestimentos.dpl.migrations._0006_predictions import SQL as SQL6
    from GarimpoInvestimentos.dpl.migrations._0008_predictions_degraded import SQL as SQL8

    conn = sqlite3.connect(tmp_path / "legacy.db")
    conn.row_factory = sqlite3.Row
    conn.executescript(SQL6)
    conn.execute(
        "INSERT INTO predictions (ativo, ts, score) VALUES ('BITCOIN','2026-06-01 10:00:00',70)"
    )
    conn.executescript(SQL8)
    row = conn.execute("SELECT input_degradado FROM predictions").fetchone()
    conn.close()
    assert row["input_degradado"] is None


# --- 3. series_quality: gaps e saltos ------------------------------------------


def _series(days_closes):
    return [_candle(DAY + timedelta(days=d), c) for d, c in days_closes]


def test_serie_limpa_sem_avisos():
    q = series_quality(_series([(0, 100), (1, 102), (2, 101)]))
    assert q == {"n_gaps": 0, "jumps": []}


def test_gap_de_um_dia_e_detectado():
    q = series_quality(_series([(0, 100), (1, 102), (3, 101)]))  # dia 2 faltando
    assert q["n_gaps"] == 1


def test_salto_overnight_anomalo_e_detectado():
    q = series_quality(_series([(0, 100), (1, 145)]))  # +45% overnight
    assert len(q["jumps"]) == 1
    assert q["jumps"][0][1] == pytest.approx(0.45)


def test_queda_normal_nao_dispara():
    q = series_quality(_series([(0, 100), (1, 85)]))  # −15%: volátil, mas normal
    assert q["jumps"] == []


# --- 4. utc_stamp ----------------------------------------------------------------


def test_utc_stamp_e_utc_no_formato_do_historico():
    stamp = utc_stamp()
    parsed = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
    delta = abs(datetime.now(timezone.utc).replace(tzinfo=None) - parsed)
    assert delta < timedelta(seconds=5)  # é UTC de verdade, não hora local
