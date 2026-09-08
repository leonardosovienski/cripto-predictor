from datetime import UTC, datetime, timedelta

from predictor_core.contracts import SourceQualityState

from GarimpoInvestimentos.dpl.derivatives import (
    SOURCE,
    funding_signal_points,
    oi_signal_points,
    persist_v3_derivatives,
)
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.quality_scorecard import calculate_and_persist_scorecard
from GarimpoInvestimentos.v3.collectors.funding_collector import FundingRecord
from GarimpoInvestimentos.v3.collectors.oi_collector import OIRecord

T0 = datetime(2026, 8, 1, tzinfo=UTC)
T0_MS = int(T0.timestamp() * 1000)


def test_v3_records_become_enriched_signal_points():
    ingested = T0 + timedelta(hours=2)
    funding = funding_signal_points(
        [FundingRecord("BTCUSDT", T0_MS, 0.0001, 100_000)], ingested_at=ingested
    )
    oi = oi_signal_points([OIRecord("BTCUSDT", T0_MS, 20_000, 2_000_000_000)], ingested_at=ingested)
    assert funding[0].require_enriched().metric == "funding_rate"
    assert {point.metric for point in oi} == {
        "open_interest_contracts",
        "open_interest_notional_usd",
    }
    assert all(point.source == SOURCE and len(point.content_hash) == 64 for point in funding + oi)


def test_derivatives_persist_bitemporally_and_scorecard_is_audited(tmp_path):
    ingested = T0 + timedelta(seconds=20)
    funding = [
        FundingRecord("BTCUSDT", T0_MS + hour * 3_600_000, 0.0001, 100_000) for hour in range(3)
    ]
    with FeatureStore(tmp_path / "features.db") as store:
        assert (
            persist_v3_derivatives(
                store, funding=funding, open_interest=[], ingested_at=ingested + timedelta(hours=2)
            )
            == 3
        )
        points = store.read_signals(SOURCE, "BTCUSDT:funding_rate")
        assert len(points) == 3 and all(point.is_enriched for point in points)
        result = calculate_and_persist_scorecard(
            store,
            points,
            source=SOURCE,
            window_start=T0,
            window_end=T0 + timedelta(hours=3),
            cadence_seconds=3600,
            successful_requests=3,
            total_requests=3,
            calculated_at=T0 + timedelta(hours=4),
        )
        # Historical backfill is intentionally degraded by the live-latency SLA;
        # it must not masquerade as a timely live collection.
        assert result.state is SourceQualityState.DEGRADED
        row = store._conn.execute("SELECT * FROM source_quality_scorecards").fetchone()
        assert row["scientific_state"] == "COLLECTION_ONLY"
