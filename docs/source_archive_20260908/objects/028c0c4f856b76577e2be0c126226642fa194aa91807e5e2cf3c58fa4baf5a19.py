"""
Feature Builder — Fase 1 do Crypto-Predictor V3.

Responsabilidade: transformar dados brutos de funding, OI e spot em
distribuições estacionárias e no contrato canônico FeatureVector.

Sem dependências externas além da stdlib — testável sem rede, sem GPU,
sem qualquer serviço externo. O regime_engine consome este contrato.

FEATURES CALCULADAS:

1. funding_zscore
   Z-score do funding rate sobre janela rolante.
   Estaciona a série (funding tem média próxima de zero mas regime-dependente).
   z = (FR_t - μ_FR) / σ_FR  [janela = fr_window períodos]

2. oi_log_delta
   Variação logarítmica do OI nocional entre períodos consecutivos.
   Δ = ln(OI_t / OI_{t-1})
   Estaciona a série de OI (que é tipicamente não-estacionária).

3. leverage_pressure (métrica composta)
   Combina intensidade do funding com direção/magnitude da mudança de OI.
   LP = funding_zscore × Δ_log_OI
   Interpretação:
     LP > 0  : funding positivo alto (longs overcrowded) E OI crescendo
               → mais longs entrando → risco de squeeze aumenta
     LP < 0  : funding negativo alto (shorts overcrowded) E OI crescendo
               → mais shorts entrando → risco de short squeeze aumenta
     LP ≈ 0  : sem pressão direcional significativa

4. log_return_8h
   Retorno logarítmico do spot nas últimas 8h (alinhado ao período de funding).
   ln(close_t / close_{t-8h})

5. realized_vol_24h
   Desvio padrão dos log returns 1h nas últimas 24h (24 observações).
   Proxy de volatilidade realizada para input do HMM.

ALINHAMENTO TEMPORAL:
   Funding rate: t = 00:00, 08:00, 16:00 UTC
   OI 8h       : timestamps nativamente alinhados
   Spot closes : 1h → selecionamos o close do mesmo open_ms do funding

O join é feito por timestamp_ms com tolerância de ±5min para diferenças de
relógio entre feeds. Registros sem par (funding sem OI ou sem spot) são descartados
com quality_score = 0.0 (NUNCA interpolados).
"""

import bisect
import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Janelas padrão — parametrizáveis pelo pipeline
_DEFAULT_FR_WINDOW = 90  # 90 períodos × 8h = 30 dias
_DEFAULT_VOL_WINDOW_HOURS = 24  # 24 closes 1h para vol realizada
_JOIN_TOLERANCE_MS = 5 * 60 * 1000  # 5 minutos


# ------------------------------------------------------------------ #
# Contrato de dado canônico                                            #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class FeatureVector:
    """
    Contrato imutável de features. Nenhum campo é Optional.
    Dados ausentes ou inválidos → data_quality_score = 0.0 e
    o registro NÃO é gerado (retorna None no builder).
    O signal_engine e o backtest rejeitam vetores com quality < 0.5.
    """

    # Identificação
    timestamp_exchange_ms: int  # timestamp do funding rate (chave de alinhamento)
    asset: str

    # Dados brutos preservados para auditoria
    funding_rate_raw: float
    oi_notional_usd: float
    spot_close: float

    # Features estacionárias
    funding_zscore: float  # z-score janela rolante
    oi_log_delta: float  # Δ log(OI_t / OI_{t-1})
    leverage_pressure: float  # composição FR_zscore × Δ_OI_log
    log_return_8h: float  # retorno log spot 8h alinhado
    realized_vol_24h: float  # std dos log returns 1h das últimas 24h

    # Qualidade
    data_quality_score: float  # 1.0 = todos os dados presentes; 0.0 = inválido


# ------------------------------------------------------------------ #
# Funções de cálculo (puras, sem side effects)                        #
# ------------------------------------------------------------------ #


def _zscore(series: list[float]) -> float:
    """Z-score do último elemento sobre a janela inteira."""
    if len(series) < 2:
        return 0.0
    mean = sum(series) / len(series)
    variance = sum((x - mean) ** 2 for x in series) / len(series)
    std = math.sqrt(variance)
    if std < 1e-12:
        return 0.0
    return (series[-1] - mean) / std


