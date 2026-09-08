"""Política de custo canônica — resolve o gap dos "dois modelos não reconciliados".

O handoff de 2026-08-14 registrou: "dois modelos de custo não reconciliados —
`v3/costs.py` (bps fixo) e `trading/microstructure.py` (anda o book) coexistem
sem nenhum ter sido escolhido como 'o' modelo canônico".

=== POR QUE "RECONCILIAR" NAO E FUNDIR OS DOIS ===

Ao ler os dois, a premissa da pergunta se desfaz: eles nao sao duas respostas
concorrentes para a mesma pergunta — sao respostas para instrumentos
DIFERENTES.

  v3/costs.py (CostModel)        -> PERPETUO. Fee taker + slippage em bps fixos
                                    + funding signed por janela de 8h. Funding
                                    so existe em perpetuo.
  trading/costs.py (spot)        -> SPOT. Walk-the-book: spread e profundidade
                                    entram no VWAP, sem funding porque spot nao
                                    tem. Marcado como NAO CALIBRADO.

Fundir seria pior que deixar separado: produziria um modelo que cobra funding de
spot ou ignora profundidade em perp. O que faltava nao era um modelo unico — era
um PONTO DE ENTRADA unico que escolhe o certo pelo instrumento e RECUSA o errado.

=== A REGRA CANONICA, declarada ===

1. `asset_class` do `Instrument` decide. `crypto_perp` -> CostModel;
   `crypto_spot` -> walk-the-book. Classe desconhecida => erro, nunca um default
   silencioso: aplicar custo errado por omissao e como nao aplicar custo.
2. Para VEREDITO CIENTIFICO, o canonico e o `v3/costs.py` — foi ele que sustentou
   os NO-GO de H1/H2/H3, esta calibrado em bps observaveis e nao depende de book.
   O walk-the-book permanece explicitamente NAO CALIBRADO (docs/HYPOTHESES.md,
   override 2026-08-14) e por isso NAO pode ser usado para emitir veredito
   enquanto nao passar por calibracao contra execucao real.
3. Esta politica NAO altera nenhum veredito ja emitido. H1/H2/H3 foram julgadas
   com o CostModel e continuam como estao.
"""

from __future__ import annotations

from GarimpoInvestimentos.trading.contracts import Instrument
from GarimpoInvestimentos.v3.costs import CostModel

PERP = "crypto_perp"
SPOT = "crypto_spot"

#: Classes cujo custo pode sustentar veredito cientifico hoje.
CALIBRATED_FOR_VERDICT = frozenset({PERP})


class CostModelMismatch(ValueError):
    """Modelo de custo incompativel com o instrumento, ou classe desconhecida."""


class UncalibratedCostModel(ValueError):
    """Modelo nao calibrado usado onde se exige rigor de veredito."""


def cost_model_for(instrument: Instrument, *, for_verdict: bool = False):
    """Devolve o modelo de custo canonico do instrumento.

    `for_verdict=True` quando o numero vai sustentar decisao cientifica: nesse
    modo, classe cujo modelo nao esta calibrado LEVANTA em vez de devolver um
    numero de aparencia oficial.
    """
    classe = instrument.asset_class
    if classe not in (PERP, SPOT):
        raise CostModelMismatch(
            f"asset_class desconhecida: {classe!r}. Conhecidas: {PERP!r}, {SPOT!r}. "
            "Sem default: aplicar custo errado por omissao equivale a nao aplicar custo."
        )
    if for_verdict and classe not in CALIBRATED_FOR_VERDICT:
        raise UncalibratedCostModel(
            f"o modelo de custo de {classe!r} (walk-the-book, trading/costs.py) e "
            "explicitamente NAO CALIBRADO contra execucao real (override 2026-08-14). "
            "Nao pode sustentar veredito cientifico. Use-o para simulacao/auditoria, "
            "ou calibre-o antes."
        )
    if classe == PERP:
        return CostModel()
    from GarimpoInvestimentos.trading.costs import simulate_spot_long_round_trip

    return simulate_spot_long_round_trip


def assert_verdict_grade(instrument: Instrument) -> None:
    """Guarda para call sites que emitem veredito. Levanta se o instrumento nao
    tem modelo de custo calibrado."""
    cost_model_for(instrument, for_verdict=True)


__all__ = [
    "CALIBRATED_FOR_VERDICT",
    "PERP",
    "SPOT",
    "CostModelMismatch",
    "UncalibratedCostModel",
    "assert_verdict_grade",
    "cost_model_for",
]
