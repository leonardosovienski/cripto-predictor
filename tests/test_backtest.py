"""Testes de analyzers/backtest.py — leitura do histórico, Spearman, métricas.

Todos os testes rodam sem rede (sem chamadas ao CoinGecko).
"""
import csv
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import GarimpoInvestimentos.analyzers.backtest as bt_mod


_HIST_FIELDNAMES = ["Ativo", "Sentimento", "Score", "Resumo", "Data", "price_usd", "Juiz", "Divergencia"]
_FALLBACK_MARKER = "fallback aplicado"


def _write_hist(path, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_HIST_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _row(ativo="bitcoin", score=80, data="2026-01-01 00:00:00",
         price=50000.0, resumo="ok", divergencia=0):
    return {
        "Ativo": ativo.upper(),
        "Sentimento": "positivo",
        "Score": str(score),
        "Resumo": resumo,
        "Data": data,
        "price_usd": str(price),
        "Juiz": "gemini:gemini-2.5-flash:abc",
        "Divergencia": str(divergencia),
    }


# ------------------------------------------------------------------ #
# _load_rows                                                           #
# ------------------------------------------------------------------ #

def test_load_rows_empty_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = Path(tmpdir) / "garimpo_historico.csv"
        with patch.object(bt_mod, "HIST_CSV", hist_path):
            rows = bt_mod._load_rows()
    assert rows == []


def test_load_rows_excludes_fallback():
    """Linhas com marker de fallback não devem entrar no backtest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = Path(tmpdir) / "garimpo_historico.csv"
        _write_hist(str(hist_path), [
            _row(resumo=_FALLBACK_MARKER),
            _row(score=70, resumo="analise real"),
        ])
        with patch.object(bt_mod, "HIST_CSV", hist_path):
            rows = bt_mod._load_rows()
    assert len(rows) == 1
    assert rows[0]["score"] == 70.0


def test_load_rows_dedup_same_ativo_data():
    """Duplicatas (Ativo, Data) devem ser deduplicadas defensivamente."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = Path(tmpdir) / "garimpo_historico.csv"
        _write_hist(str(hist_path), [
            _row("bitcoin", score=80, data="2026-01-01 00:00:00"),
            _row("bitcoin", score=80, data="2026-01-01 00:00:00"),
        ])
        with patch.object(bt_mod, "HIST_CSV", hist_path):
            rows = bt_mod._load_rows()
    assert len(rows) == 1


def test_load_rows_excludes_zero_price():
    """Linha com price_usd=0 deve ser descartada; linha válida preservada."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = Path(tmpdir) / "garimpo_historico.csv"
        _write_hist(str(hist_path), [
            _row(price=0.0, data="2026-01-01 00:00:00"),
            _row(price=50000.0, score=65, data="2026-01-02 00:00:00"),
        ])
        with patch.object(bt_mod, "HIST_CSV", hist_path):
            rows = bt_mod._load_rows()
    assert len(rows) == 1
    assert rows[0]["score"] == 65.0


def test_load_rows_preserves_divergencia_flag():
    """Flag de divergência deve ser lida como int 0 ou 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = Path(tmpdir) / "garimpo_historico.csv"
        _write_hist(str(hist_path), [
            _row(divergencia=1),
            _row(score=60, data="2026-01-02 00:00:00", divergencia=0),
        ])
        with patch.object(bt_mod, "HIST_CSV", hist_path):
            rows = bt_mod._load_rows()
    divs = {r["divergencia"] for r in rows}
    assert 0 in divs
    assert 1 in divs


# ------------------------------------------------------------------ #
# _report: Spearman IC (usa predictor_core.stats — sem rede)         #
# ------------------------------------------------------------------ #

def test_report_insufficient_data_prints_message(capsys):
    """Com < 4 pontos, _report deve imprimir 'dados insuficientes'."""
    enriched = [
        {"score": 80, "var_d7_pct": 5.0, "divergencia": 0},
        {"score": 60, "var_d7_pct": -2.0, "divergencia": 0},
    ]
    with patch.object(bt_mod, "PRIMARY_HORIZON", 7), \
         patch.object(bt_mod, "HORIZONS", [7]):
        bt_mod._report(enriched)
    out = capsys.readouterr().out
    assert "insuficiente" in out.lower()


def test_report_with_enough_data_shows_spearman(capsys):
    """Com n >= 4, _report deve exibir o valor de Spearman."""
    enriched = [
        {"score": 90, "var_d7_pct": 10.0, "divergencia": 0},
        {"score": 70, "var_d7_pct": 5.0,  "divergencia": 0},
        {"score": 50, "var_d7_pct": 0.0,  "divergencia": 1},
        {"score": 30, "var_d7_pct": -5.0, "divergencia": 0},
        {"score": 10, "var_d7_pct": -10.0,"divergencia": 1},
    ]
    with patch.object(bt_mod, "PRIMARY_HORIZON", 7), \
         patch.object(bt_mod, "HORIZONS", [7]), \
         patch.object(bt_mod, "emit_event", return_value=None):
        bt_mod._report(enriched)
    out = capsys.readouterr().out
    assert "Spearman" in out


# ------------------------------------------------------------------ #
# _metrics                                                            #
# ------------------------------------------------------------------ #

def test_metrics_insufficient_data(capsys):
    """Com menos de 3 pontos maduros, deve informar 'dados insuficientes'."""
    enriched = [
        {"score": 80, "var_d7_pct": 5.0, "divergencia": 0, "ativo": "bitcoin"},
    ]
    bt_mod._metrics(enriched, 7)
    out = capsys.readouterr().out
    assert "insuficiente" in out.lower()


def test_metrics_directional_accuracy(capsys):
    """4 de 4 previsões corretas → acurácia direcional 100%."""
    enriched = [
        {"score": 80, "var_d7_pct": 5.0,  "ativo": "bitcoin",  "divergencia": 0},
        {"score": 75, "var_d7_pct": 3.0,  "ativo": "bitcoin",  "divergencia": 0},
        {"score": 30, "var_d7_pct": -4.0, "ativo": "ethereum", "divergencia": 0},
        {"score": 25, "var_d7_pct": -2.0, "ativo": "ethereum", "divergencia": 1},
    ]
    bt_mod._metrics(enriched, 7)
    out = capsys.readouterr().out
    assert "100.0%" in out


def test_metrics_hit_rate_above_threshold(capsys):
    """Hit rate dos sinais fortes (score >= 60): 2/3 positivos → ~66.7%."""
    enriched = [
        {"score": 80, "var_d7_pct": 5.0,  "ativo": "bitcoin",  "divergencia": 0},
        {"score": 70, "var_d7_pct": 3.0,  "ativo": "bitcoin",  "divergencia": 0},
        {"score": 65, "var_d7_pct": -2.0, "ativo": "ethereum", "divergencia": 0},
        {"score": 40, "var_d7_pct": -1.0, "ativo": "solana",   "divergencia": 0},
    ]
    bt_mod._metrics(enriched, 7)
    out = capsys.readouterr().out
    # 2 de 3 sinais fortes positivos = 66.7%
    assert "66.7%" in out or "2/3" in out
