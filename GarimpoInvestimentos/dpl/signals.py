"""COMPAT SHIM — SignalPoint/SignalProvider mudaram-se para predictor_core.data.contracts.

Promovidos ao core na Onda 3. `from GarimpoInvestimentos.dpl.signals import SignalPoint,
SignalProvider` segue funcionando; novo código importa de predictor_core.data.contracts.
"""
from predictor_core.data.contracts import SignalPoint, SignalProvider  # noqa: F401
