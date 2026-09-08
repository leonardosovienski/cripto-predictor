"""Cobertura do gerador de sinal do V3 (signal_engine.generate_signal).

Trava a árvore de decisão: gating de qualidade/regime tem prioridade sobre as
condições de sinal; short/long só disparam no regime certo; strength = intensidade
× confiança do regime. (Red Team jun/2026 — antes nenhum teste tocava v3/.)
"""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from GarimpoInvestimentos.v3.signal_engine import generate_signal

if TYPE_CHECKING:
    from GarimpoInvestimentos.v3.feature_builder import FeatureVector
    from GarimpoInvestimentos.v3.regime_engine import RegimeOutput


def _fv(*, quality=1.0, fr_z=0.0, oi_d=0.0, exch_ms=1_700_000_000_000) -> "FeatureVector":
    """Stub do FeatureVector — só os atributos que generate_signal lê."""
    return cast(
        "FeatureVector",
        SimpleNamespace(
            data_quality_score=quality,
            funding_zscore=fr_z,
            oi_log_delta=oi_d,
            timestamp_exchange_ms=exch_ms,
            asset="BTCUSDT",
            funding_rate_raw=0.0001,
            leverage_pressure=0.0,
            log_return_8h=0.0,
            realized_vol_24h=0.01,
        ),
    )


def _regime(*, label="bull", conf=0.9, uncertain=False, state=0, entropy=0.2) -> "RegimeOutput":
    """Stub do RegimeOutput. hmm_posterior[state] = conf (confiança do estado)."""
    posterior = [0.0, 0.0, 0.0]
    posterior[state] = conf
    return cast(
        "RegimeOutput",
        SimpleNamespace(
            hmm_state=state,
            hmm_state_label=label,
            hmm_posterior=posterior,
            hmm_entropy=entropy,
            is_uncertain=uncertain,
        ),
    )


# ----------------------------------------------------- gating (prioridade)
def test_dados_degradados_forcam_flat_critical():
    s = generate_signal(_fv(quality=0.4, fr_z=3.0, oi_d=1.0), _regime())
    assert s.direction == 0 and s.active is False
    assert s.reason == "data_degraded" and s.operational_state == "CRITICAL"


def test_regime_incerto_forca_flat_degraded():
    s = generate_signal(_fv(fr_z=3.0, oi_d=1.0), _regime(uncertain=True))
    assert s.active is False and s.reason == "regime_uncertain"
    assert s.operational_state == "DEGRADED"


def test_baixa_confianca_de_regime_forca_flat():
    s = generate_signal(_fv(fr_z=3.0, oi_d=1.0), _regime(conf=0.55))  # < 0.60
    assert s.active is False and s.reason == "regime_low_confidence"


# ----------------------------------------------------- condições de sinal
def test_short_quando_longs_overcrowded_em_bull():
    s = generate_signal(_fv(fr_z=3.0, oi_d=1.0), _regime(label="bull", conf=0.8))
    assert s.direction == -1 and s.active is True
    assert s.reason == "long_squeeze_risk"


def test_long_quando_shorts_overcrowded_em_bear():
    s = generate_signal(_fv(fr_z=-3.0, oi_d=1.0), _regime(label="bear", conf=0.8))
    assert s.direction == +1 and s.active is True
    assert s.reason == "short_squeeze_risk"


def test_sem_condicao_vira_flat_healthy():
    s = generate_signal(_fv(fr_z=0.5, oi_d=1.0), _regime(label="bull", conf=0.9))
    assert s.direction == 0 and s.reason == "no_signal"
    assert s.operational_state == "HEALTHY"


def test_regime_errado_bloqueia_o_sinal():
    # condição SHORT satisfeita (fr_z alto, oi>0), mas regime 'bear' não permite short
    s = generate_signal(_fv(fr_z=3.0, oi_d=1.0), _regime(label="bear", conf=0.9))
    assert s.direction == 0 and s.reason == "no_signal"


def test_oi_caindo_bloqueia_o_sinal():
    # funding extremo mas OI encolhendo (oi_d<=0) → não há posição crescendo
    s = generate_signal(_fv(fr_z=3.0, oi_d=-0.1), _regime(label="bull", conf=0.9))
    assert s.direction == 0 and s.reason == "no_signal"


# ----------------------------------------------------- strength e contrato
def test_strength_e_intensidade_vezes_confianca():
    # |fr_z|/FR_ZSCORE_MAX(=4) = 4/4 = 1.0 ; × conf 0.8 = 0.8
    s = generate_signal(_fv(fr_z=4.0, oi_d=1.0), _regime(label="bull", conf=0.8))
    assert s.strength == 0.8


def test_strength_clipa_em_um():
    # fr_z=12 → intensidade clipada a 1.0 ; × conf 1.0 = 1.0 (não estoura)
    s = generate_signal(_fv(fr_z=12.0, oi_d=1.0), _regime(label="bull", conf=1.0))
    assert s.strength == 1.0


def test_anti_lookahead_signal_ts_nao_precede_exchange_ts():
    # o sinal é gerado DEPOIS do funding que o originou (contrato forward-only)
    s = generate_signal(
        _fv(fr_z=3.0, oi_d=1.0, exch_ms=1_600_000_000_000), _regime(label="bull", conf=0.8)
    )
    assert s.timestamp_signal_ms >= s.timestamp_exchange_ms


# ----------------------------------------------------- thresholds calibráveis (grid-search WFA)
def test_threshold_default_preserva_comportamento_original():
    # fr_z=2.5 dispara com o default (2.0) e continua disparando sem overrides
    s = generate_signal(_fv(fr_z=2.5, oi_d=1.0), _regime(label="bull", conf=0.8))
    assert s.active is True and s.direction == -1


def test_threshold_mais_alto_bloqueia_sinal_que_antes_disparava():
    s = generate_signal(
        _fv(fr_z=2.5, oi_d=1.0),
        _regime(label="bull", conf=0.8),
        fr_zscore_threshold=3.0,
    )
    assert s.active is False and s.reason == "no_signal"


def test_threshold_mais_baixo_dispara_sinal_que_antes_nao_disparava():
    s = generate_signal(
        _fv(fr_z=1.5, oi_d=1.0),
        _regime(label="bull", conf=0.8),
        fr_zscore_threshold=1.0,
    )
    assert s.active is True and s.direction == -1


def test_min_regime_confidence_override_bloqueia_sinal_antes_valido():
    # conf=0.65 passa no default (0.60) mas não num override mais exigente
    s = generate_signal(
        _fv(fr_z=3.0, oi_d=1.0),
        _regime(label="bull", conf=0.65),
        min_regime_confidence=0.70,
    )
    assert s.active is False and s.reason == "regime_low_confidence"


def test_min_regime_confidence_override_libera_sinal_antes_bloqueado():
    # conf=0.55 falha no default (0.60) mas passa com override mais permissivo
    s = generate_signal(
        _fv(fr_z=3.0, oi_d=1.0),
        _regime(label="bull", conf=0.55),
        min_regime_confidence=0.50,
    )
    assert s.active is True and s.direction == -1
