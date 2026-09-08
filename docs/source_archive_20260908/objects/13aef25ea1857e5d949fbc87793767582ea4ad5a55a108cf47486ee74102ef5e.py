"""COMPAT SHIM — a agregação mudou-se para predictor_core.data.aggregation.

Promovida ao core na Onda 3. `from GarimpoInvestimentos.dpl.aggregation import
consensus_median, consensus_mean, twap` segue funcionando.
"""

from predictor_core.data.aggregation import consensus_mean, consensus_median, twap

__all__ = ["consensus_mean", "consensus_median", "twap"]
