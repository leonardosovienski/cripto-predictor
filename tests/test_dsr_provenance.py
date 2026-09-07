import json

import pytest

from GarimpoInvestimentos.analyzers.trials import (
    DeflationNotEstimableError,
    PowerAttestationMissingError,
    load_trials,
    register_trial,
    registry_deflated_sharpe_ratio,
)


def test_ledger_historico_nao_produz_dsr_com_unidades_misturadas():
    with pytest.raises(DeflationNotEstimableError, match="base/unidade"):
        registry_deflated_sharpe_ratio(
            [0.01, -0.01, 0.02], load_trials(), sharpe_basis="per_trade_d7"
        )


def test_bases_compativeis_preservam_tentativas_sem_sharpe_no_n():
    trials = [
        {"name": "a", "sharpe": 0.3, "params": {"sharpe_basis": "per_trade_d7"}},
        {"name": "b", "sharpe": -0.1, "params": {"sharpe_basis": "per_trade_d7"}},
        {"name": "c", "sharpe": None, "params": {}},
    ]
    result = registry_deflated_sharpe_ratio(
        [0.01, -0.01, 0.02], trials, sharpe_basis="per_trade_d7"
    )
    assert result["n_trials"] == 3 and result["n_sharpes"] == 2


def test_update_recusa_atestado_expirado_sem_tocar_trial(tmp_path, registry_attestation):
    path = tmp_path / "trials.json"
    kwargs = registry_attestation(path)
    register_trial("synthetic", params={"h": 7}, path=path, **kwargs)
    before = path.read_bytes()
    att = kwargs["power_attestation"]
    record = json.loads(att.read_text(encoding="utf8"))
    record["expires_at"] = "2000-01-01T00:00:00Z"
    att.write_text(json.dumps(record), encoding="utf8")
    with pytest.raises(PowerAttestationMissingError, match="expirado"):
        register_trial("synthetic", params={"h": 7}, sharpe=0.5, path=path)
    assert path.read_bytes() == before
