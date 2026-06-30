"""SignalPoint — envelope de um sinal de baixa frequência (não-OHLCV).

Ex.: Fear & Greed Index (diário). Carrega `published_at` para o as-of join do
Alignment Engine, idêntico em papel ao do MarketDataPoint.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SignalPoint:
    name: str
    timestamp: datetime
    value: float
    source: str
    published_at: datetime

    def __post_init__(self) -> None:
        if self.published_at < self.timestamp:
            raise ValueError(
                f"SignalPoint '{self.name}': published_at anterior ao timestamp "
                "— violaria integridade temporal"
            )


class SignalProvider(abc.ABC):
    """Contrato de uma fonte de sinal de baixa frequência (não-OHLCV)."""

    name: str = "abstract_signal"

    @abc.abstractmethod
    async def fetch(self, limit: int = 30) -> list[SignalPoint]:
        """Retorna os últimos `limit` pontos do sinal, com published_at."""
