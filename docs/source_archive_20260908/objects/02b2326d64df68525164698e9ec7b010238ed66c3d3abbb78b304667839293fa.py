"""COMPAT SHIM — o CircuitBreaker do V3 foi UNIFICADO no predictor_core.data.circuit_breaker.

Onda 3: esta implementação e a da dpl viraram uma só, no core (fim da duplicação). O
CircuitBreaker unificado mantém a API do V3 (`can_attempt`, `data_quality_score`, estados
via `CircuitBreaker.CLOSED/OPEN/HALF_OPEN`) e a da dpl (`allow`, relógio injetável,
telemetria). `from GarimpoInvestimentos.v3.circuit_breaker import CircuitBreaker` intacto.
"""

from predictor_core.data.circuit_breaker import CircuitBreaker, CircuitOpenError  # noqa: F401
