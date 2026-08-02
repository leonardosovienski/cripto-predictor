from GarimpoInvestimentos.contracts import OperationalStatus
from GarimpoInvestimentos.persistence import ArtifactStore, FeatureRepository, PredictionRepository
from GarimpoInvestimentos.plugin import CryptoPredictorPlugin


def test_plugin_missing_store_is_fail_closed(tmp_path):
    health = CryptoPredictorPlugin(tmp_path / "missing.db").health()
    assert health.status == OperationalStatus.SOURCE_UNAVAILABLE
    assert health.details["feature_store"] == "MISSING"


def test_persistence_interfaces_are_importable_contracts():
    assert PredictionRepository.__name__ == "PredictionRepository"
    assert FeatureRepository.__name__ == "FeatureRepository"
    assert ArtifactStore.__name__ == "ArtifactStore"
