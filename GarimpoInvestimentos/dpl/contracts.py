"""COMPAT SHIM — os contratos da DPL mudaram-se para predictor_core.data.contracts.

Promovido ao core na Onda 3 (paga a dívida da ADR-002). `from GarimpoInvestimentos.dpl
.contracts import MarketDataPoint, DataProvider, DataUnavailableError` segue funcionando;
novo código deve importar de predictor_core.data.contracts.
"""
from predictor_core.data import contracts as _mod
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})
