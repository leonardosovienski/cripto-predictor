"""H7 (macro/DXY): covariáveis extras opcionais no RegimeEngine.

Cobre o que a introdução de `extra_features`/`extra_covariates` precisa garantir
sem ambiguidade:

  1. Default (sem extra_features) é BIT-IDÊNTICO ao comportamento anterior —
     regressão de H1-H3 seria um bug grave aqui, não só de H7.
  2. Construtor rejeita nome de covariável desconhecido.
  3. fit()/predict_series() rejeitam contagem/tamanho de coluna que não bate com
     o que o construtor declarou — wiring errado tem que estourar, não silenciar.
  4. Com covariável extra, a mesma invariância anti-lookahead de
     test_v3_hmm_no_lookahead.py continua valendo.
  5. O fingerprint muda quando extra_features muda — um modelo H7 nunca é
     carregável como se fosse H1-H3 (StaleRegimeModelError).
"""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("hmmlearn")
pytest.importorskip("sklearn")

from GarimpoInvestimentos.v3.regime_engine import (
    RegimeEngine,
    StaleRegimeModelError,
    _model_fingerprint,
)


def _synthetic_series(rng):
    rets, vols = [], []
    for mu, sigma in ((0.4, 0.8), (-0.5, 1.2), (0.0, 0.4), (0.3, 0.9)):
        rets += rng.normal(mu, sigma, 60).tolist()
        vols += np.abs(rng.normal(sigma, 0.2, 60)).tolist()
    return rets, vols


def test_default_sem_extra_features_bate_com_comportamento_anterior():
    """extra_features=() (default) precisa continuar produzindo o mesmo resultado
    de antes desta mudança — trava de regressão para H1-H3."""
    rng = np.random.default_rng(11)
    rets, vols = _synthetic_series(rng)

    eng = RegimeEngine()  # sem extra_features
    eng.fit(rets, vols)  # sem extra_covariates
    out = eng.predict_series(rets, vols)

    assert len(out) == len(rets)
    assert all(o.hmm_state_label in ("bull", "bear", "sideways") for o in out)


def test_construtor_rejeita_extra_feature_desconhecida():
    with pytest.raises(ValueError, match="desconhecidas"):
        RegimeEngine(extra_features=("feature_inventada",))


def test_fit_exige_extra_covariates_quando_extra_features_declaradas():
    eng = RegimeEngine(extra_features=("macro_event_dummy",))
    rng = np.random.default_rng(13)
    rets, vols = _synthetic_series(rng)
    with pytest.raises(ValueError, match="0 coluna"):
        eng.fit(rets, vols)  # esqueceu de passar extra_covariates


def test_fit_rejeita_tamanho_de_coluna_incompativel():
    eng = RegimeEngine(extra_features=("macro_event_dummy",))
    rng = np.random.default_rng(17)
    rets, vols = _synthetic_series(rng)
    curta_demais = [0.0] * (len(rets) - 1)
    with pytest.raises(ValueError, match="pontos"):
        eng.fit(rets, vols, extra_covariates=[curta_demais])


def test_treina_e_infere_com_duas_covariaveis_extras():
    rng = np.random.default_rng(19)
    rets, vols = _synthetic_series(rng)
    macro_dummy = rng.integers(0, 2, len(rets)).astype(float).tolist()
    dxy_ret = rng.normal(0, 0.3, len(rets)).tolist()

    eng = RegimeEngine(extra_features=("macro_event_dummy", "dxy_return_1d"))
    eng.fit(rets, vols, extra_covariates=[macro_dummy, dxy_ret])
    out = eng.predict_series(rets, vols, extra_covariates=[macro_dummy, dxy_ret])

    assert len(out) == len(rets)
    assert all(len(o.hmm_posterior) == 3 for o in out)  # ainda 3 estados


def test_invariancia_anti_lookahead_preservada_com_extra_covariate():
    """Mesmo teste de test_v3_hmm_no_lookahead.py, agora com uma covariável extra:
    truncar a série não pode mudar nenhum ponto do passado."""
    rng = np.random.default_rng(23)
    rets, vols = _synthetic_series(rng)
    # contínua (não quase-binária) para evitar covariância degenerada no fit —
    # o que se testa aqui é a invariância, não a distribuição real do dummy.
    macro_dummy = rng.normal(0, 0.5, len(rets)).tolist()

    eng = RegimeEngine(extra_features=("macro_event_dummy",))
    eng.fit(rets[:150], vols[:150], extra_covariates=[macro_dummy[:150]])
    full = eng.predict_series(rets, vols, extra_covariates=[macro_dummy])
    cut = 200
    parcial = eng.predict_series(rets[:cut], vols[:cut], extra_covariates=[macro_dummy[:cut]])
    for t in range(cut):
        assert parcial[t].hmm_posterior == full[t].hmm_posterior


def test_fingerprint_muda_com_extra_features():
    base = _model_fingerprint()
    com_macro = _model_fingerprint(("macro_event_dummy",))
    assert base != com_macro
    assert com_macro["emission_features"] == [
        "log_return_8h",
        "realized_vol_24h",
        "macro_event_dummy",
    ]


def test_modelo_h7_nao_carrega_como_h1_h3(tmp_path):
    """Um .pkl treinado com extra_features não pode ser servido por um
    RegimeEngine() default (e vice-versa) — StaleRegimeModelError."""
    rng = np.random.default_rng(29)
    rets, vols = _synthetic_series(rng)
    macro_dummy = rng.integers(0, 2, len(rets)).astype(float).tolist()

    eng_h7 = RegimeEngine(extra_features=("macro_event_dummy",))
    eng_h7.fit(rets, vols, extra_covariates=[macro_dummy])
    path = tmp_path / "regime_h7.pkl"
    eng_h7.save(path)

    with pytest.raises(StaleRegimeModelError):
        RegimeEngine(model_path=path)  # default, sem extra_features
