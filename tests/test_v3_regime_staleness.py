"""Guard de staleness do RegimeEngine (espelha o config_hash do wc-predictor).

Um .pkl é um modelo treinado sob um contrato (features de emissão + estrutura do
HMM). Se o contrato muda no código mas o cache é velho, servir esse modelo é um bug
silencioso. Estes testes não tocam hmmlearn — exercitam só save/load/fingerprint
com stand-ins picláveis (o import do RegimeEngine é lazy nas deps pesadas)."""
import pickle

import pytest

from GarimpoInvestimentos.v3.regime_engine import (
    MODEL_SCHEMA_VERSION,
    RegimeEngine,
    StaleRegimeModelError,
    _model_fingerprint,
)


class _DummyModel:
    """Stand-in piclável no lugar do GaussianHMM (definido no módulo p/ pickle)."""


def _engine_with_dummy():
    eng = RegimeEngine()
    eng._model = _DummyModel()
    eng._scaler = _DummyModel()  # pyright: ignore[reportAttributeAccessIssue] — stand-in piclável
    eng._state_map = {0: "bull", 1: "sideways", 2: "bear"}
    return eng


def test_save_stamps_fingerprint(tmp_path):
    p = tmp_path / "m.pkl"
    _engine_with_dummy().save(p)
    raw = pickle.loads(p.read_bytes())
    assert raw["fingerprint"] == _model_fingerprint()
    assert raw["fingerprint"]["schema_version"] == MODEL_SCHEMA_VERSION


def test_roundtrip_load_ok(tmp_path):
    p = tmp_path / "m.pkl"
    _engine_with_dummy().save(p)
    eng2 = RegimeEngine()
    eng2.load(p)   # fingerprint bate → não levanta
    assert eng2._state_map == {0: "bull", 1: "sideways", 2: "bear"}


def test_load_rejects_stale_fingerprint(tmp_path):
    p = tmp_path / "m.pkl"
    bad = {"model": _DummyModel(), "scaler": _DummyModel(), "state_map": {},
           "fingerprint": {"schema_version": 999, "n_states": 5,
                           "covariance_type": "diag", "emission_features": ["x"]}}
    p.write_bytes(pickle.dumps(bad))
    with pytest.raises(StaleRegimeModelError):
        RegimeEngine().load(p)


def test_load_warns_on_legacy_without_fingerprint(tmp_path, caplog):
    p = tmp_path / "legacy.pkl"
    legacy = {"model": _DummyModel(), "scaler": _DummyModel(), "state_map": {0: "bull"}}
    p.write_bytes(pickle.dumps(legacy))
    eng = RegimeEngine()
    with caplog.at_level("WARNING"):
        eng.load(p)   # legado: avisa mas carrega (migração não-destrutiva)
    assert eng._state_map == {0: "bull"}
    assert any("sem fingerprint" in r.message for r in caplog.records)
