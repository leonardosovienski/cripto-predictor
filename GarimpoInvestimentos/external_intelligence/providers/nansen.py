"""Nansen adapter with explicit chains, credits and conservative PIT."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any

from predictor_core.kernel.net import get_http_client, with_retry

from GarimpoInvestimentos.external_intelligence.contracts import (
    CapabilityState,
    ExternalObservationV1,
    FailureKind,
    PITGrade,
    RightsPolicy,
)
from GarimpoInvestimentos.external_intelligence.providers.common import ProviderError, RequestBudget


class NansenAdapter:
    name = "nansen"
    base_url = "https://api.nansen.ai/api/v1"

    def __init__(self, *, supported_chains: set[str], credit_budget: RequestBudget):
        self.supported_chains = frozenset(supported_chains)
        self.credit_budget = credit_budget

    def require_capability(
        self, *, chain: str, canonical_asset_id: str, provider_asset_id: str
    ) -> None:
        if chain not in self.supported_chains:
            raise ProviderError(FailureKind.UNSUPPORTED, f"Nansen chain unsupported: {chain}")
        if canonical_asset_id == "crypto:btc" and provider_asset_id.lower() == "wbtc":
            raise ProviderError(FailureKind.UNSUPPORTED, "BTC cannot be substituted with WBTC")

    def authorize_request(self, rights: RightsPolicy, *, credits: int = 5) -> None:
        if not rights.local_research:
            raise ProviderError(FailureKind.RESTRICTION, "Nansen local research rights unapproved")
        self.credit_budget.consume(credits)

    @with_retry()
    async def post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        api_key: str,
        rights: RightsPolicy,
        credits: int = 5,
    ) -> dict[str, Any]:
        if not api_key:
            raise ProviderError(FailureKind.AUTHENTICATION, "Nansen API key missing")
        self.authorize_request(rights, credits=credits)
        async with get_http_client() as client:
            response = await client.post(
                self.base_url + "/" + path.lstrip("/"),
                headers={"apikey": api_key, "Content-Type": "application/json"},
                json=body,
            )
        status_kinds = {
            401: FailureKind.AUTHENTICATION,
            402: FailureKind.CREDIT_EXHAUSTED,
            403: FailureKind.AUTHORIZATION,
            429: FailureKind.RATE_LIMIT,
        }
        if response.status_code in status_kinds:
            raise ProviderError(status_kinds[response.status_code], "Nansen request refused")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ProviderError(FailureKind.SCHEMA_ERROR, "Nansen response schema")
        return payload

    def normalize_historical_holdings(
        self,
        rows: list[dict[str, Any]],
        *,
        chain: str,
        mappings: dict[str, str],
        received_at: datetime,
        run_id: str,
        run_revision: str,
        rights: RightsPolicy,
    ) -> list[ExternalObservationV1]:
        result = []
        for row in rows:
            token = row.get("token_symbol") or row.get("symbol")
            date = row.get("date")
            if token not in mappings or not isinstance(date, str):
                raise ProviderError(FailureKind.SCHEMA_ERROR, "Nansen holding identity/date")
            self.require_capability(
                chain=chain,
                canonical_asset_id=mappings[token],
                provider_asset_id=token,
            )
            observed = datetime.combine(datetime.fromisoformat(date).date(), time.max, tzinfo=UTC)
            for metric in ("value_usd", "balance_24h_percent_change", "holders_count"):
                value = row.get(metric)
                state = CapabilityState.SUPPORTED if value is not None else CapabilityState.MISSING
                result.append(
                    ExternalObservationV1(
                        provider=self.name,
                        dataset="smart-money/historical-holdings",
                        canonical_asset_id=mappings[token],
                        provider_asset_id=token,
                        metric=metric,
                        metric_version="api-v1",
                        value=value,
                        observed_at=observed,
                        received_at=received_at,
                        pit_grade=PITGrade.RECONSTRUCTED,
                        rights=rights,
                        collection_run_id=run_id,
                        collection_run_revision=run_revision,
                        unit="USD" if metric == "value_usd" else None,
                        dimensions={"chain": chain},
                        capability_state=state,
                        metadata={
                            "availability_policy": "receipt-only; documented typical processing window is not factual publication time"
                        },
                    )
                )
        return result
