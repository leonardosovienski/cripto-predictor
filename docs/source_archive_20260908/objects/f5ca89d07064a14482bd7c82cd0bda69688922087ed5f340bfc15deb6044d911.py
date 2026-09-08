from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

T = TypeVar("T", covariant=True)


@dataclass(frozen=True)
class ResiliencePolicy:
    timeout_seconds: float = 15.0
    max_attempts: int = 3
    backoff_base_seconds: float = 0.5
    backoff_max_seconds: float = 30.0
    jitter_ratio: float = 0.2
    requests_per_minute: int = 10
    circuit_failure_threshold: int = 5
    circuit_recovery_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.max_attempts < 1 or self.requests_per_minute < 1:
            raise ValueError("invalid resilience policy")


class ExternalProvider(Protocol[T]):
    name: str
    policy: ResiliencePolicy

    async def fetch(self, request: object) -> T: ...
    def validate(self, payload: object) -> T: ...
    def redact(self, value: str) -> str: ...
