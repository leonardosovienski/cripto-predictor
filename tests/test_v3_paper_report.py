"""Testes do paper_report V3 — helpers puros + agregação de contagens.

paper_report NÃO depende de hmmlearn (só de predictor_core.stats + spot_collector
+ feature_builder, todos puros), então roda no ambiente global.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from GarimpoInvestimentos.v3 import paper_report as pr


def _mk_trade(
    ts_ms, direction=0, position=0.0, ref_price=50000.0, regime="sideways", reason="no_signal"
):
    return {
        "symbol": "BTCUSDT",
        "timestamp_exchange_ms": ts_ms,
        "signal_ts_utc": "2026-06-27T00:00:00+00:00",
        "direction": direction,
        "strength": abs(position) * 2 if position else 0.0,
        "kelly_fraction": 0.5,
        "position": position,
        "ref_price": ref_price,
        "regime_state": regime,
        "regime_confidence": 0.7,
        "reason": reason,
        "horizon_hours": 24 if direction else 0,
        "engine_id": "test",
        "active": direction != 0,
        "event_id": f"evt-{ts_ms}",
    }


def _write_paper(path, trades):
    with open(path, "w", encoding="utf-8") as f:
        for t in trades:
            f.write(json.dumps(t) + "\n")


# ------------------------------------------------------------------ #
# _equity_curve                                                       #
# ------------------------------------------------------------------ #


def test_equity_curve_compounds():
    eq = pr._equity_curve([0.1, -0.05, 0.2])
    assert eq[0] == 1.1
    assert abs(eq[1] - 1.1 * 0.95) < 1e-9
    assert abs(eq[2] - 1.1 * 0.95 * 1.2) < 1e-9


def test_equity_curve_empty():
    assert pr._equity_curve([]) == []


# ------------------------------------------------------------------ #
# _closest_price                                                      #
# ------------------------------------------------------------------ #


def test_closest_price_exact():
    assert pr._closest_price(1000 + 3_600_000, {1000: 42.0}) == 42.0


def test_closest_price_within_tolerance():
    assert pr._closest_price(1000 + 3_600_000 + 200_000, {1000: 42.0}) == 42.0


def test_closest_price_outside_tolerance():
    assert pr._closest_price(1000 + 3_600_000 + 999_999, {1000: 42.0}) is None


def test_closest_price_rejects_future_candle():
    idx = {1_000_000: 42.0, 1_200_000: 99.0}
    assert pr._closest_price(1_150_000 + 3_600_000, idx) == 42.0


# ------------------------------------------------------------------ #
# build_report — contagens (sem spot → P&L não computável)            #
# ------------------------------------------------------------------ #


def test_build_report_empty():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(pr, "_PAPER_DIR", Path(tmp)):
            s = pr.build_report("BTCUSDT")
    assert s["n_total"] == 0
    assert s["cum_pnl"] == 0.0


def test_build_report_counts_active_vs_flat():
    with tempfile.TemporaryDirectory() as tmp:
        paper = Path(tmp) / "BTCUSDT_paper.jsonl"
        _write_paper(
            paper,
            [
                _mk_trade(1000, direction=0, position=0.0),
                _mk_trade(2000, direction=1, position=0.4),
                _mk_trade(3000, direction=-1, position=-0.3),
            ],
        )
        # _spot_path aponta para dir sem spot → P&L fica 0, mas contagens valem
        with patch.object(pr, "_PAPER_DIR", Path(tmp)), patch.object(pr, "_DATA_ROOT", Path(tmp)):
            s = pr.build_report("BTCUSDT")
    assert s["n_total"] == 3
    assert s["n_active"] == 2
    assert s["n_flat"] == 1


def test_build_report_computes_pnl_with_spot():
    """Com spot disponível, P&L = position × ln(exit/entry)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sym_dir = root / "BTCUSDT"
        sym_dir.mkdir(parents=True)
        paper_dir = root / "paper"
        paper_dir.mkdir()

        # Trade LONG em t=0 (preço 100), horizonte 24h → preço 110 (subiu 10%)
        entry_ms = 1_000_000_000_000
        exit_ms = entry_ms + 24 * 3_600_000
        _write_paper(
            paper_dir / "BTCUSDT_paper.jsonl",
            [
                _mk_trade(entry_ms, direction=1, position=1.0, ref_price=100.0),
            ],
        )

        # O indice usa open-time; o close de saida abre 1h antes de ficar publico.
        fake_spot = {entry_ms - 3_600_000: 100.0, exit_ms - 3_600_000: 110.0}

        with (
            patch.object(pr, "_PAPER_DIR", paper_dir),
            patch.object(pr, "_DATA_ROOT", root),
            patch.object(pr, "load_spot_csv", return_value=[]),
            patch.object(pr, "build_spot_index", return_value=fake_spot),
            patch("pathlib.Path.exists", return_value=True),
        ):
            s = pr.build_report("BTCUSDT", horizon_hours=24)

    assert s["n_mature"] == 1
    # position=1.0, ln(110/100) ≈ 0.0953
    assert abs(s["cum_pnl"] - 0.09531) < 1e-3
    assert s["hit_rate"] == 1.0
