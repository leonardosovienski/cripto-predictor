"""COMPAT SHIM — a agregação mudou-se para predictor_core.data.aggregation.

Promovida ao core na Onda 3. `from GarimpoInvestimentos.dpl.aggregation import
consensus_median, consensus_mean, twap` segue funcionando.
"""
from predictor_core.data import aggregation as _mod
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})
