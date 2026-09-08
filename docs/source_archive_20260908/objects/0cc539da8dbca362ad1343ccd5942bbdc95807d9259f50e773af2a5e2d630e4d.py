import json

import pytest

from GarimpoInvestimentos.analyzers.trials import load_trials
from GarimpoInvestimentos.governance import (
    SCIENTIFIC_STATE_CHARTER,
    HypothesisStatus,
    load_scientific_state,
)


def test_scientific_state_freezes_no_go_and_fails_closed():
    state = load_scientific_state()
    assert state.hypotheses["H1"] == "CLOSED_NO_GO"
    assert state.hypotheses["H3"] == "CLOSED_NO_GO"
    assert state.hypotheses["H6"] == "CLOSED_NO_GO"
    assert state.hypotheses["H7"] == "REGISTERED_NOT_ACTIVATED"
    assert "funding_oi_hmm_v3" in state.frozen_families
    assert not state.capital_authorized
    assert not state.leverage_authorized
    assert not state.llm_direct_trading_authorized


def test_charter_real_cobre_exatamente_o_vocabulario_tipado():
    state = load_scientific_state()
    assert state.hypotheses["H4"] is HypothesisStatus.CLOSED_INSUFFICIENT_SAMPLE
    assert state.hypotheses["H6"] is HypothesisStatus.CLOSED_NO_GO
    assert state.hypotheses["H7"] is HypothesisStatus.REGISTERED_NOT_ACTIVATED
    assert state.hypotheses["H4"].is_closed
    assert state.hypotheses["H6"].is_closed
    # A serialização externa continua idêntica ao JSON versionado.
    dumped = state.model_dump(mode="json")
    original = json.loads(SCIENTIFIC_STATE_CHARTER.read_text(encoding="utf-8"))
    assert dumped["hypotheses"] == original["hypotheses"]


def test_scientific_state_rejeita_status_desconhecido_ou_typo(tmp_path):
    payload = json.loads(SCIENTIFIC_STATE_CHARTER.read_text(encoding="utf-8"))
    payload["hypotheses"]["H6"] = "COLLECTION_ONLY_IMATURE"
    path = tmp_path / "state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="HypothesisStatus|hypotheses.H6"):
        load_scientific_state(path)


def test_hypothesis_trials_mapeia_h1_para_a_trial_hmm_nao_para_v1_direct(tmp_path):
    """Regressão do rótulo confundido em 2026-08-19: 'H1' foi tratado como
    v1-direct-gemini-h7 (ancestral pré-protocolo sem rótulo formal) em vez de
    v3-hmm-funding-oi-fr90 (o H1 real, per docs/HYPOTHESES.md). O mapeamento
    explícito existe pra essa confusão nunca mais ser possível silenciosamente."""
    state = load_scientific_state()
    assert state.hypothesis_trials["H1"] == "v3-hmm-funding-oi-fr90"
    assert state.hypothesis_trials["H1"] != "v1-direct-gemini-h7"
    assert state.hypothesis_trials["H2"] == "v3-hmm-funding-oi-fr21"
    assert state.hypothesis_trials["H3"] == "v3-hmm-funding-oi-fr90-h48"
    assert state.hypothesis_trials["H4"] == "v2-dpl-gemini-h7"
    assert state.hypothesis_trials["H5"] == "v2-dpl-multi-h7"
    assert state.hypothesis_trials["H6"] == "h6-sinal-invertido-d7"


def test_hypothesis_trials_referencia_nomes_reais_de_trials_json():
    """As trials referenciadas (exceto H7, ainda não ativada) precisam existir
    de verdade em trials.json — senão o mapeamento vira só mais uma fonte
    de confusão, igual ao problema que ele foi criado pra resolver."""
    state = load_scientific_state()
    real_names = {t["name"] for t in load_trials()}
    for h_number, trial_name in state.hypothesis_trials.items():
        if h_number == "H7":
            continue  # ainda não ativada — não tem entrada em trials.json
        assert trial_name in real_names, f"{h_number} -> {trial_name} nao existe em trials.json"


def test_hypothesis_trials_exige_mesmas_chaves_de_hypotheses(tmp_path):
    payload = json.loads(SCIENTIFIC_STATE_CHARTER.read_text(encoding="utf-8"))
    del payload["hypothesis_trials"]["H2"]
    path = tmp_path / "state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="hypothesis_trials"):
        load_scientific_state(path)


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
