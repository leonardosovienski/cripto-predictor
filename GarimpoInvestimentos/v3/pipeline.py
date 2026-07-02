"""
Pipeline — Fase 1 do Crypto-Predictor V3.

Orquestrador de ponta a ponta:
    1. Coleta histórica: funding + OI + spot (com circuit breakers)
    2. Constrói FeatureVectors (alinhamento temporal, sem interpolação)
    3. Treina RegimeEngine sobre série in-sample completa
    4. Gera sinais causais para toda a série
    5. Persiste dados brutos (CSV) e sinais (JSONL) em data/v3/
    6. Emite evento wfa_ready via predictor_core.obs

USO (CLI):
    python -m GarimpoInvestimentos.v3.pipeline \
        --symbol BTCUSDT \
        --start-date 2023-01-01 \
        --end-date 2024-12-31

    python -m GarimpoInvestimentos.v3.pipeline \
        --symbol ETHUSDT SOLUSDT \
        --start-date 2024-01-01

DEPENDÊNCIAS:
    pip install hmmlearn numpy scikit-learn httpx
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.v3.circuit_breaker import CircuitBreaker
from GarimpoInvestimentos.v3.collectors.funding_collector import (
    FundingCollector,
    load_funding_csv,
    save_funding_csv,
)
from GarimpoInvestimentos.v3.collectors.oi_collector import (
    OICollector,
    load_oi_csv,
    save_oi_csv,
)
from GarimpoInvestimentos.v3.collectors.spot_collector import (
    SpotCollector,
    load_spot_csv,
    save_spot_csv,
)
from GarimpoInvestimentos.v3.feature_builder import (
    build_feature_vectors,
    build_oi_index,
    build_spot_index,
)
from GarimpoInvestimentos.v3.regime_engine import RegimeEngine, StaleRegimeModelError
from GarimpoInvestimentos.v3.signal_engine import (
    SignalRecord,
    emit_signal,
    generate_signal,
    save_signals_jsonl,
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Caminhos de dados                                                   #
# ------------------------------------------------------------------ #

_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "v3"


def _symbol_dir(symbol: str) -> Path:
    return _DATA_ROOT / symbol


def _funding_path(symbol: str) -> Path:
    return _symbol_dir(symbol) / "funding.csv"


def _oi_path(symbol: str) -> Path:
    return _symbol_dir(symbol) / "oi.csv"


def _spot_path(symbol: str) -> Path:
    return _symbol_dir(symbol) / "spot_1h.csv"


def _signals_path(symbol: str) -> Path:
    return _symbol_dir(symbol) / "signals.jsonl"


def _model_path(symbol: str) -> Path:
    return _symbol_dir(symbol) / "regime_engine.pkl"


# ------------------------------------------------------------------ #
# Conversão de data para ms                                           #
# ------------------------------------------------------------------ #

def _date_to_ms(date_str: str) -> int:
    """'YYYY-MM-DD' → timestamp UTC início do dia em ms."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


# ------------------------------------------------------------------ #
# Coleta (assíncrona)                                                 #
# ------------------------------------------------------------------ #

async def _collect_symbol(
    symbol: str,
    start_ms: int,
    end_ms: int,
    force_refresh: bool = False,
) -> tuple[list, list, list]:
    """
    Coleta funding, OI e spot para um símbolo.
    Se os CSVs já existem e force_refresh=False, usa os dados locais.
    Retorna (funding_records, oi_records, kline_records).
    """
    cb_funding = CircuitBreaker(f"funding_{symbol}")
    cb_oi = CircuitBreaker(f"oi_{symbol}")
    cb_spot = CircuitBreaker(f"spot_{symbol}")

    # --- Funding ---
    f_path = _funding_path(symbol)
    if f_path.exists() and not force_refresh:
        funding = load_funding_csv(f_path)
        logger.info("pipeline [%s]: %d registros de funding do cache", symbol, len(funding))
    else:
        collector = FundingCollector(symbol, cb_funding)
        funding = await collector.fetch_range(start_ms, end_ms)
        save_funding_csv(funding, f_path)

    # --- OI ---
    oi_path = _oi_path(symbol)
    if oi_path.exists() and not force_refresh:
        oi = load_oi_csv(oi_path)
        logger.info("pipeline [%s]: %d registros de OI do cache", symbol, len(oi))
    else:
        collector = OICollector(symbol, cb_oi)
        oi = await collector.fetch_range(start_ms, end_ms)
        save_oi_csv(oi, oi_path)

    # --- Spot 1h ---
    spot_path = _spot_path(symbol)
    if spot_path.exists() and not force_refresh:
        spot = load_spot_csv(spot_path)
        logger.info("pipeline [%s]: %d klines do cache", symbol, len(spot))
    else:
        collector = SpotCollector(symbol, cb_spot)
        spot = await collector.fetch_range(start_ms, end_ms)
        save_spot_csv(spot, spot_path)

    return funding, oi, spot


# ------------------------------------------------------------------ #
# Pipeline completo de um símbolo                                     #
# ------------------------------------------------------------------ #

