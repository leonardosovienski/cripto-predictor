from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from GarimpoInvestimentos.analyzers.opportunity_detector import detect_asset_opportunity
from GarimpoInvestimentos.external_intelligence.audit import temporal_perturbation_audit
from GarimpoInvestimentos.external_intelligence.collection import (
    collect_isolated,
    collection_status,
)
from GarimpoInvestimentos.external_intelligence.conditional import analyze
from GarimpoInvestimentos.external_intelligence.context import context_at
from GarimpoInvestimentos.external_intelligence.contracts import (
    AssetMapping,
    CapabilityState,
    CollectionRun,
    ExternalObservationV1,
    PITGrade,
    RightsPolicy,
)
from GarimpoInvestimentos.external_intelligence.ledger import attach_external_reference
from GarimpoInvestimentos.external_intelligence.providers.coinmetrics import CoinMetricsAdapter
from GarimpoInvestimentos.external_intelligence.providers.common import ProviderError, RequestBudget
from GarimpoInvestimentos.external_intelligence.providers.nansen import NansenAdapter
from GarimpoInvestimentos.external_intelligence.providers.santiment import SantimentAdapter
from GarimpoInvestimentos.external_intelligence.shadow import attach_shadow_context
from GarimpoInvestimentos.external_intelligence.store import ExternalIntelligenceStore
from GarimpoInvestimentos.jobs import job_config

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def run(run_id="run-1", received=T0 + timedelta(days=10), count=1):
    value = CollectionRun(
        collection_run_id=run_id,
        provider="coinmetrics",
        collector_version="fixture/1",
        started_at=received,
        finished_at=received + timedelta(seconds=1),
        status="SUCCEEDED",
        requests=1,
        observation_count=count,
    )
    return value


def observation(
    collection,
    *,
    value=1.0,
    observed=T0,
    received=T0 + timedelta(days=10),
    pit=PITGrade.RECONSTRUCTED,
):
    return ExternalObservationV1(
        provider="coinmetrics",
        dataset="asset-metrics",
        canonical_asset_id="crypto:btc",
        provider_asset_id="btc",
        metric="TxCnt",
        metric_version="api-v4",
        value=value,
        observed_at=observed,
        received_at=received,
        pit_grade=pit,
        rights=RightsPolicy(policy_version="fixture/1", local_research=True),
        collection_run_id=collection.collection_run_id,
        collection_run_revision=collection.collection_run_revision,
    )


def test_pit_semantics_and_asset_mapping_are_fail_closed():
    collection = run()
    item = observation(collection)
    assert item.effective_available_at == item.received_at
    with pytest.raises(ValueError, match="requires"):
        replace(item, pit_grade=PITGrade.PROVIDER_PIT)
    with pytest.raises(ValueError, match="BTC and WBTC"):
        AssetMapping("nansen", "crypto:btc", "WBTC", "1")
    assert RightsPolicy.unknown().cain_generate is False
    assert RightsPolicy.unknown().raw_export is False


def test_store_idempotency_revision_and_database_append_only(tmp_path):
    with ExternalIntelligenceStore(tmp_path / "external_intelligence.db") as store:
        first_run = run()
        store.record_collection_run(first_run)
        first = observation(first_run)
        assert store.add_observation(first) is True
        assert store.add_observation(first) is False
        revised = replace(first, value=2.0)
        assert revised.observation_id == first.observation_id
        assert revised.revision_id != first.revision_id
        assert store.add_observation(revised) is True
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            store.raw_connection_for_test().execute(
                "UPDATE external_observations SET value_json='3'"
            )


def test_recollection_is_same_semantic_revision_and_earliest_receipt_wins(tmp_path):
    with ExternalIntelligenceStore(tmp_path / "external_intelligence.db") as store:
        later_run = run("later", T0 + timedelta(days=20))
        earlier_run = run("earlier", T0 + timedelta(days=10))
        store.record_collection_run(later_run)
        store.record_collection_run(earlier_run)
        later = observation(later_run, received=T0 + timedelta(days=20))
        earlier = observation(earlier_run, received=T0 + timedelta(days=10))
        assert later.revision_id == earlier.revision_id
        assert store.add_observation(later) is True
        assert store.add_observation(earlier) is False
        assert store.observations_at(T0 + timedelta(days=15))[0]["revision_id"] == later.revision_id


def test_snapshot_determinism_separates_run_and_dataset_identity(tmp_path):
    with ExternalIntelligenceStore(tmp_path / "external_intelligence.db") as store:
        collection = run()
        store.record_collection_run(collection)
        store.add_observation(observation(collection))
        one = store.materialize_snapshot(T0 + timedelta(days=11), canonical_asset_id="crypto:btc")
        two = store.materialize_snapshot(T0 + timedelta(days=11), canonical_asset_id="crypto:btc")
        assert one == two
        assert collection.collection_run_revision != one["dataset_snapshot_revision"]


def test_coinmetrics_missing_is_not_zero_and_historical_is_reconstructed():
    collection = run(count=2)
    rows = [{"asset": "btc", "time": "2026-01-01T00:00:00Z", "TxCnt": None}]
    observations = CoinMetricsAdapter().normalize_asset_metrics(
        rows,
        metrics=("TxCnt", "SplyCur"),
        mappings={"btc": "crypto:btc"},
        received_at=T0 + timedelta(days=10),
        run_id=collection.collection_run_id,
        run_revision=collection.collection_run_revision,
        historical_request=True,
    )
    assert [item.capability_state for item in observations] == [
        CapabilityState.MISSING,
        CapabilityState.NOT_SUPPORTED,
    ]
    assert all(
        item.value is None and item.pit_grade is PITGrade.RECONSTRUCTED for item in observations
    )


