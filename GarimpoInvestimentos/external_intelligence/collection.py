"""Failure-isolated provider collection orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass

from GarimpoInvestimentos.external_intelligence.contracts import FailureKind
from GarimpoInvestimentos.external_intelligence.providers.common import ProviderError


@dataclass(frozen=True)
class ProviderCollectionResult:
    provider: str
    status: str
    observations: tuple[object, ...]
    failure_kind: str | None = None


async def collect_isolated(
    collectors: Mapping[str, Callable[[], Awaitable[Sequence[object]]]],
) -> list[ProviderCollectionResult]:
    async def one(name: str, call: Callable[[], Awaitable[Sequence[object]]]):
        try:
            rows = await call()
            return ProviderCollectionResult(name, "SUCCEEDED", tuple(rows))
        except ProviderError as exc:
            mapping = {
                FailureKind.AUTHENTICATION: "BLOCKED_AUTH",
                FailureKind.AUTHORIZATION: "BLOCKED_AUTH",
                FailureKind.RESTRICTION: "BLOCKED_RIGHTS",
                FailureKind.RATE_LIMIT: "RATE_LIMITED",
                FailureKind.CREDIT_EXHAUSTED: "CREDIT_EXHAUSTED",
                FailureKind.PROVIDER_UNAVAILABLE: "PROVIDER_UNAVAILABLE",
            }
            return ProviderCollectionResult(
                name, mapping.get(exc.kind, "FAILED"), (), exc.kind.value
            )
        except Exception:
            return ProviderCollectionResult(name, "FAILED", (), FailureKind.UNKNOWN.value)

    return list(
        await asyncio.gather(*(one(name, call) for name, call in sorted(collectors.items())))
    )


def collection_status(results: list[ProviderCollectionResult]) -> str:
    succeeded = sum(result.status == "SUCCEEDED" for result in results)
    return "SUCCEEDED" if succeeded == len(results) else "PARTIAL" if succeeded else "FAILED"
