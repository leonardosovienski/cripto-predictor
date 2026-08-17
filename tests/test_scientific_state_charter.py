import json

import pytest

from GarimpoInvestimentos.governance import (
    SCIENTIFIC_STATE_CHARTER,
    load_scientific_state,
)


def test_scientific_state_freezes_no_go_and_fails_closed():
    state = load_scientific_state()
    assert state.hypotheses["H1"] == "CLOSED_NO_GO"
    assert state.hypotheses["H3"] == "CLOSED_NO_GO"
    assert state.hypotheses["H6"] == "COLLECTION_ONLY_IMMATURE"
    assert state.hypotheses["H7"] == "REGISTERED_NOT_ACTIVATED"
    assert "funding_oi_hmm_v3" in state.frozen_families
    assert not state.capital_authorized
    assert not state.leverage_authorized
    assert not state.llm_direct_trading_authorized


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("capital_authorized", True),
        ("leverage_authorized", True),
        ("llm_direct_trading_authorized", True),
    ],
)
def test_scientific_state_rejects_unsafe_authorization(tmp_path, field, value):
    payload = json.loads(SCIENTIFIC_STATE_CHARTER.read_text(encoding="utf-8"))
    payload[field] = value
    path = tmp_path / "state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        load_scientific_state(path)


def test_scientific_state_rejects_silent_v3_reopening(tmp_path):
    payload = json.loads(SCIENTIFIC_STATE_CHARTER.read_text(encoding="utf-8"))
    payload["hypotheses"]["H1"] = "ACTIVE"
    path = tmp_path / "state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="H1"):
        load_scientific_state(path)
