"""`build_portfolio_report()` — a visão única que faltava sobre `portfolio.py`.

As funções de `portfolio.py` sempre foram independentes: beta, correlação, HHI,
exposição por venue, leverage agregada, drawdown. Cada uma respondia uma
pergunta; ninguém as compunha. O handoff de 2026-08-14 registrou isso como gap
("sem build_portfolio_report(); as funções são todas independentes, ninguém as
compõe numa visão única").

Compor NÃO é só conveniência. Risco de portfólio é justamente o que não se vê
olhando posição a posição: duas posições individualmente pequenas e altamente
correlacionadas são uma posição grande disfarçada, e nenhuma métrica isolada
mostra isso.

=== O QUE ESTE RELATÓRIO NÃO FAZ ===

Não emite veredito, não aprova, não bloqueia e não define limite. Ele MEDE e
reporta, incluindo avisos textuais quando um número cruza uma referência — e as
referências são declaradas como CONVENÇÃO DE LEITURA, não como gate: este
projeto não tem limite de risco pré-registrado, e inventar um agora seria criar
um número de aparência oficial sem nada por trás. Continua valendo:
`capital_authorized = false`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from GarimpoInvestimentos.trading.contracts import Position
from GarimpoInvestimentos.trading.portfolio import (
    aggregate_leverage,
    concentration_hhi,
    correlation_matrix,
    exchange_exposure,
)

# Referências de LEITURA, não gates. Origem: convenção comum de mesa, não
# critério pré-registrado deste projeto. Trocá-las não "afrouxa" nada porque
# elas não autorizam nada — só mudam o texto do aviso.
HHI_CONCENTRADO = 0.25  # ~ equivalente a 4 posições iguais
CORRELACAO_ALTA = 0.7


@dataclass(frozen=True)
class PortfolioReport:
    n_positions: int
    equity: float
    gross_notional: float
    gross_leverage: float
    concentration_hhi: float
    exposure_by_venue: dict[str, float]
    max_pairwise_correlation: tuple[str, str, float] | None
    avisos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def nota(self) -> str:
        return (
            "Descritivo. Nao e gate, nao aprova e nao bloqueia: este projeto nao "
            "tem limite de risco pre-registrado. capital_authorized=false."
        )


def build_portfolio_report(
    positions: Iterable[Position],
    mark_prices: dict[str, float],
    *,
    equity: float,
    returns_by_asset: dict[str, Sequence[float]] | None = None,
) -> PortfolioReport:
    """Compõe as métricas de `portfolio.py` numa visão única.

    Reusa as funções existentes em vez de recalcular: divergir delas criaria dois
    números para a mesma pergunta, que é o defeito que a auditoria já pegou
    noutros pontos deste projeto.
    """
    posicoes = list(positions)
    notionais = {}
    for pos in posicoes:
        mark = mark_prices.get(pos.instrument.key)
        if mark is None:
            raise ValueError(f"build_portfolio_report: falta mark price para {pos.instrument.key}")
        notionais[pos.instrument.key] = pos.notional(mark)

    bruto = sum(notionais.values())
    leverage = aggregate_leverage(posicoes, mark_prices, equity) if posicoes else 0.0
    hhi = concentration_hhi(notionais) if notionais else 0.0
    por_venue = exchange_exposure(posicoes, mark_prices) if posicoes else {}

    pior_par: tuple[str, str, float] | None = None
    if returns_by_asset and len(returns_by_asset) >= 2:
        matriz = correlation_matrix({k: list(v) for k, v in returns_by_asset.items()})
        for (a, b), valor in matriz.items():
            if a >= b:  # matriz e simetrica; olha so metade e ignora a diagonal
                continue
            if pior_par is None or abs(valor) > abs(pior_par[2]):
                pior_par = (a, b, valor)

    avisos: list[str] = []
    if hhi >= HHI_CONCENTRADO:
        avisos.append(
            f"concentracao alta: HHI {hhi:.3f} >= {HHI_CONCENTRADO} "
            "(referencia de leitura, nao limite)"
        )
    if pior_par and abs(pior_par[2]) >= CORRELACAO_ALTA:
        avisos.append(
            f"correlacao alta entre {pior_par[0]} e {pior_par[1]}: {pior_par[2]:+.2f} — "
            "posicoes correlacionadas somam risco que a exposicao individual esconde"
        )
    if leverage > 1.0:
        avisos.append(f"leverage bruta {leverage:.2f}x > 1.0 (capital proprio excedido)")

    return PortfolioReport(
        n_positions=len(posicoes),
        equity=equity,
        gross_notional=bruto,
        gross_leverage=leverage,
        concentration_hhi=hhi,
        exposure_by_venue=por_venue,
        max_pairwise_correlation=pior_par,
        avisos=tuple(avisos),
    )


def render(report: PortfolioReport) -> str:
    linhas = [
        "PORTFOLIO REPORT (descritivo — nao e gate)",
        f"  posicoes: {report.n_positions}   equity: {report.equity:,.2f}",
        f"  notional bruto: {report.gross_notional:,.2f}   leverage bruta: {report.gross_leverage:.2f}x",
        f"  concentracao (HHI): {report.concentration_hhi:.3f}",
    ]
    if report.exposure_by_venue:
        linhas.append("  exposicao por venue:")
        for venue, valor in sorted(report.exposure_by_venue.items()):
            linhas.append(f"    {venue:<16}{valor:>14,.2f}")
    if report.max_pairwise_correlation:
        a, b, v = report.max_pairwise_correlation
        linhas.append(f"  maior correlacao par-a-par: {a} x {b} = {v:+.2f}")
    if report.avisos:
        linhas.append("  AVISOS:")
        linhas.extend(f"    - {a}" for a in report.avisos)
    linhas.append(f"  {report.nota}")
    return "\n".join(linhas)


__all__ = [
    "CORRELACAO_ALTA",
    "HHI_CONCENTRADO",
    "PortfolioReport",
    "build_portfolio_report",
    "render",
]
