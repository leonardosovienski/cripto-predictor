"""Data Provider Layer (DPL) — piloto da Fase 1.

Camada de abstração de fontes de dados de mercado. Nasce aqui no domínio
(evolução por demanda); quando estável e genérica, é candidata a promoção para
`predictor_core`. O domínio consome apenas a fachada `CryptoDataProvider` e o
contrato `MarketDataPoint` — nunca conhece Binance, CoinGecko ou o CCXT.

Ver docs/DOSSIE_PLATAFORMA.md §5 (componentes) e §7 (plano de fases).
"""
from GarimpoInvestimentos.dpl.aggregation import consensus_mean, consensus_median, twap
from GarimpoInvestimentos.dpl.alignment import AlignmentEngine
from GarimpoInvestimentos.dpl.circuit_breaker import CircuitBreaker, CircuitOpenError
from GarimpoInvestimentos.dpl.contracts import (
    DataProvider,
    DataUnavailableError,
    MarketDataPoint,
)
from GarimpoInvestimentos.dpl.facade import CryptoDataProvider
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.router import AggregationRouter, FallbackRouter
from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider

__all__ = [
    "DataProvider",
    "DataUnavailableError",
    "MarketDataPoint",
    "CryptoDataProvider",
    "FallbackRouter",
    "AggregationRouter",
    "AlignmentEngine",
    "FeatureStore",
    "SignalPoint",
    "SignalProvider",
    "CircuitBreaker",
    "CircuitOpenError",
    "consensus_median",
    "consensus_mean",
    "twap",
]
