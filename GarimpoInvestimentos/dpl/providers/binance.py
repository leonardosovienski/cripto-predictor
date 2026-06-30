"""BinanceProvider — fonte primária de preço (Binance via CCXT)."""
from __future__ import annotations

from GarimpoInvestimentos.dpl.providers.ccxt_base import CCXTProvider


class BinanceProvider(CCXTProvider):
    exchange_id = "binance"
