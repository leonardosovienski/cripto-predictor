"""H7 (macro/DXY): integração ponta-a-ponta de --use-macro-dxy através de
run_wfa — prova que a fiação (CLI → covariáveis → RegimeEngine) funciona sobre
dado sintético gravado em disco, não só as peças isoladas (já cobertas em
test_v3_regime_engine_extra_covariates.py e test_v3_macro_features.py).

Usa o calendário macro REAL do projeto (macro_calendar.json) — só o CSV de DXY é
sintético (escrito no tmp_path do teste, sem rede).
"""

import csv
from datetime import UTC, datetime

import pytest

pytest.importorskip("hmmlearn")
pytest.importorskip("sklearn")

from GarimpoInvestimentos.v3 import backtest_v3

_MS_PER_HOUR = 3_600_000
_MS_PER_8H = 8 * _MS_PER_HOUR
_TOTAL_DAYS = 230  # > _IS_DAYS(180) + _PURGE_DAYS(7) + _OOS_DAYS(30) = 217


def _write_synthetic_data(data_root, symbol="BTCUSDT"):
    sym_dir = data_root / symbol
    sym_dir.mkdir(parents=True)

    start_ms = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() * 1000)
    n_periods = (_TOTAL_DAYS * 24_000) // 8_000  # nº de janelas de 8h

    # Funding + spot com leve tendência senoidal — só precisa ser numericamente
    # válido e variado o bastante pro HMM convergir; não testa edge, testa wiring.
    import math

    rng = __import__("random").Random(42)
    with (sym_dir / "funding.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "funding_time_ms", "funding_rate", "mark_price"])
        for i in range(n_periods):
            ts = start_ms + i * _MS_PER_8H
            # Baseline QUIETO (desvio pequeno) + spikes RAROS e grandes. O
            # z-score é sobre janela rolante (fr_window=90): spikes frequentes
            # viram parte da "normalidade" e nunca cruzam o threshold — só
            # outliers raros contra um baseline calmo produzem |z|>2 de forma
            # confiável. Verificado numericamente antes de fixar esta forma
            # (35 pontos com |z|>2 em 600 feature vectors). Isto testa fiação
            # de código, não modela dinâmica de mercado real.
            spike = 0.02 if i % 17 == 0 else 0.0
            rate = rng.gauss(0, 0.00005) + spike
            price = 30000.0 + 500.0 * math.sin(i / 13.0)
            w.writerow([symbol, ts, f"{rate:.8f}", f"{price:.2f}"])

    with (sym_dir / "oi.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "timestamp_ms", "oi_contracts", "oi_notional_usd"])
        for i in range(n_periods):
            ts = start_ms + i * _MS_PER_8H
            notional = 1_000_000.0 + 50_000.0 * math.sin(i / 11.0)
            w.writerow([symbol, ts, f"{notional / 30000.0:.4f}", f"{notional:.2f}"])

    with (sym_dir / "spot_1h.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "open_ms", "close", "volume"])
        n_hours = _TOTAL_DAYS * 24
        for i in range(n_hours):
            ts = start_ms + i * _MS_PER_HOUR
            price = 30000.0 + 500.0 * math.sin(i / (13.0 * 8))
            w.writerow([symbol, ts, f"{price:.2f}", "100.0"])

    return start_ms


def _write_dxy_csv(path, start_ms):
    """DXY sintético diário cobrindo toda a janela + folga pro publish_lag."""
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "close"])
        start_date = datetime.fromtimestamp(start_ms / 1000, tz=UTC).date()
        import datetime as dt

        for i in range(_TOTAL_DAYS + 5):
            d = start_date + dt.timedelta(days=i)
            close = 100.0 + 0.3 * (i % 17)
            w.writerow([d.isoformat(), f"{close:.4f}"])


@pytest.fixture
def synthetic_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data_v3"
    start_ms = _write_synthetic_data(data_root)
    monkeypatch.setattr(backtest_v3, "_DATA_ROOT", data_root)
    return data_root, start_ms


# Thresholds do sinal deliberadamente baixos: o que este arquivo testa é a
# FIAÇÃO (CLI/parâmetros → covariáveis → RegimeEngine → folds completados),
# não se o sinal sintético é realista. Thresholds de produção continuam sendo
# os defaults do signal_engine — não mudamos nada lá.
_LOW_FR_THRESHOLD = 0.1
_LOW_REGIME_CONFIDENCE = 0.0


def test_use_macro_dxy_false_comportamento_inalterado(synthetic_data_root):
    """Regressão: sem a flag, resultado idêntico ao caminho de sempre (roda sem
    erro, folds >= 1)."""
    _, _ = synthetic_data_root
    result = backtest_v3.run_wfa(
        symbol="BTCUSDT",
        fr_zscore_threshold=_LOW_FR_THRESHOLD,
        min_regime_confidence=_LOW_REGIME_CONFIDENCE,
    )
    assert result.n_folds >= 1


def test_use_macro_dxy_true_roda_ponta_a_ponta(synthetic_data_root, tmp_path):
    data_root, start_ms = synthetic_data_root
    dxy_path = tmp_path / "dxy.csv"
    _write_dxy_csv(dxy_path, start_ms)

    result = backtest_v3.run_wfa(
        symbol="BTCUSDT",
        use_macro_dxy=True,
        dxy_closes_path=dxy_path,
        fr_zscore_threshold=_LOW_FR_THRESHOLD,
        min_regime_confidence=_LOW_REGIME_CONFIDENCE,
    )
    assert result.n_folds >= 1
    assert result.final_verdict in ("GO", "NO-GO")


def test_use_macro_dxy_sem_dxy_closes_path_e_erro(synthetic_data_root):
    with pytest.raises(ValueError, match="dxy_closes_path"):
        backtest_v3.run_wfa(symbol="BTCUSDT", use_macro_dxy=True)
