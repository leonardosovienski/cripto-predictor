"""Circuit Breaker — protege fonte e sistema contra falhas repetidas (ADR-004).

Três estados:
  - CLOSED   : chamadas passam; conta falhas consecutivas.
  - OPEN     : após `failure_threshold` falhas, bloqueia chamadas por `reset_timeout`s
               (fail-fast, não desperdiça requisições numa fonte que está caída).
  - HALF_OPEN: passado o timeout, libera UMA chamada de sondagem; sucesso fecha o
               circuito, falha o reabre.

Estado em memória por instância (suficiente para o piloto de ingestão single-process).
O relógio é injetável (`clock`) para testes determinísticos — evita depender do tempo
real. Transições emitem telemetria (obs). Estado compartilhado multi-instância fica
como evolução futura (ver docs/DOSSIE_PLATAFORMA.md §12, ponto em aberto).
"""
from __future__ import annotations

import time
from typing import Callable

from predictor_core.obs import emit_event

CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"
# Default NEUTRO: a DPL é multi-domínio. O dono do domínio (fachada cripto, ingest
# de ações, etc.) injeta o seu via `domain=` — não se hardcoda um domínio na camada
# compartilhada, senão a telemetria de ações/futebol sai atribuída ao cripto.
_DEFAULT_DOMAIN = "dpl"


class CircuitOpenError(Exception):
    """Levantada quando o circuito está aberto e a chamada é bloqueada (fail-fast)."""


class CircuitBreaker:
    def __init__(self, name: str, *, failure_threshold: int = 3,
                 reset_timeout: float = 60.0, clock: Callable[[], float] = time.monotonic,
                 domain: str = _DEFAULT_DOMAIN):
        self.name = name
        self._threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._clock = clock
        self._domain = domain
        self._state = CLOSED
        self._failures = 0
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        # Transição preguiçosa OPEN → HALF_OPEN quando o timeout expira.
        if self._state == OPEN and (self._clock() - self._opened_at) >= self._reset_timeout:
            self._transition(HALF_OPEN)
        return self._state

    def allow(self) -> bool:
        """True se a chamada pode prosseguir. OPEN (ainda no timeout) → False."""
        return self.state != OPEN

    def record_success(self) -> None:
        self._failures = 0
        if self._state != CLOSED:
            self._transition(CLOSED)

    def record_failure(self) -> None:
        self._failures += 1
        # Falha durante a sondagem (HALF_OPEN) ou ao atingir o limiar → abre.
        if self._state == HALF_OPEN or self._failures >= self._threshold:
            self._opened_at = self._clock()
            self._transition(OPEN)

    def _transition(self, new_state: str) -> None:
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        emit_event(self._domain, "circuit.transition",
                   metrics={"failures": self._failures},
                   metadata={"breaker": self.name, "from": old, "to": new_state})
