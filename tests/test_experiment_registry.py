"""Experiment Registry (jul/2026) — schema formal de trials.json, governança de
identidade (mudar params = trial nova, N+1) e fechamento automático do Sharpe
por-trade pelo backtest.

Offline: trials em arquivo temporário; o trials.json REAL do repositório também
é validado contra o schema (o desconto do DSR só é honesto se todo campo do
denominador for interpretável).
"""
import json

import pytest

from GarimpoInvestimentos.analyzers.trials import (
    TRIALS_PATH, load_trials, register_trial, validate_trials)
from GarimpoInvestimentos.analyzers.backtest import close_trial_sharpes

PARAMS = {"fonte": "dpl:fallback", "juiz": "gemini:g", "horizonte_dias": 7}


# --- schema ------------------------------------------------------------------

def test_trials_json_do_repositorio_conforma_ao_schema():
    trials = load_trials(TRIALS_PATH)
    assert trials, "trials.json do repositório sumiu?"
    assert validate_trials(trials) == []


@pytest.mark.parametrize("mutacao,erro", [
    ({"name": "com espaço"}, "name inválido"),
    ({"registered_at": "2026-07-07"}, "registered_at inválido"),
    ({"params": {}}, "params precisa ser dict NÃO-vazio"),
    ({"sharpe": float("nan")}, "sharpe inválido"),
    ({"notes": 42}, "notes precisa ser str"),
    ({"train_period": ["só-início"]}, "train_period inválido"),
    ({"features_used": ["ok", 3]}, "features_used inválido"),
])
def test_schema_rejeita_campo_invalido(mutacao, erro):
    trial = {"name": "t1", "registered_at": "2026-07-07T00:00:00Z",
             "params": {"a": 1}, "sharpe": None, "notes": "", **mutacao}
    errs = validate_trials([trial])
    assert any(erro in e for e in errs), errs


def test_schema_rejeita_nome_duplicado():
    t = {"name": "dup", "registered_at": "2026-07-07T00:00:00Z",
         "params": {"a": 1}, "sharpe": None, "notes": ""}
    assert any("duplicado" in e for e in validate_trials([t, dict(t)]))


# --- governança de identidade (N+1) -------------------------------------------

def test_reexecucao_mesma_config_atualiza_sharpe_preservando_registro(tmp_path):
    p = tmp_path / "trials.json"
    register_trial("t-a", params=PARAMS, path=p)
    original = load_trials(p)[0]["registered_at"]
    register_trial("t-a", params=PARAMS, sharpe=0.12, notes="maturou", path=p)
    trials = load_trials(p)
    assert len(trials) == 1
    assert trials[0]["sharpe"] == 0.12
    assert trials[0]["registered_at"] == original  # identidade preservada


def test_mudar_params_de_trial_existente_e_erro():
    """Variação de hiperparâmetro escondida num 'update' fabricaria significância
    que o DSR não desconta — tem que ser trial NOVA."""
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "trials.json"
        register_trial("t-a", params=PARAMS, path=p)
        with pytest.raises(ValueError, match="tentativa nova"):
            register_trial("t-a", params={**PARAMS, "horizonte_dias": 30}, path=p)
        assert load_trials(p)[0]["params"] == PARAMS  # nada gravado


def test_registro_invalido_nao_e_gravado(tmp_path):
    p = tmp_path / "trials.json"
    with pytest.raises(ValueError, match="schema"):
        register_trial("t-a", params={}, path=p)  # params vazio
    assert load_trials(p) == []


def test_campos_opcionais_do_registry_sao_gravados(tmp_path):
    p = tmp_path / "trials.json"
    register_trial("t-a", params=PARAMS, path=p,
                   features_used=["rsi", "sma_200"],
                   train_period=["2026-01-01", "2026-06-30"],
                   test_period=["2026-07-01", "2026-07-31"])
    t = load_trials(p)[0]
    assert t["features_used"] == ["rsi", "sma_200"]
    assert t["test_period"][0] == "2026-07-01"


# --- fechamento automático do ciclo (backtest → trials.json) -------------------

def _pred(score, var, fonte="dpl:fallback"):
    return {"score": score, "var_d7_pct": var, "fonte": fonte}


def test_backtest_fecha_sharpe_da_trial_casada(tmp_path):
    p = tmp_path / "trials.json"
    register_trial("v2-teste", params=PARAMS, path=p)
    enriched = [_pred(80, 2.0), _pred(75, -1.0), _pred(90, 3.0),
                _pred(40, 9.9)]  # abaixo do limiar: fora da estratégia
    updated = close_trial_sharpes(enriched, 7, trials_path=p, threshold=70)
    assert "v2-teste" in updated
    t = load_trials(p)[0]
    assert t["sharpe"] == updated["v2-teste"]
    assert t["sharpe"] is not None and -10 < t["sharpe"] < 10


def test_backtest_nao_fecha_com_n_insuficiente(tmp_path):
    p = tmp_path / "trials.json"
    register_trial("v2-teste", params=PARAMS, path=p)
    enriched = [_pred(80, 2.0), _pred(75, -1.0)]  # n=2 < 3
    assert close_trial_sharpes(enriched, 7, trials_path=p, threshold=70) == {}
    assert load_trials(p)[0]["sharpe"] is None


def test_backtest_nunca_cria_trial_nova(tmp_path):
    """Criar tentativa é decisão humana (pré-registro) — estrato sem trial
    casada é ignorado, não inventado."""
    p = tmp_path / "trials.json"
    register_trial("v2-teste", params=PARAMS, path=p)
    enriched = [_pred(80, 2.0, fonte="dpl:consensus"),
                _pred(75, -1.0, fonte="dpl:consensus"),
                _pred(90, 3.0, fonte="dpl:consensus")]
    assert close_trial_sharpes(enriched, 7, trials_path=p, threshold=70) == {}
    assert len(load_trials(p)) == 1


def test_trials_json_real_permanece_intacto_em_dry_run(tmp_path):
    """Sanidade: o closure em path temporário jamais toca o registro real."""
    before = json.loads(TRIALS_PATH.read_text(encoding="utf-8"))
    p = tmp_path / "trials.json"
    register_trial("x", params=PARAMS, path=p)
    close_trial_sharpes([_pred(80, 1.0)] * 3, 7, trials_path=p, threshold=70)
    after = json.loads(TRIALS_PATH.read_text(encoding="utf-8"))
    assert before == after
