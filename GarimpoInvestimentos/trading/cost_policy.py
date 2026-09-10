"""Route simulation costs by instrument; historical use is not execution calibration.

Neither the fixed-bps perpetual scenario nor the spot order-book simulation has
account/tier/size-specific calibration sufficient to certify realized profitability.
Historical frozen NO-GO results remain preserved; they are not recalibrated here.
"""

from __future__ import annotations

from GarimpoInvestimentos.trading.contracts import Instrument
from GarimpoInvestimentos.v3.costs import CostModel

PERP = "crypto_perp"
SPOT = "crypto_spot"

#: Classes cujo custo pode sustentar veredito cientifico hoje.
CALIBRATED_FOR_VERDICT = frozenset()


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
            f"o modelo de custo de {classe!r} e "
            "NAO CALIBRADO contra execucao real para conta/tamanho/tier. "
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
