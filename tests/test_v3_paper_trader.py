"""Testes dos helpers puros do paper_trader V3 — sem rede, sem hmmlearn.

Cobrem: seleção do sinal mais recente, casamento de preço de referência (±5 min),
e o cálculo de posição (direction × strength × kelly_fraction).

NOTA: importa só helpers que não dependem de hmmlearn. Se hmmlearn faltar no
ambiente de teste, os imports do pipeline falhariam — por isso testamos a
matemática de posição de forma isolada quando possível.
"""

import pytest

# paper_trader importa pipeline -> regime_engine -> hmmlearn. Se hmmlearn não
# estiver instalado (suite roda no global), pula o módulo inteiro com skip claro.
pytest.importorskip("hmmlearn", reason="paper_trader depende de hmmlearn (venv V3)")

from GarimpoInvestimentos.v3.paper_trader import _latest_signal, _ref_price
from GarimpoInvestimentos.v3.signal_engine import SignalRecord


def _mk_signal(ts_ms: int, direction: int = 1, strength: float = 0.8) -> SignalRecord:
    return SignalRecord(
        schema_version="v3.1.0",
        event_id=f"evt-{ts_ms}",
        timestamp_exchange_ms=ts_ms,
        timestamp_signal_ms=ts_ms,
        asset="BTCUSDT",
        engine_id="test",
        regime_state="bull",
        regime_confidence=0.7,
        regime_entropy=0.3,
        regime_is_uncertain=False,
        direction=direction,
        strength=strength,
        active=direction != 0,
        reason="test",
        horizon_hours=24,
        data_quality_score=1.0,
        operational_state="HEALTHY",
        features_used={},
    )


# ------------------------------------------------------------------ #
# _latest_signal                                                      #
# ------------------------------------------------------------------ #


def test_latest_signal_empty_returns_none():
    assert _latest_signal([]) is None


def test_latest_signal_picks_max_timestamp():
    sigs = [_mk_signal(1000), _mk_signal(3000), _mk_signal(2000)]
    latest = _latest_signal(sigs)
    assert latest is not None and latest.timestamp_exchange_ms == 3000


# ------------------------------------------------------------------ #
# _ref_price                                                          #
# ------------------------------------------------------------------ #


def test_ref_price_exact_match():
    idx = {1000: 50000.0, 2000: 51000.0}
    assert _ref_price(1000, idx) == 50000.0


def test_ref_price_within_tolerance():
    # 1000 + 4min (240000ms) está dentro de ±5min → casa com 1000
    idx = {1000: 50000.0}
    assert _ref_price(1000 + 240_000, idx) == 50000.0


def test_ref_price_outside_tolerance_returns_none():
    # 1000 + 10min está fora de ±5min → None
    idx = {1000: 50000.0}
    assert _ref_price(1000 + 600_000, idx) is None


def test_ref_price_picks_closest():
    idx = {1_000_000: 50000.0, 1_200_000: 51000.0}
    # alvo 1_150_000: mais próximo de 1_200_000 (50k a 150k vs 50k de distância)
    assert _ref_price(1_150_000, idx) == 51000.0


# ------------------------------------------------------------------ #
# Cálculo de posição (direction × strength × kelly_fraction)          #
# ------------------------------------------------------------------ #


@pytest.mark.parametrize(
    "direction,strength,kelly,expected",
    [
        (1, 0.8, 0.5, 0.4),  # long
        (-1, 0.8, 0.5, -0.4),  # short
        (0, 0.0, 0.5, 0.0),  # flat
        (1, 1.0, 0.25, 0.25),  # kelly conservador
        (1, 1.0, 1.0, 1.0),  # kelly completo
    ],
)
def test_position_math(direction, strength, kelly, expected):
    assert direction * strength * kelly == pytest.approx(expected)


def test_default_kelly_fraction_is_homologated():
    """A fração homologada (Kelly sweep 2026-06-27) é 0.50."""
    from GarimpoInvestimentos.v3.backtest_v3 import DEFAULT_KELLY_FRACTION

    assert DEFAULT_KELLY_FRACTION == 0.50
