"""Redoma do main.run() — o teste de integração que teria pego o bug do close prematuro.

Lição da conferência de 2026-07-02: quatro suítes verdes (329 testes) não pegaram uma
previsão sumindo em silêncio porque NENHUM teste exercitava o run() de ponta a ponta —
o caminho real: parse → serving da Feature Store → análise → carimbos → persistência.
Esta redoma roda o run() VERDADEIRO com as bordas stubbadas (LLM, notícias, exportação
XLSX, rede) e afirma o que importa: a previsão TEM que estar na store ao final, com os
carimbos certos. Se alguém reintroduzir um close prematuro (ou quebrar a ordem do
fluxo), este teste acusa.
"""

import asyncio
import sys
import types
from datetime import UTC, datetime
from unittest import mock

_OPENPYXL_MODS = (
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.formatting",
    "openpyxl.formatting.rule",
    "openpyxl.chart",
    "openpyxl.chart.label",
    "openpyxl.utils",
    "openpyxl.worksheet.worksheet",
)


def test_run_analisa_do_serving_e_persiste_carimbado(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "GEMINIKEY-0123456789-abcdef")
    monkeypatch.setenv("SERP_API_KEY", "SERPKEY-0123456789-abcdef")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("PREDICTOR_EVENTS_PATH", str(tmp_path / "ev.jsonl"))
    monkeypatch.setitem(sys.modules, "httpx", types.ModuleType("httpx"))
    for m in _OPENPYXL_MODS:  # reporter importa no topo; suíte não tem openpyxl
        monkeypatch.setitem(sys.modules, m, mock.MagicMock())

    import GarimpoInvestimentos.main as main
    from GarimpoInvestimentos.core import history
    from GarimpoInvestimentos.dpl import FeatureStore, MarketDataPoint

    # Feature Store semeada como a ingestão deixaria (candle bruto + features servíveis)
    db = tmp_path / "fs.db"
    ts = datetime(2026, 7, 1, tzinfo=UTC)
    with FeatureStore(db) as fs:
        fs.write_raw(
            [
                MarketDataPoint(
                    source="coingecko",
                    symbol="bitcoin",
                    interval="1d",
                    timestamp=ts,
                    open=1.0,
                    high=2.0,
                    low=0.5,
                    close=60000.0,
                    volume=1e9,
                    published_at=ts,
                )
            ]
        )
        fs.write_features(
            "bitcoin", "1d", [{"ts": ts, "price_usd": 60000.0, "close": 60000.0, "rsi_14": 40.0}]
        )

    monkeypatch.setattr(main, "FEATURE_STORE_DB", db)
    monkeypatch.setattr(history, "HIST_CSV", str(tmp_path / "nao_existe.csv"))

    async def fake_analyze(ativo, hard_data, news):
        return {
            "sentiment": "positivo",
            "score": 77,
            "opportunity_score": 77,
            "summary": "análise da redoma",
        }

    from GarimpoInvestimentos.collectors.news import NewsResult

    async def fake_news(ativo):
        return NewsResult([], "stub", "stub_empty")

    monkeypatch.setattr(main, "analyze_asset", fake_analyze)
    monkeypatch.setattr(main, "get_news_result", fake_news)
    monkeypatch.setattr(main, "judge_signature", lambda asset_name=None: "stub:modelo:hash")
    monkeypatch.setattr(main, "export_results", lambda resultados: None)
    monkeypatch.setattr(sys, "argv", ["main", "--assets", "bitcoin", "--no-cache"])

    asyncio.run(main.run())

    # O QUE IMPORTA: a previsão persistiu no histórico oficial, carimbada.
    with FeatureStore(db) as fs:
        preds = fs.read_predictions()
    assert len(preds) == 1, (
        "run() terminou sem persistir a previsão (regressão do close prematuro?)"
    )
    p = preds[0]
    assert p["ativo"] == "BITCOIN"
    assert p["score"] == 77.0
    assert p["fonte"] == "dpl:fallback"  # derivado do source do candle servido
    assert p["juiz"] == "stub:modelo:hash"
