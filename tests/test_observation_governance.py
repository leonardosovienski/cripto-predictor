import json
from pathlib import Path

import pytest
import yaml

from GarimpoInvestimentos.governance import (
    BINANCE_OBSERVATION_ACTIVATION,
    BINANCE_OBSERVATION_PLAN,
    load_observation_activation,
    load_observation_plan,
)


def test_observation_activation_is_valid_and_collection_only():
    activation = load_observation_activation()
    assert activation.state == "ACTIVE"
    assert activation.scientific_state == "COLLECTION_ONLY"
    assert activation.capital_authorized is False
    assert activation.watchdog.healthy is True


@pytest.mark.parametrize(
    ("field", "value"),
    [("scientific_state", "GO"), ("capital_authorized", True)],
)
def test_observation_activation_cannot_authorize_science_or_capital(
    tmp_path: Path, field: str, value
):
    raw = json.loads(BINANCE_OBSERVATION_ACTIVATION.read_text(encoding="utf-8"))
    raw[field] = value
    path = tmp_path / "invalid-activation.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        load_observation_activation(path)


def test_active_observation_plan_is_valid_and_sealed():
    plan = load_observation_plan()
    assert plan.scientific_state == "COLLECTION_ONLY"
    assert {metric.metric for metric in plan.metrics_under_observation} == {
        "funding_rate",
        "open_interest",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [("min_daily_coverage", -0.1), ("latency_p50_max_ms", -1), ("min_points", 0)],
)
def test_invalid_observation_metric_is_rejected(tmp_path: Path, field: str, value):
    raw = yaml.safe_load(BINANCE_OBSERVATION_PLAN.read_text(encoding="utf-8"))
    raw["metrics_under_observation"][0][field] = value
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        load_observation_plan(path)


def test_active_plan_mutation_breaks_checksum(tmp_path: Path):
    raw = BINANCE_OBSERVATION_PLAN.read_text(encoding="utf-8").replace(
        "min_daily_coverage: 0.99", "min_daily_coverage: 0.98", 1
    )
    path = tmp_path / "changed.yaml"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_observation_plan(path)
