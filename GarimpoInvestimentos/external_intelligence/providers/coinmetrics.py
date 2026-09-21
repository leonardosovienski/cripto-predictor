"""Conservative Coin Metrics API v4 adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

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


class CoinMetricsAdapter:
    name = "coinmetrics"
    base_url = "https://community-api.coinmetrics.io/v4"
    allowed_hosts = frozenset({"community-api.coinmetrics.io", "api.coinmetrics.io"})

    async def fetch_pages(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        rows, _ = await self.fetch_pages_with_receipt(path, params)
        return rows

    @with_retry()
    async def fetch_pages_with_receipt(
        self, path: str, params: dict[str, str]
    ) -> tuple[list[dict[str, Any]], int]:
        url = self.base_url + "/" + path.lstrip("/")
        rows: list[dict[str, Any]] = []
        requests = 0
        async with get_http_client() as client:
            while url:
                requests += 1
                response = await client.get(url, params=params if not rows else None)
                if response.status_code == 401:
                    raise ProviderError(
                        FailureKind.AUTHENTICATION, "Coin Metrics authentication failed"
                    )
                if response.status_code == 403:
                    raise ProviderError(
                        FailureKind.AUTHORIZATION, "Coin Metrics dataset not authorized"
                    )
                if response.status_code == 429:
                    raise ProviderError(FailureKind.RATE_LIMIT, "Coin Metrics rate limit")
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                    raise ProviderError(FailureKind.SCHEMA_ERROR, "Coin Metrics response schema")
                rows.extend(payload["data"])
                url = payload.get("next_page_url") or ""
                if url and urlparse(url).hostname not in self.allowed_hosts:
                    raise ProviderError(FailureKind.BAD_RESPONSE, "untrusted pagination host")
        return rows, requests

    def capability_snapshots(
        self, catalog_rows: list[dict[str, Any]], *, received_at: datetime
    ) -> list[CapabilitySnapshot]:
        snapshots = []
        for row in catalog_rows:
            asset = row.get("asset")
            metrics = row.get("metrics")
            if not isinstance(asset, str) or not isinstance(metrics, list):
                continue
            for metric in sorted(item for item in metrics if isinstance(item, str)):
                snapshots.append(
                    CapabilitySnapshot(
                        provider=self.name,
                        scope={"asset": asset, "metric": metric, "dataset": "asset-metrics"},
                        state=CapabilityState.SUPPORTED,
                        received_at=received_at,
                        evidence={"source": "catalog-v2/asset-metrics"},
                    )
                )
        return snapshots

    def normalize_asset_metrics(
        self,
        rows: list[dict[str, Any]],
        *,
        metrics: tuple[str, ...],
        mappings: dict[str, str],
        received_at: datetime,
        run_id: str,
        run_revision: str,
        historical_request: bool,
        rights: RightsPolicy | None = None,
    ) -> list[ExternalObservationV1]:
        rights = rights or RightsPolicy.unknown()
        observations: list[ExternalObservationV1] = []
        for row in rows:
            provider_asset = row.get("asset")
            if provider_asset not in mappings or not isinstance(row.get("time"), str):
                raise ProviderError(FailureKind.SCHEMA_ERROR, "unknown asset or missing time")
            observed_at = datetime.fromisoformat(row["time"].replace("Z", "+00:00")).astimezone(UTC)
            for metric in metrics:
                if metric not in row:
                    state, value = CapabilityState.NOT_SUPPORTED, None
                elif row[metric] is None:
                    state, value = CapabilityState.MISSING, None
                else:
                    state = CapabilityState.SUPPORTED
                    try:
                        value = float(row[metric])
                    except (TypeError, ValueError) as exc:
                        raise ProviderError(FailureKind.SCHEMA_ERROR, "non-numeric metric") from exc
                observations.append(
                    ExternalObservationV1(
                        provider=self.name,
                        dataset="asset-metrics",
                        canonical_asset_id=mappings[provider_asset],
                        provider_asset_id=provider_asset,
                        metric=metric,
                        metric_version="api-v4",
                        value=value,
                        observed_at=observed_at,
                        received_at=received_at,
                        pit_grade=PITGrade.RECONSTRUCTED
                        if historical_request
                        else PITGrade.RECEIPT_PIT,
                        rights=rights,
                        collection_run_id=run_id,
                        collection_run_revision=run_revision,
                        unit=None,
                        capability_state=state,
                        metadata={
                            "provider_status": row.get(metric + "-status"),
                            "provider_status_time": row.get(metric + "-status-time"),
                        },
                    )
                )
        return observations
