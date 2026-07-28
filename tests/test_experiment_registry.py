"""Experiment Registry (jul/2026) — schema formal de trials.json, governança de
identidade (mudar params = trial nova, N+1) e fechamento automático do Sharpe
por-trade pelo backtest.

Offline: trials em arquivo temporário; o trials.json REAL do repositório também
é validado contra o schema (o desconto do DSR só é honesto se todo campo do
denominador for interpretável).
"""
import json
from typing import TypedDict

import pytest

from GarimpoInvestimentos.analyzers.trials import (
    TRIALS_PATH, PowerAttestationMissingError, attestation_path_for,
    load_trials, register_trial, validate_trials)
from GarimpoInvestimentos.analyzers.backtest import (
    close_trial_sharpes, close_h6_inverted_signal, H6_TRIAL_NAME)

PARAMS = {"fonte": "dpl:fallback", "juiz": "gemini:g", "horizonte_dias": 7}


class _NoGateKwargs(TypedDict):
    power_attestation: bool


# Mecânica do registro é testada com bypass EXPLÍCITO da trava de poder
# (power_attestation=False) — a trava tem testes próprios no fim do arquivo.
_NOGATE: _NoGateKwargs = {"power_attestation": False}


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
    register_trial("t-a", params=PARAMS, path=p, **_NOGATE)
    original = load_trials(p)[0]["registered_at"]
    register_trial("t-a", params=PARAMS, sharpe=0.12, notes="maturou", path=p)  # update: sem trava
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
        register_trial("t-a", params=PARAMS, path=p, **_NOGATE)
        with pytest.raises(ValueError, match="tentativa nova"):
            register_trial("t-a", params={**PARAMS, "horizonte_dias": 30}, path=p, **_NOGATE)
        assert load_trials(p)[0]["params"] == PARAMS  # nada gravado


def test_registro_invalido_nao_e_gravado(tmp_path):
    p = tmp_path / "trials.json"
    with pytest.raises(ValueError, match="schema"):
        register_trial("t-a", params={}, path=p, **_NOGATE)  # params vazio
    assert load_trials(p) == []