def test_santiment_graphql_errors_and_restrictions():
    with pytest.raises(ProviderError) as error:
        SantimentAdapter.validate_graphql({"data": {"partial": True}, "errors": [{"message": "x"}]})
    assert error.value.kind.value == "partial_response"
    snapshots = SantimentAdapter().restriction_snapshots(
        [{"name": "social_volume_total", "isAccessible": True, "isRestricted": True}],
        received_at=T0,
    )
    assert snapshots[0].state is CapabilityState.RESTRICTED


def test_nansen_chain_credit_rights_and_btc_wbtc_guards():
    adapter = NansenAdapter(supported_chains={"ethereum", "solana"}, credit_budget=RequestBudget(5))
    with pytest.raises(ProviderError, match="rights"):
        adapter.authorize_request(RightsPolicy.unknown())
    allowed = RightsPolicy(policy_version="fixture", local_research=True)
    adapter.authorize_request(allowed, credits=5)
    with pytest.raises(ProviderError) as error:
        adapter.authorize_request(allowed)
    assert error.value.kind.value == "credit_exhausted"
    with pytest.raises(ProviderError, match="WBTC"):
        adapter.require_capability(
            chain="ethereum", canonical_asset_id="crypto:btc", provider_asset_id="WBTC"
        )


def test_context_temporal_audit_late_revision_and_transformation(tmp_path):
    with ExternalIntelligenceStore(tmp_path / "external_intelligence.db") as store:
        collection = run(count=3)
        store.record_collection_run(collection)
        store.add_observation(observation(collection, observed=T0, value=1.0))
        store.add_observation(observation(collection, observed=T0 + timedelta(days=1), value=2.0))
        late = observation(
            collection,
            observed=T0 + timedelta(days=1),
            received=T0 + timedelta(days=30),
            value=20.0,
        )
        store.add_observation(late)
        audit = temporal_perturbation_audit(
            store,
            asset="crypto:btc",
            cutoff=T0 + timedelta(days=15),
            provider="coinmetrics",
            dataset="asset-metrics",
            metric="TxCnt",
        )
        assert audit.status == "PASS"
        assert all(audit.checks.values())


def test_shadow_is_downstream_and_radar_signal_is_invariant(tmp_path):
    hard_data = {
        "return_1d": 0.04,
        "return_3d": 0.05,
        "return_7d": 0.07,
        "volume_ratio": 1.8,
        "volatility_7d": 0.03,
        "as_of": T0,
    }
    before = detect_asset_opportunity("BTCUSDT", hard_data)
    with ExternalIntelligenceStore(tmp_path / "external_intelligence.db") as store:
        context = context_at(store, asset="crypto:btc", decision_time=T0)
        shadow = attach_shadow_context(before, context, T0)
    after = detect_asset_opportunity("BTCUSDT", hard_data)
    assert before == after == shadow.canonical_signal


def test_provider_failure_isolation():
    async def ok():
        return [1]

    async def credits():
        raise ProviderError(
            kind=__import__(
                "GarimpoInvestimentos.external_intelligence.contracts", fromlist=["FailureKind"]
            ).FailureKind.CREDIT_EXHAUSTED,
            message="fixture",
        )

    results = asyncio.run(collect_isolated({"coinmetrics": ok, "nansen": credits}))
    assert collection_status(results) == "PARTIAL"
    assert {result.provider: result.status for result in results} == {
        "coinmetrics": "SUCCEEDED",
        "nansen": "CREDIT_EXHAUSTED",
    }


def test_conditional_analysis_is_explicitly_hypothesis_generating():
    result = analyze(
        [
            {"pit_valid": True, "high": True, "return_1d": 0.1},
            {"pit_valid": True, "high": False, "return_1d": -0.1},
            {"pit_valid": False, "high": True, "return_1d": 10.0},
        ],
        condition_id="fixture-high",
        condition=lambda row: row["high"],
        horizons=("return_1d",),
    )
    assert result.status == "HYPOTHESIS_GENERATING_ONLY"
    assert result.conditional_means["return_1d"] == pytest.approx(0.1)


def test_causal_ledger_bridge_uses_references_not_raw_payload(tmp_path):
    with ExternalIntelligenceStore(tmp_path / "external_intelligence.db") as store:
        context = context_at(store, asset="crypto:btc", decision_time=T0)
    original = {"signal": {"state": "WATCH"}}
    linked = attach_external_reference(original, context)
    assert original == {"signal": {"state": "WATCH"}}
    assert linked["external_evidence"]["external_dataset_snapshot_revision"]
    assert "observations" not in linked["external_evidence"]


def test_coinmetrics_job_reuses_predictor_ops_and_is_research_only(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIPTO_EXTERNAL_INTELLIGENCE_DB", str(tmp_path / "external.db"))
    config = job_config("external-coinmetrics")
    assert config.id == "cripto-external-coinmetrics"
    assert config.expected_artifact == tmp_path / "external.db"
    assert config.scientific_state == "COLLECTION_ONLY"
    assert config.capital_permission is False
