"""Modelo de custos de transação — Risco nº 4 da auditoria (passo 5.2).

Edge de microestrutura vive ou morre nos custos: todo retorno simulado do
backtest DEVE ser líquido. Três componentes, por trade round-trip:

  1. Taxa taker (default 10 bps ≈ 0,10% por perna — ordem a mercado em perp;
     maker seria menor, mas o sinal de 8h não garante fill passivo → conservador).
  2. Slippage (default 5 bps por perna — o mesmo estresse que o veredito NO-GO
     do backtest_v3 já usava).
  3. Funding: posição em perpétuo atravessa janelas de 8h; LONG PAGA funding
     positivo, SHORT RECEBE (e vice-versa). Cobramos o funding_rate_raw VIGENTE
     na abertura para todas as janelas do horizonte — aproximação conservadora
     documentada (o funding futuro não é conhecível em t; usar o corrente evita
     look-ahead e erra pouco em horizonte de 8h = 1 janela).

Fricção (fee+slippage) é sempre custo; funding é SIGNED (pode ser receita).
Unidades: retornos e custos em fração do capital; `position` é fração signed
do capital (direction × strength × kelly).
"""
from dataclasses import dataclass

_FUNDING_WINDOW_HOURS = 8.0


@dataclass(frozen=True)
class CostModel:
    taker_fee_bps: float = 10.0
    slippage_bps: float = 5.0

    def friction(self, position: float) -> float:
        """Custo de fricção round-trip (2 pernas × (fee+slippage)) sobre |posição|.
        Sempre ≥ 0."""
        per_leg = (self.taker_fee_bps + self.slippage_bps) / 10_000.0
        return 2.0 * per_leg * abs(position)

    def funding_pnl(self, position: float, funding_rate: float,
                    horizon_hours: float) -> float:
        """P&L de funding da posição mantida pelo horizonte (signed):
        long paga funding positivo (pnl negativo); short o recebe."""
        n_windows = horizon_hours / _FUNDING_WINDOW_HOURS
        return -position * funding_rate * n_windows

    def net_return(self, gross: float, position: float, funding_rate: float,
                   horizon_hours: float) -> float:
        """Retorno líquido = bruto + funding (signed) − fricção."""
        if position == 0.0:
            return gross
        return gross + self.funding_pnl(position, funding_rate, horizon_hours) \
            - self.friction(position)
