from GarimpoInvestimentos.core.paths import CACHE_DIR, DATA_DIR
from GarimpoInvestimentos.v3 import backtest_v3, paper_report, paper_trader, pipeline, vision_ingest
from GarimpoInvestimentos.v3.collectors import binance_vision


def test_v3_mutable_paths_follow_configured_runtime_roots():
    assert vision_ingest._DATA_ROOT == DATA_DIR / "v3"
    assert pipeline._DATA_ROOT == DATA_DIR / "v3"
    assert paper_trader._DATA_ROOT == DATA_DIR / "v3"
    assert paper_report._DATA_ROOT == DATA_DIR / "v3"
    assert backtest_v3._DATA_ROOT == DATA_DIR / "v3"
    assert binance_vision._CACHE_DIR == CACHE_DIR / "v3" / "binance_vision"
