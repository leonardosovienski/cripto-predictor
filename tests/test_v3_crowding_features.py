"""H9 (OI/volume, docs/HYPOTHESES.md): testa build_oi_volume_ratio isoladamente —
mecanismo puro, sem rede, sem I/O."""

import math

import pytest

from GarimpoInvestimentos.v3.crowding_features import build_oi_volume_ratio
from GarimpoInvestimentos.v3.feature_builder import FeatureVector


def _fv(ts_ms: int, oi_notional_usd: float, spot_close: float) -> FeatureVector:
    return FeatureVector(
        timestamp_exchange_ms=ts_ms,
        asset="BTCUSDT",
        funding_rate_raw=0.0001,
        oi_notional_usd=oi_notional_usd,
        spot_close=spot_close,
        funding_zscore=0.0,
        oi_log_delta=0.0,
        leverage_pressure=0.0,
        log_return_8h=0.0,
        realized_vol_24h=0.01,
        data_quality_score=1.0,
    )


def test_razao_basica_log_oi_sobre_volume_notional():
    fv = _fv(1_000_000, oi_notional_usd=1_000_000.0, spot_close=100.0)
    # volume=5_000 unidades base * close=100 = 500_000 USD notional
    volume_index = {1_000_000: 5_000.0}
    out = build_oi_volume_ratio([fv], volume_index)
    assert out == pytest.approx([math.log(1_000_000.0 / 500_000.0)])


def test_sem_volume_alinhado_retorna_zero_neutro():
    fv = _fv(1_000_000, oi_notional_usd=1_000_000.0, spot_close=100.0)
    out = build_oi_volume_ratio([fv], volume_index={})
    assert out == [0.0]


def test_volume_zero_ou_negativo_retorna_zero_neutro():
    fv = _fv(1_000_000, oi_notional_usd=1_000_000.0, spot_close=100.0)
    out = build_oi_volume_ratio([fv], volume_index={1_000_000: 0.0})
    assert out == [0.0]


def test_oi_zero_retorna_zero_neutro():
    fv = _fv(1_000_000, oi_notional_usd=0.0, spot_close=100.0)
    out = build_oi_volume_ratio([fv], volume_index={1_000_000: 5_000.0})
    assert out == [0.0]


def test_usa_valor_mais_recente_dentro_da_tolerancia_nunca_futuro():
    fv = _fv(1_000_000, oi_notional_usd=1_000_000.0, spot_close=100.0)
    # volume 1min antes (dentro da tolerância default 5min) deve ser usado;
    # um valor FUTURO (ts maior que o ponto) nunca deve ser escolhido.
    volume_index = {
        1_000_000 - 60_000: 5_000.0,  # passado, dentro da tolerância
        1_000_000 + 60_000: 99_999.0,  # futuro — nunca deveria ser usado
    }
    out = build_oi_volume_ratio([fv], volume_index)
    assert out == pytest.approx([math.log(1_000_000.0 / 500_000.0)])


def test_fora_da_tolerancia_retorna_zero_neutro():
    fv = _fv(1_000_000, oi_notional_usd=1_000_000.0, spot_close=100.0)
    volume_index = {
        1_000_000 - 10 * 60_000: 5_000.0
    }  # 10min atrás, fora da tolerância default 5min
    out = build_oi_volume_ratio([fv], volume_index)
    assert out == [0.0]


def test_join_tolerance_ms_negativo_levanta_erro():
    with pytest.raises(ValueError):
        build_oi_volume_ratio([], {}, join_tolerance_ms=-1)


def test_multiplos_pontos_preserva_ordem():
    fvs = [
        _fv(1_000_000, oi_notional_usd=2_000_000.0, spot_close=50.0),
        _fv(2_000_000, oi_notional_usd=1_000_000.0, spot_close=100.0),
    ]
    volume_index = {1_000_000: 10_000.0, 2_000_000: 5_000.0}
    out = build_oi_volume_ratio(fvs, volume_index)
    assert out == pytest.approx(
        [
            math.log(2_000_000.0 / (10_000.0 * 50.0)),
            math.log(1_000_000.0 / (5_000.0 * 100.0)),
        ]
    )
