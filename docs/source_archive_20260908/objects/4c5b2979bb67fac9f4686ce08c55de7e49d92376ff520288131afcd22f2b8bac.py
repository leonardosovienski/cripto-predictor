import json

import pytest
from predictor_core.contracts import ScientificState

from GarimpoInvestimentos.governance import (
    FUNDING_OI_CHARTER,
    load_acquisition_charter,
    load_microstructure_charter,
)


def test_funding_oi_charter_is_complete_and_collection_only():
    charter = load_acquisition_charter()
    assert charter.initial_scientific_state is ScientificState.COLLECTION_ONLY
    assert charter.assets == ("BTCUSDT", "ETHUSDT")
    assert charter.latency_sla.p99_seconds == 60
    assert charter.quality_thresholds["minimum_coverage"] == 0.99


def test_charter_loader_rejects_missing_sla(tmp_path):
    value = json.loads(FUNDING_OI_CHARTER.read_text(encoding="utf-8"))
    value.pop("latency_sla")
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises((KeyError, ValueError)):
        load_acquisition_charter(path)


def test_binance_spot_microstructure_charter_is_public_collection_only():
    charter = load_microstructure_charter()
    assert charter.initial_scientific_state is ScientificState.COLLECTION_ONLY
    assert charter.source == "binance-spot"
    assert charter.assets == ("BTCUSDT", "ETHUSDT")
    assert "order_book_depth" in charter.metrics
