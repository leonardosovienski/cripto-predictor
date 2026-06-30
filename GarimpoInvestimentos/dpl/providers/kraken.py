"""KrakenProvider — segunda exchange de alta confiabilidade (Kraken via CCXT).

Adicionada na Fase 3 para o modo de agregação (consensus_median): consolidar o preço
de Binance + Kraken imuniza o sinal contra anomalias de uma única corretora.
"""
from __future__ import annotations

from GarimpoInvestimentos.dpl.providers.ccxt_base import CCXTProvider


class KrakenProvider(CCXTProvider):
    exchange_id = "kraken"
