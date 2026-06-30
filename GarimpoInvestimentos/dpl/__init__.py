"""Data Provider Layer (DPL) — piloto da Fase 1.

Camada de abstração de fontes de dados de mercado. Nasce aqui no domínio
(evolução por demanda); quando estável e genérica, é candidata a promoção para
`predictor_core`. O domínio consome apenas a fachada `CryptoDataProvider` e o
contrato `MarketDataPoint` — nunca conhece Binance, CoinGecko ou o CCXT.

Ver docs/DOSSIE_PLATAFORMA.md §5 (componentes) e §7 (plano de fases).
"""
from GarimpoInvestimentos.dpl.alignment import AlignmentEngine
from GarimpoInvestimentos.dpl.contracts import (
    DataProvider,
    DataUnavailableError,
    MarketDataPoint,
)
from GarimpoInvestimentos.dpl.facade import CryptoDataProvider
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.router import FallbackRouter
from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider

__all__ = [
    "DataProvider",
    "DataUnavailableError",
    "MarketDataPoint",
    "CryptoDataProvider",
    "FallbackRouter",
    "AlignmentEngine",
    "FeatureStore",
    "SignalPoint",
    "SignalProvider",
]
