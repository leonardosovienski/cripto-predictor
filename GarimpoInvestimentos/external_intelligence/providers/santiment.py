"""Santiment GraphQL adapter with body-level failure handling."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from predictor_core.kernel.net import get_http_client, with_retry

from GarimpoInvestimentos.external_intelligence.contracts import (
    CapabilitySnapshot,
    CapabilityState,
    ExternalObservationV1,
    FailureKind,
    PITGrade,
    RightsPolicy,
)
from GarimpoInvestimentos.external_intelligence.providers.common import ProviderError


class SantimentAdapter:
    name = "santiment"
    endpoint = "https://api.santiment.net/graphql"

    @with_retry()
    async def fetch_graphql(
        self, query: str, variables: dict[str, Any], *, api_key: str
    ) -> dict[str, Any]:
        if not api_key:
            raise ProviderError(FailureKind.AUTHENTICATION, "Santiment API key missing")
        async with get_http_client() as client:
            response = await client.post(
                self.endpoint,
                headers={"Authorization": "Apikey " + api_key},
                json={"query": query, "variables": variables},
            )
        if response.status_code == 401:
            raise ProviderError(FailureKind.AUTHENTICATION, "Santiment authentication failed")
        if response.status_code == 403:
            raise ProviderError(FailureKind.AUTHORIZATION, "Santiment request not authorized")
        if response.status_code == 429:
            raise ProviderError(FailureKind.RATE_LIMIT, "Santiment rate limit")
        response.raise_for_status()
        return self.validate_graphql(response.json())

    @staticmethod
    def validate_graphql(payload: object) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ProviderError(FailureKind.SCHEMA_ERROR, "GraphQL body must be an object")
        errors = payload.get("errors")
        data = payload.get("data")
        if errors:
            kind = FailureKind.PARTIAL_RESPONSE if data else FailureKind.BAD_RESPONSE
            raise ProviderError(kind, "Santiment GraphQL body contains errors")
        if not isinstance(data, dict):
            raise ProviderError(FailureKind.SCHEMA_ERROR, "Santiment GraphQL data missing")
        return data

    def restriction_snapshots(
        self, restrictions: list[dict[str, Any]], *, received_at: datetime
    ) -> list[CapabilitySnapshot]:
        snapshots = []
        for item in restrictions:
            name = item.get("name")
            if not isinstance(name, str):
                continue
            if item.get("isAccessible") is not True:
                state = CapabilityState.NOT_AUTHORIZED
            elif item.get("isRestricted") is True:
                state = CapabilityState.RESTRICTED
            elif item.get("isDeprecated") is True:
                state = CapabilityState.DEGRADED
            else:
                state = CapabilityState.SUPPORTED
            snapshots.append(
                CapabilitySnapshot(
                    provider=self.name,
                    scope={"dataset": "metric", "metric": name, "asset": None},
                    state=state,
                    received_at=received_at,
                    evidence={
                        "restricted_from": item.get("restrictedFrom"),
                        "restricted_to": item.get("restrictedTo"),
                        "versions": item.get("availableVersions", []),
                        "deprecated": item.get("isDeprecated"),
                    },
                )
            )
        return snapshots

    def normalize_timeseries(
        self,
        rows: list[dict[str, Any]],
        *,
        metric: str,
        metric_version: str,
        slug: str,
        canonical_asset_id: str,
        received_at: datetime,
        run_id: str,
        run_revision: str,
        historical_request: bool,
        rights: RightsPolicy | None = None,
    ) -> list[ExternalObservationV1]:
        rights = rights or RightsPolicy.unknown()
        result = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("datetime"), str):
                raise ProviderError(FailureKind.SCHEMA_ERROR, "Santiment timeseries row")
            value = row.get("value")
            state = CapabilityState.SUPPORTED if value is not None else CapabilityState.MISSING
            result.append(
                ExternalObservationV1(
                    provider=self.name,
                    dataset="metric-timeseries",
                    canonical_asset_id=canonical_asset_id,
                    provider_asset_id=slug,
                    metric=metric,
                    metric_version=metric_version,
                    value=value,
                    observed_at=datetime.fromisoformat(row["datetime"].replace("Z", "+00:00")),
                    received_at=received_at,
                    pit_grade=PITGrade.RECONSTRUCTED
                    if historical_request
                    else PITGrade.RECEIPT_PIT,
                    rights=rights,
                    collection_run_id=run_id,
                    collection_run_revision=run_revision,
                    capability_state=state,
                )
            )
        return result
