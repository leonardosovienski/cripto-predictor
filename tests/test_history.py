"""Testes de history.py — dedup, header migration, campos aditivos.

Todos os testes rodam sem rede e sem .env real (conftest injeta credenciais mínimas).
"""
import csv
import os
import tempfile
from unittest.mock import patch

import GarimpoInvestimentos.store.history as history_mod


_FIELDNAMES = ["Ativo", "Sentimento", "Score", "Resumo", "Data", "price_usd", "Juiz", "Divergencia"]


def _make_resultado(ativo="bitcoin", score=75, data="2026-06-27 10:00:00"):
    return {
        "ativo": ativo,
        "sentimento": "positivo",
        "score": score,
        "resumo": "teste",
        "data": data,
        "price_usd": 65000.0,
        "judge": "gemini:gemini-2.5-flash:abc123",
        "divergencia": 0,
    }


def _write_csv(path: str, rows: list, fieldnames=None) -> None:
    fn = fieldnames or _FIELDNAMES
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fn)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_csv(path: str) -> list:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ #
# Testes                                                              #
# ------------------------------------------------------------------ #

def test_append_history_creates_file_with_header():
    """Quando não existe histórico, cria o arquivo com o header correto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = os.path.join(tmpdir, "garimpo_historico.csv")
        with patch.object(history_mod, "HIST_CSV", hist_path):
            history_mod.append_history([_make_resultado()])
        rows = _read_csv(hist_path)
    assert len(rows) == 1
    assert rows[0]["Ativo"] == "BITCOIN"
    assert rows[0]["Score"] == "75"


def test_append_history_dedup_same_ativo_data():
    """Duas chamadas com mesmo (Ativo, Data) não devem duplicar a linha."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = os.path.join(tmpdir, "garimpo_historico.csv")
        r = _make_resultado()
        with patch.object(history_mod, "HIST_CSV", hist_path):
            history_mod.append_history([r])
            history_mod.append_history([r])
        rows = _read_csv(hist_path)
    assert len(rows) == 1


def test_append_history_different_assets_both_written():
    """Ativos distintos devem ser escritos normalmente."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = os.path.join(tmpdir, "garimpo_historico.csv")
        with patch.object(history_mod, "HIST_CSV", hist_path):
            history_mod.append_history([
                _make_resultado("bitcoin"),
                _make_resultado("ethereum"),
            ])
        rows = _read_csv(hist_path)
    assert len(rows) == 2
    ativos = {r["Ativo"] for r in rows}
    assert ativos == {"BITCOIN", "ETHEREUM"}


def test_append_history_same_asset_different_dates():
    """Mesmo ativo em datas distintas deve gerar duas linhas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = os.path.join(tmpdir, "garimpo_historico.csv")
        with patch.object(history_mod, "HIST_CSV", hist_path):
            history_mod.append_history([
                _make_resultado("bitcoin", data="2026-06-27 10:00:00"),
                _make_resultado("bitcoin", data="2026-06-28 10:00:00"),
            ])
        rows = _read_csv(hist_path)
    assert len(rows) == 2


def test_ensure_header_migrates_old_csv():
    """Histórico com header antigo deve ser migrado sem perder dados."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = os.path.join(tmpdir, "garimpo_historico.csv")
        old_fieldnames = ["Ativo", "Sentimento", "Score", "Resumo", "Data"]
        _write_csv(hist_path, [
            {"Ativo": "BITCOIN", "Sentimento": "positivo", "Score": "80",
             "Resumo": "antigo", "Data": "2026-01-01 00:00:00"},
        ], fieldnames=old_fieldnames)
        with patch.object(history_mod, "HIST_CSV", hist_path):
            history_mod._ensure_header()
        rows = _read_csv(hist_path)
    assert len(rows) == 1
    assert rows[0]["Ativo"] == "BITCOIN"
    assert rows[0]["Score"] == "80"
    assert rows[0].get("Juiz", "") == ""


def test_divergencia_field_written_correctly():
    """Flag de divergência deve ser preservada como '1'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_path = os.path.join(tmpdir, "garimpo_historico.csv")
        r = _make_resultado()
        r["divergencia"] = 1
        with patch.object(history_mod, "HIST_CSV", hist_path):
            history_mod.append_history([r])
        rows = _read_csv(hist_path)
    assert rows[0]["Divergencia"] == "1"
