"""
Circuit Breaker para coletores REST da Fase 1.

Estados: CLOSED → OPEN → HALF_OPEN → CLOSED
- CLOSED  : operação normal; data_quality_score = 1.0
- OPEN    : bloqueado; data_quality_score = 0.0; aguarda reset_timeout
- HALF_OPEN: prova com uma tentativa; se OK → CLOSED, se falha → OPEN

Intencional: sem asyncio.Lock — atribuições de atributos simples são
atômicas no CPython (GIL). Suficiente para o uso single-event-loop desta fase.
"""
import logging
import time

logger = logging.getLogger(__name__)


class CircuitBreaker:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None

    # ------------------------------------------------------------------ #
    # Propriedades públicas                                                #
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> str:
        return self._state

    @property
    def data_quality_score(self) -> float:
        """Propaga degradação para o contrato de dados downstream."""
        if self._state == self.CLOSED:
            return 1.0
        if self._state == self.HALF_OPEN:
            return 0.5
        return 0.0  # OPEN

    # ------------------------------------------------------------------ #
    # Interface de controle                                                #
    # ------------------------------------------------------------------ #

    def can_attempt(self) -> bool:
        """Retorna True se o circuito permite uma tentativa agora."""
        if self._state == self.CLOSED:
            return True
        if self._state == self.OPEN:
            if (
                self._last_failure_time is not None
                and (time.monotonic() - self._last_failure_time) >= self.reset_timeout
            ):
                self._state = self.HALF_OPEN
                logger.info("CircuitBreaker [%s]: OPEN → HALF_OPEN (sondando)", self.name)
                return True
            return False
        # HALF_OPEN: permite exatamente uma tentativa
        return True

    def record_success(self) -> None:
        if self._state != self.CLOSED:
            logger.info(
                "CircuitBreaker [%s]: %s → CLOSED", self.name, self._state
            )
        self._failure_count = 0
        self._state = self.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            if self._state != self.OPEN:
                logger.warning(
                    "CircuitBreaker [%s]: → OPEN após %d falhas",
                    self.name,
                    self._failure_count,
                )
            self._state = self.OPEN
        else:
            logger.warning(
                "CircuitBreaker [%s]: falha %d/%d (CLOSED)",
                self.name,
                self._failure_count,
                self.failure_threshold,
            )
