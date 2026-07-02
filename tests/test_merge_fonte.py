"""Integração do merge DPL + discovery (ADR docs/DECISAO_MERGE_DPL_DISCOVERY.md).

Cobre as três decisões: D2 (carimbo Fonte: fonte_label + coluna no histórico com
migração aditiva de header) e D3 (universo default da análise = Feature Store via
list_symbols; latest_source alimenta o carimbo). D1 (altcoin sem symbol_map cai no
CoinGecko) já é coberta pelo teste de fachada da Fase 1 + validada em smoke ao vivo.
"""
from datetime import datetime, timezone

from GarimpoInvestimentos.dpl import FeatureStore, MarketDataPoint
from GarimpoInvestimentos.dpl.feature_store import fonte_label

UTC = timezone.utc


def _candle(symbol, source, ts):
    return MarketDataPoint(
        source=source, symbol=symbol, interval="1d", timestamp=ts,
        open=1.0, high=2.0, low=0.5, close=1.5, volume=100.0, published_at=ts,
    )


# --- D2: rótulo do carimbo -------------------------------------------------

def test_fonte_label_mapeia_politicas():
    assert fonte_label("coingecko") == "dpl:fallback"
    assert fonte_label("binance") == "dpl:fallback"
    assert fonte_label("consensus_median") == "dpl:consensus"
    assert fonte_label("consensus_mean") == "dpl:consensus"
    assert fonte_label(None) == "direct"
    assert fonte_label("") == "direct"


def test_latest_source_devolve_fonte_do_candle_mais_recente(tmp_path):
    with FeatureStore(tmp_path / "fs.db") as fs:
        fs.write_raw([
            _candle("bitcoin", "binance", datetime(2026, 6, 30, tzinfo=UTC)),
            _candle("bitcoin", "coingecko", datetime(2026, 7, 1, tzinfo=UTC)),
        ])
        assert fs.latest_source("bitcoin", "1d") == "coingecko"   # o mais recente
        assert fs.latest_source("inexistente", "1d") is None
        assert fonte_label(fs.latest_source("inexistente", "1d")) == "direct"


# --- D3: universo default da análise ---------------------------------------

def test_list_symbols_devolve_universo_materializado(tmp_path):
    ts = datetime(2026, 7, 1, tzinfo=UTC)
    with FeatureStore(tmp_path / "fs.db") as fs:
        fs.write_features("bitcoin", "1d", [{"ts": ts, "close": 60000.0}])
        fs.write_features("kaspa", "1d", [{"ts": ts, "close": 0.1}])
        fs.write_features("bitcoin", "4h", [{"ts": ts, "close": 60000.0}])  # outro intervalo
        assert fs.list_symbols("1d") == ["bitcoin", "kaspa"]
        assert fs.list_symbols("1w") == []


# --- D2: coluna Fonte no histórico (com migração de header) ----------------

def test_append_history_grava_fonte_e_migra_header_antigo(tmp_path, monkeypatch):
    from GarimpoInvestimentos.core import history

    hist = tmp_path / "garimpo_historico.csv"
    monkeypatch.setattr(history, "HIST_CSV", str(hist))

    # 1) arquivo legado SEM a coluna Fonte (header pré-merge)
    hist.write_text(
        "﻿Ativo,Sentimento,Score,Resumo,Data,price_usd,Juiz,Divergencia\r\n"
        "BITCOIN,negativo,25.0,resumo,2026-06-30 02:35:23,59296.8,gemini:x:y,0\r\n",
        encoding="utf-8",
    )
    # 2) nova previsão carimbada
    history.append_history([{
        "ativo": "solana", "sentimento": "positivo", "score": 85.0, "resumo": "r",
        "data": "2026-07-01 23:02:31", "price_usd": 150.0, "judge": "gemini:x:y",
        "divergencia": 0, "data_source": "dpl:fallback",
    }])

    import csv
    rows = list(csv.DictReader(open(hist, newline="", encoding="utf-8-sig")))
    assert len(rows) == 2
    legada, nova = rows
    # linha legada sobreviveu à migração com Fonte vazia (backtest lê como 'direct')
    assert legada["Ativo"] == "BITCOIN" and legada["Fonte"] == ""
    assert (legada["Fonte"] or "direct") == "direct"
    # linha nova nasce carimbada
    assert nova["Ativo"] == "SOLANA" and nova["Fonte"] == "dpl:fallback"
