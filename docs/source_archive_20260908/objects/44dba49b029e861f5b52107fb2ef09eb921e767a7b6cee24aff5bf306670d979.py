from datetime import UTC, datetime

import pytest

from GarimpoInvestimentos.contracts import PredictionRequest
from GarimpoInvestimentos.providers import ResiliencePolicy
from GarimpoInvestimentos.services.inference import classify_scientific_eligibility


def test_request_rejects_naive_datetimes():
    with pytest.raises(ValueError, match="timezone-aware"):
        PredictionRequest(
            prediction_id="p",
            asset_id="btc",
            trial_id="locked",
            predicted_at=datetime.now(),
            data_as_of=datetime.now(UTC),
            matures_at=datetime.now(UTC),
            idempotency_key="k",
        )


def test_fallback_is_excluded_from_science():
    assert classify_scientific_eligibility(llm_fallback=True, degraded=False) == "EXCLUDED_DEGRADED"
    assert classify_scientific_eligibility(llm_fallback=False, degraded=False) == "ELIGIBLE"


def test_resilience_policy_is_fail_fast():
    with pytest.raises(ValueError):
        ResiliencePolicy(timeout_seconds=0)
