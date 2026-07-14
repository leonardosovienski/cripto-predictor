"""COMPAT SHIM — os routers mudaram-se para predictor_core.data.router.

Promovidos ao core na Onda 3. `from GarimpoInvestimentos.dpl.router import FallbackRouter,
AggregationRouter` segue funcionando.
"""
from predictor_core.data.router import AggregationRouter, FallbackRouter

__all__ = ["AggregationRouter", "FallbackRouter"]
