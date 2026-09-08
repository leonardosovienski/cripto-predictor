import json
from types import SimpleNamespace

from GarimpoInvestimentos.v3 import backtest_v3


def test_grid_registers_every_combination_before_execution(tmp_path, monkeypatch):
    trials = tmp_path / "trials.json"
    trials.write_text("[]", encoding="utf-8")
    trials.with_name("trials.harness_attestation.json").write_text(
        json.dumps({"pipeline_fingerprint": "fingerprint"}), encoding="utf-8"
    )
    calls = []
    executed_after = []

    def register(name, **kwargs):
        calls.append((name, kwargs))

    def run_wfa(**kwargs):
        executed_after.append(len(calls))
        return SimpleNamespace(
            final_verdict="NO-GO",
            aggregate_psr=0.1,
            aggregate_ic_ci_lower=-0.1,
            aggregate_max_dd=0.1,
            aggregate_sharpe=-0.2,
            folds=[],
        )

    monkeypatch.setattr(backtest_v3, "TRIALS_PATH", trials)
    monkeypatch.setattr(backtest_v3, "register_trial", register)
    monkeypatch.setattr(backtest_v3, "run_wfa", run_wfa)
    monkeypatch.setattr(backtest_v3, "emit_event", lambda *args, **kwargs: None)

    result = backtest_v3.run_threshold_grid("BTCUSDT", [0.5, 1.0], [0.6, 0.8])

    assert len(result.results) == 4
    assert executed_after[0] == 4
    assert len(calls) == 8  # quatro pré-registros + quatro atualizações
    assert {call[0] for call in calls[:4]} == {
        "v3-grid-btcusdt-fr0.5-conf0.6",
        "v3-grid-btcusdt-fr0.5-conf0.8",
        "v3-grid-btcusdt-fr1-conf0.6",
        "v3-grid-btcusdt-fr1-conf0.8",
    }
    assert all(call[1]["metric"] == "psr" for call in calls[:4])
