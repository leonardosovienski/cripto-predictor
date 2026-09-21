from __future__ import annotations

from dataclasses import dataclass

from GarimpoInvestimentos.external_intelligence.contracts import FailureKind


class ProviderError(RuntimeError):
    def __init__(self, kind: FailureKind, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass
class RequestBudget:
    limit: int
    used: int = 0

    def consume(self, amount: int = 1) -> None:
        if amount < 1 or self.used + amount > self.limit:
            raise ProviderError(FailureKind.CREDIT_EXHAUSTED, "request budget exhausted")
        self.used += amount
