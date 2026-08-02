"""Regressão C4 (auditoria 2026-07-09): o paper_trader appendava sempre —
re-execução no mesmo dia gravava o MESMO sinal (timestamp_exchange_ms igual)
duas vezes, e o paper_report não deduplica: o trade contava dobrado no P&L
dos 30 dias de produção assistida. A guarda _already_recorded fecha isso.
"""

import json
from unittest import mock

from GarimpoInvestimentos.v3 import paper_trader


def _write_paper(path, ts_list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ts in ts_list:
            f.write(json.dumps({"symbol": "BTCUSDT", "timestamp_exchange_ms": ts}) + "\n")


def test_already_recorded_detects_existing_timestamp(tmp_path):
    p = tmp_path / "BTCUSDT_paper.jsonl"
    _write_paper(p, [1000, 2000])
    with mock.patch.object(paper_trader, "_paper_path", return_value=p):
        assert paper_trader._already_recorded("BTCUSDT", 2000) is True
        assert paper_trader._already_recorded("BTCUSDT", 3000) is False


def test_already_recorded_without_file(tmp_path):
    p = tmp_path / "BTCUSDT_paper.jsonl"
    with mock.patch.object(paper_trader, "_paper_path", return_value=p):
        assert paper_trader._already_recorded("BTCUSDT", 1000) is False


def test_already_recorded_ignores_corrupt_lines(tmp_path):
    p = tmp_path / "BTCUSDT_paper.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"timestamp_exchange_ms": 500}\nnão-é-json\n\n', encoding="utf-8")
    with mock.patch.object(paper_trader, "_paper_path", return_value=p):
        assert paper_trader._already_recorded("BTCUSDT", 500) is True
        assert paper_trader._already_recorded("BTCUSDT", 999) is False
