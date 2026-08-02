"""
Signal Engine — Fase 1 do Crypto-Predictor V3.

Responsabilidade: combinar FeatureVector + RegimeOutput em um sinal
direcional (-1 / 0 / +1) com strength [0,1] e produzir o contrato
canônico de sinal (SignalRecord) — gravado como JSONL via predictor_core.obs.

HIPÓTESE TESTADA:
    Edge existe na assimetria de alavancagem forçada:
    → Funding extremo + OI crescendo + regime identificado
      = mercado overcrowded em uma direção → pressão de liquidação forçada

LÓGICA DE SINAL:
    SHORT (direction=-1):
        funding_zscore >= +THRESHOLD   (longs pagando caro pelo carry)
        AND oi_log_delta > 0           (mais longs entrando = posição crescendo)
        AND regime in {"bull", "sideways"}  (não "bear" — lá longs já liquidados)

    LONG (direction=+1):
        funding_zscore <= -THRESHOLD   (shorts pagando caro)
        AND oi_log_delta > 0           (mais shorts entrando)
        AND regime in {"bear", "sideways"}

    FLAT (direction=0):
        qualquer outra condição; regime incerto; dados degradados

STRENGTH [0,1]:
    Proporcional à intensidade do sinal e à confiança do regime.
    strength = clip(|FR_zscore| / FR_ZSCORE_MAX, 0, 1) × P(regime_state)
    Usado diretamente como "score" pelo WFA e PSR no predictor_core.

CONTRATO DE SAÍDA (SignalRecord):
    Serializado como JSONL via predictor_core.obs.emit_event.
    O campo features_used garante rastreabilidade completa ("Por que abriu às 14:32?").
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.v3.feature_builder import FeatureVector
from GarimpoInvestimentos.v3.regime_engine import RegimeOutput

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Parâmetros do sinal (tunar SOMENTE no in-sample do WFA)            #
# ------------------------------------------------------------------ #

_FR_ZSCORE_THRESHOLD = 2.0  # |z| > 2.0 → sinal ativo
_FR_ZSCORE_MAX = 4.0  # normalização do strength
_MIN_DATA_QUALITY = 0.5  # abaixo disso → FLAT obrigatório
_MIN_REGIME_CONFIDENCE = 0.60  # P(estado) < 0.60 → não gera sinal


# ------------------------------------------------------------------ #
# Contrato de sinal                                                   #
# ------------------------------------------------------------------ #


@dataclass
class SignalRecord:
    """
    Contrato canônico de sinal — imutável e auditável.

    timestamp_exchange_ms: timestamp do funding que gerou o sinal.
    engine_id: hash do engine + versão dos parâmetros para reprodutibilidade.
    features_used: vetor exato que gerou o sinal (replay hermético).
    """

    schema_version: str
    event_id: str
    timestamp_exchange_ms: int
    timestamp_signal_ms: int  # quando o sinal foi gerado (≥ exchange_ms)
    asset: str
    engine_id: str

    # Regime
    regime_state: str
    regime_confidence: float  # P(regime_state | x_{0:t})
    regime_entropy: float
    regime_is_uncertain: bool

    # Sinal
    direction: int  # -1 (short) / 0 (flat) / +1 (long)
    strength: float  # [0, 1] — proporcional à convicção
    active: bool  # False = sem sinal / dados degradados
    reason: str  # legível: "long_squeeze_risk" etc.
    horizon_hours: int  # horizonte esperado do edge (8h/24h/48h)

    # Infraestrutura
    data_quality_score: float
    operational_state: str  # "HEALTHY" / "DEGRADED" / "CRITICAL"

    # Auditoria completa
    features_used: dict


_ENGINE_ID = "funding_oi_hmm_v1:phase1"
_SCHEMA_VERSION = "v3.1.0"


# ------------------------------------------------------------------ #
# Gerador de sinal                                                    #
# ------------------------------------------------------------------ #


def generate_signal(
    fv: FeatureVector,
    regime: RegimeOutput,
    horizon_hours: int = 24,
) -> SignalRecord:
    """
    Gera o SignalRecord para um par (FeatureVector, RegimeOutput).

    Regras em ordem de prioridade:
    1. Dados degradados (quality < MIN_DATA_QUALITY) → FLAT / CRITICAL
    2. Regime incerto (entropy > threshold) → FLAT / observação
    3. Regime com baixa confiança → FLAT
    4. Condições de sinal: short ou long se atendidas
    5. Caso contrário → FLAT
    """
    now_ms = int(datetime.now(UTC).timestamp() * 1000)

    # Estado operacional propagado
    if fv.data_quality_score < _MIN_DATA_QUALITY:
        return _flat(
            fv,
            regime,
            now_ms,
            reason="data_degraded",
            operational_state="CRITICAL",
        )

    if regime.is_uncertain:
        return _flat(
            fv,
            regime,
            now_ms,
            reason="regime_uncertain",
            operational_state="DEGRADED",
        )

    regime_confidence = regime.hmm_posterior[regime.hmm_state]
    if regime_confidence < _MIN_REGIME_CONFIDENCE:
        return _flat(
            fv,
            regime,
            now_ms,
            reason="regime_low_confidence",
            operational_state="DEGRADED",
        )

    fr_z = fv.funding_zscore
    oi_d = fv.oi_log_delta
    intensity = min(abs(fr_z) / _FR_ZSCORE_MAX, 1.0)
    strength = round(intensity * regime_confidence, 4)

    # Sinal SHORT: longs overcrowded
    if fr_z >= _FR_ZSCORE_THRESHOLD and oi_d > 0 and regime.hmm_state_label in ("bull", "sideways"):
        return _signal(
            fv,
            regime,
            now_ms,
            direction=-1,
            strength=strength,
            reason="long_squeeze_risk",
            horizon_hours=horizon_hours,
        )

    # Sinal LONG: shorts overcrowded
    if (
        fr_z <= -_FR_ZSCORE_THRESHOLD
        and oi_d > 0
        and regime.hmm_state_label in ("bear", "sideways")
    ):
        return _signal(
            fv,
            regime,
            now_ms,
            direction=+1,
            strength=strength,
            reason="short_squeeze_risk",
            horizon_hours=horizon_hours,
        )

    # Sem condições atendidas
    return _flat(fv, regime, now_ms, reason="no_signal", operational_state="HEALTHY")


def _signal(
    fv: FeatureVector,
    regime: RegimeOutput,
    now_ms: int,
    direction: int,
    strength: float,
    reason: str,
    horizon_hours: int,
) -> SignalRecord:
    return _build(
        fv,
        regime,
        now_ms,
        direction=direction,
        strength=strength,
        active=True,
        reason=reason,
        horizon_hours=horizon_hours,
        operational_state="HEALTHY",
    )


def _flat(
    fv: FeatureVector,
    regime: RegimeOutput,
    now_ms: int,
    reason: str,
    operational_state: str = "HEALTHY",
) -> SignalRecord:
    return _build(
        fv,
        regime,
        now_ms,
        direction=0,
        strength=0.0,
        active=False,
        reason=reason,
        horizon_hours=0,
        operational_state=operational_state,
    )


def _build(
    fv: FeatureVector,
    regime: RegimeOutput,
    now_ms: int,
    direction: int,
    strength: float,
    active: bool,
    reason: str,
    horizon_hours: int,
    operational_state: str,
) -> SignalRecord:
    return SignalRecord(
        schema_version=_SCHEMA_VERSION,
        event_id=str(uuid.uuid4()),
        timestamp_exchange_ms=fv.timestamp_exchange_ms,
        timestamp_signal_ms=now_ms,
        asset=fv.asset,
        engine_id=_ENGINE_ID,
        regime_state=regime.hmm_state_label,
        regime_confidence=round(regime.hmm_posterior[regime.hmm_state], 4),
        regime_entropy=regime.hmm_entropy,
        regime_is_uncertain=regime.is_uncertain,
        direction=direction,
        strength=strength,
        active=active,
        reason=reason,
        horizon_hours=horizon_hours,
        data_quality_score=fv.data_quality_score,
        operational_state=operational_state,
        features_used={
            "funding_rate_raw": fv.funding_rate_raw,
            "funding_zscore": fv.funding_zscore,
            "oi_log_delta": fv.oi_log_delta,
            "leverage_pressure": fv.leverage_pressure,
            "log_return_8h": fv.log_return_8h,
            "realized_vol_24h": fv.realized_vol_24h,
            "hmm_state": regime.hmm_state,
            "hmm_posterior": regime.hmm_posterior,
        },
    )


# ------------------------------------------------------------------ #
# Persistência — JSONL via predictor_core.obs                        #
# ------------------------------------------------------------------ #


def emit_signal(record: SignalRecord) -> None:
    """
    Emite o sinal como evento estruturado no JSONL via predictor_core.obs.
    Mantém rastreabilidade completa — o event_id permite replay hermético.
    """
    emit_event(
        "v3_cripto",
        "signal_generated",
        metrics={
            "direction": float(record.direction),
            "strength": record.strength,
            "data_quality_score": record.data_quality_score,
            "regime_confidence": record.regime_confidence,
            "regime_entropy": record.regime_entropy,
        },
        metadata={
            "event_id": record.event_id,
            "schema_version": record.schema_version,
            "asset": record.asset,
            "engine_id": record.engine_id,
            "regime_state": record.regime_state,
            "regime_is_uncertain": record.regime_is_uncertain,
            "direction": record.direction,
            "strength": record.strength,
            "active": record.active,
            "reason": record.reason,
            "horizon_hours": record.horizon_hours,
            "operational_state": record.operational_state,
            "timestamp_exchange_ms": record.timestamp_exchange_ms,
            "features_used": record.features_used,
        },
    )


def save_signals_jsonl(records: list[SignalRecord], path: Path) -> None:
    """Persiste lista de SignalRecord como JSONL (append-only)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    logger.info("signal_engine: %d sinais gravados em %s", len(records), path)
