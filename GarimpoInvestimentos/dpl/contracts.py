"""Contratos da DPL — o envelope `MarketDataPoint` e a interface `DataProvider`.

Estes são os tipos que atravessam a fronteira entre fontes externas e o domínio.
Um conector concreto traduz o formato nativo de uma API para `MarketDataPoint`; o
domínio só enxerga este envelope.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime


class DataUnavailableError(Exception):
    """Levantada quando NENHUMA fonte conseguiu entregar o dado solicitado.

    É o sinal terminal do Router após esgotar todos os provedores. O domínio
    decide como reagir (pular o ativo, degradar, etc.).
    """


@dataclass(frozen=True)
class MarketDataPoint:
    """Envelope imutável de um ponto de mercado (OHLCV + metadados de origem).

    `timestamp` é o instante do candle (abertura do período). `published_at` é o
    instante em que o dado se tornou publicamente disponível — âncora do
    Alignment Engine contra lookahead bias (Fase 2). Para dados de preço de
    exchange, os dois coincidem; para fontes de baixa frequência, divergem.
    """

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str
    interval: str
    published_at: datetime

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(
                f"MarketDataPoint inválido para {self.symbol}: high={self.high} < low={self.low}"
            )
        if self.published_at < self.timestamp:
            raise ValueError(
                f"MarketDataPoint inválido para {self.symbol}: published_at "
                f"({self.published_at.isoformat()}) anterior ao timestamp "
                f"({self.timestamp.isoformat()}) — violaria integridade temporal"
            )


class DataProvider(abc.ABC):
    """Contrato que todo conector concreto implementa.

    Implementações devem ser baratas de instanciar (sem rede no __init__) e
    fazer toda a I/O dentro dos métodos async abaixo.
    """

    #: Nome curto e estável da fonte (ex.: "binance", "coingecko"). Usado em
    #: telemetria e no campo `source` do MarketDataPoint.
    name: str = "abstract"

    @abc.abstractmethod
    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        """Retorna os últimos `limit` candles de `symbol` no `interval` dado.

        `symbol` é o ID canônico do domínio (ex.: "bitcoin"); cabe ao conector
        traduzi-lo para o formato nativo da fonte. Deve levantar uma exceção
        (qualquer) em falha — o Router decide se tenta a próxima fonte.
        """

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """True se a fonte parece saudável. Usado pelo Circuit Breaker (Fase 3)."""
