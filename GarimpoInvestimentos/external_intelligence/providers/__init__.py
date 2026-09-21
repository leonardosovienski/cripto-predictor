"""Provider adapters. Network transport and retries come from predictor-core."""

from GarimpoInvestimentos.external_intelligence.providers.coinmetrics import CoinMetricsAdapter
from GarimpoInvestimentos.external_intelligence.providers.nansen import NansenAdapter
from GarimpoInvestimentos.external_intelligence.providers.santiment import SantimentAdapter

__all__ = ["CoinMetricsAdapter", "NansenAdapter", "SantimentAdapter"]
