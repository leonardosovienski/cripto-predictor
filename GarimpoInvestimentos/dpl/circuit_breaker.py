"""COMPAT SHIM — o CircuitBreaker mudou-se para predictor_core.data.circuit_breaker.

Onda 3: as DUAS implementações do cripto (esta, da dpl, e a v3/circuit_breaker) foram
UNIFICADAS numa só, no core. `from GarimpoInvestimentos.dpl.circuit_breaker import
CircuitBreaker, CircuitOpenError` e as constantes de estado seguem funcionando.

Nota de semântica: o `state` unificado é um getter PURO — a transição OPEN→HALF_OPEN
acontece em `allow()`/`can_attempt()` (não ao ler `state`). O router usa `allow()`,
então o comportamento de produção é idêntico.
"""
from predictor_core.data.circuit_breaker import CircuitBreaker, CircuitOpenError  # noqa: F401

# Constantes de módulo (compat: test_dpl_aggregation importa CLOSED/OPEN/HALF_OPEN daqui).
CLOSED = CircuitBreaker.CLOSED
OPEN = CircuitBreaker.OPEN
HALF_OPEN = CircuitBreaker.HALF_OPEN