def test_campos_opcionais_do_registry_sao_gravados(tmp_path):
    p = tmp_path / "trials.json"
    register_trial("t-a", params=PARAMS, path=p, **_NOGATE,
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
    register_trial("v2-teste", params=PARAMS, path=p, **_NOGATE)
    enriched = [_pred(80, 2.0), _pred(75, -1.0), _pred(90, 3.0),
                _pred(40, 9.9)]  # abaixo do limiar: fora da estratégia
    updated = close_trial_sharpes(enriched, 7, trials_path=p, threshold=70)
    assert "v2-teste" in updated
    t = load_trials(p)[0]
    assert t["sharpe"] == updated["v2-teste"]
    assert t["sharpe"] is not None and -10 < t["sharpe"] < 10


def test_backtest_nao_fecha_com_n_insuficiente(tmp_path):
    p = tmp_path / "trials.json"
    register_trial("v2-teste", params=PARAMS, path=p, **_NOGATE)
    enriched = [_pred(80, 2.0), _pred(75, -1.0)]  # n=2 < 3
    assert close_trial_sharpes(enriched, 7, trials_path=p, threshold=70) == {}
    assert load_trials(p)[0]["sharpe"] is None


def test_backtest_nunca_cria_trial_nova(tmp_path):
    """Criar tentativa é decisão humana (pré-registro) — estrato sem trial
    casada é ignorado, não inventado."""
    p = tmp_path / "trials.json"
    register_trial("v2-teste", params=PARAMS, path=p, **_NOGATE)
    enriched = [_pred(80, 2.0, fonte="dpl:consensus"),
                _pred(75, -1.0, fonte="dpl:consensus"),
                _pred(90, 3.0, fonte="dpl:consensus")]
    assert close_trial_sharpes(enriched, 7, trials_path=p, threshold=70) == {}
    assert len(load_trials(p)) == 1


def test_backtest_divide_eras_entre_trial_encerrada_e_sucessora(tmp_path):
    """Duas trials com os MESMOS params de casamento (fonte, horizonte) — caso
    real: v2-dpl-gemini-h7 encerrada e v2-dpl-multi-h7 sucessora. Cada previsão
    matura a trial VIGENTE na sua data (fronteira = registered_at da sucessora);
    a sucessora nunca herda dados do juiz anterior."""
    import json as _json
    from datetime import datetime
    p = tmp_path / "trials.json"
    register_trial("era-1", params=PARAMS, path=p, **_NOGATE)
    register_trial("era-2", params=PARAMS, path=p, **_NOGATE)
    trials = _json.loads(p.read_text(encoding="utf-8"))
    trials[0]["registered_at"] = "2026-07-01T00:00:00Z"
    trials[1]["registered_at"] = "2026-07-10T00:00:00Z"
    p.write_text(_json.dumps(trials), encoding="utf-8")

    def _dated(score, var, day):
        return {**_pred(score, var), "pred_date": datetime(2026, 7, day)}

    enriched = [_dated(80, 2.0, 2), _dated(75, -1.0, 3), _dated(90, 3.0, 5),   # era 1
                _dated(85, -2.0, 11), _dated(72, 4.0, 12), _dated(88, 1.0, 13)]  # era 2
    updated = close_trial_sharpes(enriched, 7, trials_path=p, threshold=70)
    assert set(updated) == {"era-1", "era-2"}
    assert updated["era-1"] != updated["era-2"]  # cada era com os próprios dados


# --- H6 (sinal invertido) — mecanismo separado, anti-data-snooping ------------

H6_PARAMS = {"fonte": "reserved:h6-inversao-sinal", "horizonte_dias": 7}


def _dated_score(score, var, day, fonte="dpl:fallback"):
    from datetime import datetime
    return {"score": score, "var_d7_pct": var, "fonte": fonte,
            "pred_date": datetime(2026, 7, day)}


def test_h6_sem_trial_registrada_e_no_op(tmp_path):
    p = tmp_path / "trials.json"
    assert close_h6_inverted_signal([_dated_score(10, 5.0, 25)], 7,
                                    trials_path=p, threshold=60) is None


def test_h6_ignora_dado_anterior_ao_registro_mesmo_com_score_baixo(tmp_path):
    """A trava anti-data-snooping: dado ANTES do registered_at da H6 nunca
    conta, mesmo que o score já bata o limiar invertido — senão a mesma
    amostra que inspirou a hipótese validaria a própria hipótese."""
    from datetime import datetime as _dt
    p = tmp_path / "trials.json"
    register_trial(H6_TRIAL_NAME, params=H6_PARAMS, path=p, **_NOGATE)
    trials = json.loads(p.read_text(encoding="utf-8"))
    trials[0]["registered_at"] = "2026-07-20T00:00:00Z"
    p.write_text(json.dumps(trials), encoding="utf-8")

    anterior = [_dated_score(10, 5.0, d) for d in (10, 11, 12)]  # antes do registro
    assert close_h6_inverted_signal(anterior, 7, trials_path=p, threshold=60) is None
    assert load_trials(p)[0]["sharpe"] is None


def test_h6_matura_com_dado_posterior_ao_registro_e_score_baixo(tmp_path):
    p = tmp_path / "trials.json"
    register_trial(H6_TRIAL_NAME, params=H6_PARAMS, path=p, **_NOGATE)
    trials = json.loads(p.read_text(encoding="utf-8"))
    trials[0]["registered_at"] = "2026-07-20T00:00:00Z"
    p.write_text(json.dumps(trials), encoding="utf-8")

    # score <= 40 (100 - limiar 60) = sinal invertido forte; depois do registro
    posterior = [_dated_score(35, v, d) for v, d in ((3.0, 21), (1.5, 22), (4.2, 23))]
    sharpe = close_h6_inverted_signal(posterior, 7, trials_path=p, threshold=60)
    assert sharpe is not None
    t = load_trials(p)[0]
    assert t["sharpe"] == sharpe
    assert t["params"] == H6_PARAMS  # identidade preservada (update, não trial nova)


def test_h6_ignora_score_acima_do_limiar_invertido(tmp_path):
    p = tmp_path / "trials.json"
    register_trial(H6_TRIAL_NAME, params=H6_PARAMS, path=p, **_NOGATE)
    trials = json.loads(p.read_text(encoding="utf-8"))
    trials[0]["registered_at"] = "2026-07-20T00:00:00Z"
    p.write_text(json.dumps(trials), encoding="utf-8")

    # score 80 > 40 (limiar invertido) — não é sinal invertido forte
    posterior = [_dated_score(80, 3.0, d) for d in (21, 22, 23)]
    assert close_h6_inverted_signal(posterior, 7, trials_path=p, threshold=60) is None


def test_h6_ignora_fonte_diferente_da_coleta_real():
    p_trials = json.loads(TRIALS_PATH.read_text(encoding="utf-8"))
    assert any(t["name"] == H6_TRIAL_NAME for t in p_trials), (
        "trial H6 sumiu do trials.json real — deveria estar pré-registrada")
    # fonte reservada do PRÓPRIO registro nunca aparece em predictions.fonte
    # real (direct/dpl:fallback/dpl:consensus) — dado com essa fonte não conta.
    h6 = next(t for t in p_trials if t["name"] == H6_TRIAL_NAME)
    assert h6["params"]["fonte"].startswith("reserved:")
    posterior = [_dated_score(10, 5.0, 25, fonte=h6["params"]["fonte"])]
    assert close_h6_inverted_signal(posterior, 7, threshold=60) is None


def test_h6_no_repositorio_real_mantem_o_fonte_reservado():
    """A trial H6 do trials.json real deve continuar com o fonte reservado —
    se alguém mudar isso sem querer, ela passaria a casar com dado real sem
    a trava explícita desta função (o casamento genérico do
    close_trial_sharpes também não a pegaria, mas por acidente, não desenho).

    **Errata de 2026-07-28.** Este teste exigia `sharpe is None`, com o
    comentário "ainda não amadureceu — sem dado genuinamente novo". Ficou
    obsoleto em `556f5ad` (2026-07-20), que implementou
    `close_h6_inverted_signal` e a ligou ao ciclo noturno **de propósito**: a
    H6 passa a amadurecer sozinha, mas SÓ com previsões posteriores ao
    `registered_at` dela, que é a trava anti-data-snooping que o casamento
    genérico não tem.

    O teste não foi atualizado junto e continuou verde por acidente, enquanto
    não havia n≥3 de dado posterior. Quebrou em 2026-07-28, quando o contador
    passou — ou seja, avisou de uma mudança de desenho **oito dias depois**
    dela ter acontecido. O que ele deve guardar é o `fonte` reservado, não a
    ausência de número.
    """
    trials = json.loads(TRIALS_PATH.read_text(encoding="utf-8"))
    h6 = next(t for t in trials if t["name"] == H6_TRIAL_NAME)
    assert h6["params"] == {"fonte": "reserved:h6-inversao-sinal", "horizonte_dias": 7}
    sharpe = h6["sharpe"]
    assert sharpe is None or isinstance(sharpe, (int, float)), \
        "sharpe da H6 so pode ser None ou numero produzido por close_h6_inverted_signal"


def test_load_rows_exclui_fallback_estrutural(tmp_path, monkeypatch):
    """0009: linha com llm_fallback=1 NÃO entra no backtest (é o fallback neutro,
    não análise real); o marcador legado no resumo continua coberto."""
    from GarimpoInvestimentos.analyzers import backtest
    from GarimpoInvestimentos.dpl import FeatureStore

    db = tmp_path / "fs.db"
    with FeatureStore(db) as store:
        store.write_predictions([
            {"ativo": "BITCOIN", "ts": "2026-07-10 10:00:00", "score": 72,
             "sentimento": "positivo", "resumo": "analise real", "price_usd": 50000,
             "juiz": "groq:m:h", "divergencia": 0, "fonte": "dpl:fallback",
             "input_degradado": 0, "llm_fallback": 0},
            {"ativo": "ETHEREUM", "ts": "2026-07-10 10:00:00", "score": 50,
             "sentimento": "neutro", "resumo": "erro na análise (fallback aplicado)",
             "price_usd": 3000, "juiz": "groq:m:h", "divergencia": 0,
             "fonte": "dpl:fallback", "input_degradado": 0, "llm_fallback": 1},
            {"ativo": "SOLANA", "ts": "2026-07-10 10:00:00", "score": 50,
             "sentimento": "neutro", "resumo": "erro na análise (fallback aplicado)",
             "price_usd": 150, "juiz": "gemini:m:h", "divergencia": 0,
             "fonte": "dpl:fallback", "input_degradado": None,
             "llm_fallback": None},  # legado: pré-0009, coberto pelo marcador
        ])
    monkeypatch.setattr(backtest, "FEATURE_STORE_DB", db)
    # redoma: sem absorver o CSV legado REAL da máquina no banco do teste
    monkeypatch.setattr(backtest, "migrate_csv_to_store", lambda store: 0)
    rows = backtest._load_rows()
    assert [r["ativo"] for r in rows] == ["bitcoin"]
    assert rows[0]["juiz"] == "groq:m:h"


def test_trials_json_real_permanece_intacto_em_dry_run(tmp_path):
    """Sanidade: o closure em path temporário jamais toca o registro real."""
    before = json.loads(TRIALS_PATH.read_text(encoding="utf-8"))
    p = tmp_path / "trials.json"
    register_trial("x", params=PARAMS, path=p, **_NOGATE)
    close_trial_sharpes([_pred(80, 1.0)] * 3, 7, trials_path=p, threshold=70)
    after = json.loads(TRIALS_PATH.read_text(encoding="utf-8"))
    assert before == after


# --- trava de poder (harness ↔ registry, core v1.1.0) ---------------------------

def test_trial_nova_sem_atestado_e_barrada(tmp_path):
    p = tmp_path / "trials.json"
    with pytest.raises(PowerAttestationMissingError, match="controle positivo"):
        register_trial("t-a", params=PARAMS, path=p)
    assert load_trials(p) == []


def test_atestado_real_do_repositorio_existe_e_e_valido():
    """O registro REAL só aceita trials novas porque scripts/attest_harness.py
    provou (harness oficial) que o juiz GO/NO-GO detecta edge plantado e
    rejeita ruído. Se este arquivo sumir, criar trial nova volta a ser erro —
    comportamento desejado."""
    ap = attestation_path_for(TRIALS_PATH)
    assert ap.exists(), f"atestado ausente: {ap} — rode scripts/attest_harness.py"
    rec = json.loads(ap.read_text(encoding="utf-8"))
    assert rec.get("passed_at") and rec.get("edge_verdict") == "GO"


def test_juiz_go_nogo_tem_poder():
    """Re-executa o controle positivo em memória (determinístico, seeds fixos):
    o juiz do backtest_v3 (PSR>=0.80 & IC_lower>0) detecta skill plantado e não
    fabrica GO em ruído. É o mesmo braço que emitiu o atestado."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "attest_harness",
        Path(__file__).resolve().parents[1] / "scripts" / "attest_harness.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from predictor_core.testing.harness import assert_pipeline_has_power
    assert assert_pipeline_has_power(
        mod.judge_go_nogo, mod.edge_series, mod.noise_series, edge_verdict="GO")
