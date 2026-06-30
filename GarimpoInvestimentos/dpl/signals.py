"""SignalPoint — envelope de um sinal de baixa frequência (não-OHLCV).

Ex.: Fear & Greed (diário, cripto), Selic/IPCA (BCB, macro). Carrega `published_at`
para o as-of join do Alignment Engine, idêntico em papel ao do MarketDataPoint.

Point-in-time / revisões (Fase 4): séries macro são revisadas (o BCB republica o IPCA
de um mês). Modelamos cada revisão como um SignalPoint SEPARADO com seu próprio
`published_at` (instante em que ficou público) e `vintage` (instante de coleta). O
as-of por `published_at` do Alignment Engine então escolhe automaticamente o valor
vigente em cada data — sem lookahead, sem lógica extra (ver ADR-008).
  - timestamp      : instante do dado (grade do as-of join e do max_staleness).
  - reference_date : referência semântica (ex.: mês do IPCA); default = timestamp.
  - vintage        : quando o dado foi coletado; distingue revisões na persistência.
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
    # Campos opcionais (aditivos — cripto/Fear&Greed seguem funcionando sem eles).
    reference_date: datetime | None = None
    vintage: datetime | None = None

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