async def run_symbol(
    symbol: str,
    start_date: str,
    end_date: str | None = None,
    force_refresh: bool = False,
    horizon_hours: int = 24,
) -> list[SignalRecord]:
    """
    Executa o pipeline completo para um símbolo e retorna todos os sinais gerados.
    """
    start_ms = _date_to_ms(start_date)
    end_ms = _date_to_ms(end_date) if end_date else _now_ms()

    logger.info(
        "pipeline [%s]: iniciando coleta %s → %s",
        symbol, start_date, end_date or "agora",
    )

    # 1. Coleta
    funding_records, oi_records, kline_records = await _collect_symbol(
        symbol, start_ms, end_ms, force_refresh,
    )

    if not funding_records:
        logger.error("pipeline [%s]: sem dados de funding — abortando", symbol)
        emit_event(
            "v3_cripto", "pipeline_aborted",
            metrics={"data_quality_score": 0.0},
            metadata={"symbol": symbol, "reason": "no_funding_data"},
        )
        return []

    # 2. Índices para join
    oi_index = build_oi_index(oi_records)
    spot_index = build_spot_index(kline_records)

    # 3. Feature vectors
    funding_times_ms = [r.funding_time_ms for r in funding_records]
    funding_rates = [r.funding_rate for r in funding_records]

    feature_vectors = build_feature_vectors(
        funding_times_ms=funding_times_ms,
        funding_rates=funding_rates,
        oi_index=oi_index,
        spot_index=spot_index,
        asset=symbol,
    )

    if len(feature_vectors) < 100:
        logger.error(
            "pipeline [%s]: apenas %d feature vectors — mínimo 100 para treinar HMM",
            symbol, len(feature_vectors),
        )
        emit_event(
            "v3_cripto", "pipeline_aborted",
            metrics={"data_quality_score": 0.0},
            metadata={"symbol": symbol, "reason": "insufficient_features", "count": len(feature_vectors)},
        )
        return []

    logger.info("pipeline [%s]: %d feature vectors construídos", symbol, len(feature_vectors))

    # 4. Treinar HMM sobre série completa (in-sample para o pipeline de sinal)
    #    O backtest_v3 fará o WFA com janelas rolantes — este fit é para produção.
    model_path = _model_path(symbol)
    engine = RegimeEngine()

    log_returns = [fv.log_return_8h for fv in feature_vectors]
    realized_vols = [fv.realized_vol_24h for fv in feature_vectors]

    if model_path.exists() and not force_refresh:
        try:
            engine.load(model_path)
            logger.info("pipeline [%s]: modelo RegimeEngine carregado de %s", symbol, model_path)
        except StaleRegimeModelError as exc:
            # Contrato de features/HMM mudou: o .pkl em cache é incoerente. Auto-cura
            # retreinando em vez de servir previsões erradas em silêncio.
            logger.warning("pipeline [%s]: modelo em cache incompatível — retreinando. %s",
                           symbol, exc)
            engine.fit(log_returns, realized_vols)
            engine.save(model_path)
    else:
        logger.info("pipeline [%s]: treinando RegimeEngine com %d obs…", symbol, len(feature_vectors))
        engine.fit(log_returns, realized_vols)
        engine.save(model_path)

    # 5. Inferência causal — um regime por feature vector
    regime_series = engine.predict_series(log_returns, realized_vols)

    # 6. Geração de sinais
    signals: list[SignalRecord] = []
    for fv, regime in zip(feature_vectors, regime_series):
        signal = generate_signal(fv, regime, horizon_hours=horizon_hours)
        signals.append(signal)
        if signal.active:
            emit_signal(signal)

    # 7. Persistência
    sig_path = _signals_path(symbol)
    save_signals_jsonl(signals, sig_path)

    active_count = sum(1 for s in signals if s.active)
    logger.info(
        "pipeline [%s]: %d sinais totais, %d ativos → %s",
        symbol, len(signals), active_count, sig_path,
    )

    emit_event(
        "v3_cripto", "pipeline_complete",
        metrics={
            "n_features": float(len(feature_vectors)),
            "n_signals": float(len(signals)),
            "n_active": float(active_count),
            "signal_rate": round(active_count / len(signals), 4) if signals else 0.0,
        },
        metadata={
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date or "now",
            "model_path": str(model_path),
            "signals_path": str(sig_path),
        },
    )

    return signals


# ------------------------------------------------------------------ #
# CLI                                                                  #
# ------------------------------------------------------------------ #

async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Crypto-Predictor V3 — Pipeline Fase 1",
    )
    parser.add_argument(
        "--symbol",
        nargs="+",
        default=["BTCUSDT"],
        help="Símbolos Binance Futures (ex: BTCUSDT ETHUSDT). Default: BTCUSDT",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Data de início no formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Data de fim (YYYY-MM-DD). Default: hoje",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignora cache e re-coleta todos os dados da Binance",
    )
    parser.add_argument(
        "--horizon-hours",
        type=int,
        default=24,
        help="Horizonte em horas para o sinal (default: 24)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    for symbol in args.symbol:
        await run_symbol(
            symbol=symbol.upper(),
            start_date=args.start_date,
            end_date=args.end_date,
            force_refresh=args.force_refresh,
            horizon_hours=args.horizon_hours,
        )


if __name__ == "__main__":
    asyncio.run(_main())