def _log_delta(prev: float, curr: float) -> float | None:
    """Δ log(curr/prev). Retorna None se algum valor for ≤ 0."""
    if prev <= 0.0 or curr <= 0.0:
        return None
    return math.log(curr / prev)


def _realized_vol(log_returns: list[float]) -> float:
    """Desvio padrão populacional dos log returns."""
    n = len(log_returns)
    if n < 2:
        return 0.0
    mean = sum(log_returns) / n
    variance = sum((r - mean) ** 2 for r in log_returns) / n
    return math.sqrt(variance)


# ------------------------------------------------------------------ #
# Alinhamento de séries                                               #
# ------------------------------------------------------------------ #


def _find_closest(target_ms: int, index: dict[int, float], tolerance_ms: int) -> float | None:
    """
    Encontra o valor mais próximo de target_ms no índice.
    Retorna None se o timestamp mais próximo exceder tolerance_ms.
    """
    if target_ms in index:
        return index[target_ms]
    best_ts = min(index.keys(), key=lambda ts: abs(ts - target_ms), default=None)
    if best_ts is None or abs(best_ts - target_ms) > tolerance_ms:
        return None
    return index[best_ts]


def _find_asof(target_ms: int, index: dict[int, float], tolerance_ms: int) -> float | None:
    """Latest observation at or before target; never selects a future value."""
    eligible = (ts for ts in index if ts <= target_ms)
    best_ts = max(eligible, default=None)
    if best_ts is None or target_ms - best_ts > tolerance_ms:
        return None
    return index[best_ts]


# ------------------------------------------------------------------ #
# Builder principal                                                   #
# ------------------------------------------------------------------ #


