import zipfile
from pathlib import Path


def test_governance_assets_are_packaged_in_wheel():
    wheels = sorted(Path("dist").glob("cripto_predictor-*.whl"))
    if not wheels:
        return
    with zipfile.ZipFile(wheels[-1]) as wheel:
        names = set(wheel.namelist())
    assert "GarimpoInvestimentos/charters/funding_oi_v3.json" in names
    assert "GarimpoInvestimentos/observation_plans/binance_funding_oi_v1.yaml" in names
    assert (
        "GarimpoInvestimentos/observation_plans/activations/binance_funding_oi_v1_2026-08-09.json"
    ) in names
