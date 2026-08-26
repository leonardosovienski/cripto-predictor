"""O diagnóstico exploratório da H6 também deve obedecer point-in-time."""

from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from scripts.diagnose_h6_mechanism import load_mechanism_rows


def _point(symbol, ts, close, published_at):
    return MarketDataPoint(
        symbol=symbol,
        timestamp=ts,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000.0,
        source="binance",
        interval="1d",
        published_at=published_at,
    )


def test_replay_descarta_feature_publicada_depois_da_previsao(tmp_path):
    pred_at = datetime(2026, 2, 10, tzinfo=UTC)
    horizon = 7
    db = tmp_path / "feature_store.db"
    with FeatureStore(db) as store:
        store.write_raw(
            [
                _point(
                    "bitcoin",
                    pred_at - timedelta(days=horizon),
                    90.0,
                    pred_at + timedelta(days=1),
                ),
                _point(
                    "bitcoin",
                    pred_at + timedelta(days=horizon),
                    110.0,
                    pred_at + timedelta(days=horizon),
                ),
            ]
        )
        rows = load_mechanism_rows(
            store,
            [{"ativo": "bitcoin", "ts": "2026-02-10 00:00:00", "score": 70.0, "price_usd": 100.0}],
            horizon_days=horizon,
        )

    assert rows == [], "feature indisponível na época vazou para o replay"


def test_replay_mantem_feature_disponivel_e_desfecho_posterior(tmp_path):
    pred_at = datetime(2026, 2, 10, tzinfo=UTC)
    horizon = 7
    db = tmp_path / "feature_store.db"
    with FeatureStore(db) as store:
        store.write_raw(
            [
                _point(
                    "bitcoin",
                    pred_at - timedelta(days=horizon),
                    80.0,
                    pred_at - timedelta(days=horizon),
                ),
                _point(
                    "bitcoin",
                    pred_at + timedelta(days=horizon),
                    110.0,
                    pred_at + timedelta(days=horizon),
                ),
            ]
        )
        rows = load_mechanism_rows(
            store,
            [{"ativo": "BITCOIN", "ts": "2026-02-10 00:00:00", "score": 70.0, "price_usd": 100.0}],
            horizon_days=horizon,
        )

    assert len(rows) == 1
    assert rows[0]["score"] == 70.0
    assert rows[0]["past_ret_pct"] == pytest.approx(25.0)
    assert rows[0]["fut_ret_pct"] == pytest.approx(10.0)
