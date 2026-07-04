"""COMPAT SHIM — os routers mudaram-se para predictor_core.data.router.

Promovidos ao core na Onda 3. `from GarimpoInvestimentos.dpl.router import FallbackRouter,
AggregationRouter` segue funcionando.
"""
from predictor_core.data import router as _mod
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})
