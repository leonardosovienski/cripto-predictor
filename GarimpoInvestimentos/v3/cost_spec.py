"""Custos explícitos e configuráveis da avaliação (fee, spread, slippage; funding realizado).

`v3/costs.py` (CostModel) é artefato protegido da qualificação e não muda. Este módulo
só torna os componentes explícitos e compõe o CostModel existente:

  * taker_fee_bps  taxa por perna (default = o histórico do V3, 10 bps);
  * spread_bps     spread COTADO inteiro; uma ordem taker atravessa meio spread por perna
                   (default 0: preserva exatamente os números históricos do V3, cujo
                   slippage de 5 bps já era o estresse de execução);
  * slippage_bps   impacto/slippage por perna (default = histórico, 5 bps);
  * funding        sempre o funding REALIZADO nas liquidações observadas (com mark price)
                   durante a posição; não é configurável porque é contabilidade do perp.

Mudar os defaults muda o custo das hipóteses registradas — só com trial nova
pré-registrada (ver o aviso em v3/costs.py). Toda métrica de estratégia é líquida.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from GarimpoInvestimentos.trading.contracts import require_finite
from GarimpoInvestimentos.v3.costs import CostModel

FUNDING_ACCOUNTING = "realized_settlements_with_mark_price"


@dataclass(frozen=True)
class CostSpec:
    taker_fee_bps: float = 10.0
    spread_bps: float = 0.0
    slippage_bps: float = 5.0

    def __post_init__(self) -> None:
        for name in ("taker_fee_bps", "spread_bps", "slippage_bps"):
            require_finite(getattr(self, name), name)
            if getattr(self, name) < 0:
                raise ValueError(f"{name} nao pode ser negativo")

    @property
    def per_leg_bps(self) -> float:
        """Fricção por perna: fee + slippage + meio spread."""
        return self.taker_fee_bps + self.slippage_bps + self.spread_bps / 2.0

    def to_cost_model(self) -> CostModel:
        """CostModel com a mesma fricção por perna (o meio spread entra junto do slippage)."""
        return CostModel(
            taker_fee_bps=self.taker_fee_bps,
            slippage_bps=self.slippage_bps + self.spread_bps / 2.0,
        )

    def as_dict(self) -> dict:
        return {**asdict(self), "per_leg_bps": self.per_leg_bps, "funding": FUNDING_ACCOUNTING}
