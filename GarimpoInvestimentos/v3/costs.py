"""Modelo de custos de transação — Risco nº 4 da auditoria (passo 5.2).

Edge de microestrutura vive ou morre nos custos: todo retorno simulado do
backtest DEVE ser líquido. Três componentes, por trade round-trip:

  1. Taxa taker (default 10 bps ≈ 0,10% por perna — ordem a mercado em perp;
     maker seria menor, mas o sinal de 8h não garante fill passivo → conservador).
     PROVENIÊNCIA NÃO DOCUMENTADA: este valor não foi conferido contra a tabela
     de fees/tier VIP de nenhuma conta real (a Binance Futures VIP0 cobra 5bps
     taker padrão — o dobro aqui é deliberadamente conservador, mas a origem
     exata do número "10" nunca foi registrada nem citada com data/fonte).
     Não alterar sem nova trial pré-registrada: H1 perdeu por margem estreita
     (líquido −0,09bps vs. −0,53bps de custo total), então revisar este valor
     tem efeito material sobre o veredito e cai sob a mesma trava de
     `frozen_families` — mudança de custo pede o mesmo rigor que mudança de
     sinal, não é ajuste de infraestrutura livre.
  2. Slippage (default 5 bps por perna — o mesmo estresse que o veredito NO-GO
     do backtest_v3 já usava).
  3. Funding: posição em perpétuo atravessa janelas de 8h; LONG PAGA funding
     positivo, SHORT RECEBE (e vice-versa). Cobramos o funding_rate_raw VIGENTE
     na abertura para todas as janelas do horizonte — cenario de taxa constante, que pode subestimar ou superestimar o realizado,
     explicitamente sem garantia conservadora (o funding futuro não é conhecível em t; usar o corrente evita
     look-ahead e erra pouco em horizonte de 8h = 1 janela).

Fricção (fee+slippage) é sempre custo; funding é SIGNED (pode ser receita).
Unidades: retornos e custos em fração do capital; `position` é fração signed
do capital (direction × strength × kelly).
"""

from dataclasses import dataclass

from GarimpoInvestimentos.trading.contracts import require_finite

_FUNDING_WINDOW_HOURS = 8.0


@dataclass(frozen=True)
class CostModel:
    taker_fee_bps: float = 10.0
    slippage_bps: float = 5.0

    def __post_init__(self) -> None:
        for name in ("taker_fee_bps", "slippage_bps"):
            require_finite(getattr(self, name), name)
            if getattr(self, name) < 0:
                raise ValueError("custos nao podem ser negativos")

    def friction(self, position: float, *, exit_price_ratio: float = 1.0) -> float:
        """Custo de fricção round-trip (2 pernas × (fee+slippage)) sobre |posição|.
        Sempre ≥ 0."""
        require_finite(position, "position")
        require_finite(exit_price_ratio, "exit_price_ratio")
        if exit_price_ratio <= 0:
            raise ValueError("exit_price_ratio deve ser positivo")
        per_leg = (self.taker_fee_bps + self.slippage_bps) / 10_000.0
        return (1 + exit_price_ratio) * per_leg * abs(position)

    def funding_pnl(self, position: float, funding_rate: float, horizon_hours: float) -> float:
        """P&L de funding da posição mantida pelo horizonte (signed):
        long paga funding positivo (pnl negativo); short o recebe."""
        for name, value in (
            ("position", position),
            ("funding_rate", funding_rate),
            ("horizon_hours", horizon_hours),
        ):
            require_finite(value, name)
        if horizon_hours < 0:
            raise ValueError("horizon_hours nao pode ser negativo")
        n_windows = horizon_hours / _FUNDING_WINDOW_HOURS
        return -position * funding_rate * n_windows

    def net_return(
        self, gross: float, position: float, funding_rate: float, horizon_hours: float
    ) -> float:
        """Retorno líquido = bruto + funding (signed) − fricção."""
        require_finite(gross, "gross")
        require_finite(position, "position")
        if position == 0.0:
            return gross
        return (
            gross
            + self.funding_pnl(position, funding_rate, horizon_hours)
            - self.friction(position)
        )