def build_feature_vectors(
    funding_times_ms: list[int],
    funding_rates: list[float],
    oi_index: dict[int, float],  # timestamp_ms → oi_notional_usd
    spot_index: dict[int, float],  # open_ms → close price (1h klines)
    asset: str,
    fr_window: int = _DEFAULT_FR_WINDOW,
    vol_window_hours: int = _DEFAULT_VOL_WINDOW_HOURS,
    join_tolerance_ms: int = _JOIN_TOLERANCE_MS,
) -> list[FeatureVector]:
    """
    Constrói a série completa de FeatureVectors alinhando funding, OI e spot.

    Parâmetros:
        funding_times_ms : lista de timestamps de funding (ordenada cronologicamente)
        funding_rates    : lista de funding rates correspondentes
        oi_index         : dict {timestamp_ms: oi_notional_usd}
        spot_index       : dict {open_ms: close_price} — klines 1h
        asset            : símbolo (ex.: "BTCUSDT")
        fr_window        : janela para z-score do funding (em períodos 8h)
        vol_window_hours : janela para vol realizada (em klines 1h)
        join_tolerance_ms: tolerância de alinhamento temporal

    Contrato:
        - Registros sem par em OI ou spot → descartados (quality=0, não gerados).
        - Janela de z-score não atingida (fr_window) → descartados.
        - NÃO interpola, NÃO preenche lacunas.
    """
    if len(funding_times_ms) != len(funding_rates):
        raise ValueError("funding_times_ms e funding_rates devem ter o mesmo tamanho")

    n = len(funding_times_ms)
    vectors: list[FeatureVector] = []
    skipped = 0

    # Pré-ordena os closes do spot UMA vez (antes era re-ordenado a cada funding ts:
    # O(n²) — inviável para anos de klines 1h vindos do data lake). bisect → O(log n)/ts.
    sorted_spot_ts = sorted(spot_index.keys())
    sorted_spot_closes = [spot_index[t] for t in sorted_spot_ts]
    ms_per_hour = 3_600_000

    for i in range(n):
        ts = funding_times_ms[i]

        # --- 1. Janela de z-score atingida? ---
        if i < fr_window:
            continue  # sem janela suficiente para z-score

        fr_window_slice = funding_rates[i - fr_window + 1 : i + 1]
        funding_zscore = _zscore(fr_window_slice)

        # --- 2. Δ log OI ---
        oi_curr = _find_asof(ts, oi_index, join_tolerance_ms)
        # OI anterior: timestamp do funding anterior
        oi_prev_ts = funding_times_ms[i - 1] if i > 0 else None
        oi_prev = _find_asof(oi_prev_ts, oi_index, join_tolerance_ms) if oi_prev_ts else None

        if oi_curr is None or oi_prev is None:
            skipped += 1
            logger.debug("feature_builder: OI ausente em ts=%d — descartando", ts)
            continue

        oi_log_delta = _log_delta(oi_prev, oi_curr)
        if oi_log_delta is None:
            skipped += 1
            continue

        # --- 3. Leverage Pressure ---
        leverage_pressure = funding_zscore * oi_log_delta

        # --- 4. Log return 8h (spot) ---
        # Timestamp 8h atrás = funding_times_ms[i-1] (período anterior)
        # spot_index is keyed by candle OPEN while its value is the final close.
        # At ts, only the candle opened one hour earlier is closed/available.
        spot_curr = _find_asof(ts - ms_per_hour, spot_index, join_tolerance_ms)
        spot_prev_ts = funding_times_ms[i - 1]
        spot_prev = _find_asof(spot_prev_ts - ms_per_hour, spot_index, join_tolerance_ms)

        if spot_curr is None or spot_prev is None:
            skipped += 1
            logger.debug("feature_builder: spot ausente em ts=%d — descartando", ts)
            continue

        log_return_8h = _log_delta(spot_prev, spot_curr)
        if log_return_8h is None:
            skipped += 1
            continue

        # --- 5. Realized vol 24h (klines 1h) ---
        # Janela [ts - 24h, ts] localizada por bisect na série pré-ordenada.
        lo_ts = ts - vol_window_hours * ms_per_hour
        lo_idx = bisect.bisect_left(sorted_spot_ts, lo_ts)
        hi_idx = bisect.bisect_right(sorted_spot_ts, ts - ms_per_hour)
        vol_closes = sorted_spot_closes[lo_idx:hi_idx]

        if len(vol_closes) < 2:
            skipped += 1
            continue

        vol_log_returns = [
            math.log(vol_closes[j] / vol_closes[j - 1])
            for j in range(1, len(vol_closes))
            if vol_closes[j - 1] > 0 and vol_closes[j] > 0
        ]
        realized_vol_24h = _realized_vol(vol_log_returns)

        vectors.append(
            FeatureVector(
                timestamp_exchange_ms=ts,
                asset=asset,
                funding_rate_raw=round(funding_rates[i], 8),
                oi_notional_usd=round(oi_curr, 2),
                spot_close=round(spot_curr, 4),
                funding_zscore=round(funding_zscore, 6),
                oi_log_delta=round(oi_log_delta, 8),
                leverage_pressure=round(leverage_pressure, 8),
                log_return_8h=round(log_return_8h, 8),
                realized_vol_24h=round(realized_vol_24h, 8),
                data_quality_score=1.0,
            )
        )

    if skipped:
        logger.warning(
            "feature_builder [%s]: %d/%d timestamps descartados por dados ausentes",
            asset,
            skipped,
            n,
        )

    logger.info("feature_builder [%s]: %d FeatureVectors construídos", asset, len(vectors))
    return vectors


# ------------------------------------------------------------------ #
# Helpers para construção de índices                                  #
# ------------------------------------------------------------------ #


def build_oi_index(oi_records) -> dict[int, float]:
    """Constrói índice {timestamp_ms: oi_notional_usd} de OIRecord[]."""
    return {r.timestamp_ms: r.oi_notional_usd for r in oi_records}


def build_spot_index(kline_records) -> dict[int, float]:
    """Constrói índice {open_ms: close} de KlineRecord[]."""
    return {r.open_ms: r.close for r in kline_records}


def build_volume_index(kline_records) -> dict[int, float]:
    """Constrói índice {open_ms: volume} de KlineRecord[]. Separado de
    build_spot_index (que só devolve close) para não alterar a assinatura usada
    por paper_trader.py/paper_report.py/pipeline.py — H1-H3 continuam
    byte-idênticos. Usado por H9 (docs/HYPOTHESES.md): a razão OI/volume
    precisa do campo `volume` de KlineRecord, que já é coletado
    (spot_collector.py) mas nunca tinha sido consumido."""
    return {r.open_ms: r.volume for r in kline_records}
