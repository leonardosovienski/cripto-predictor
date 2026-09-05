"""DSR + registro de tentativas (governança estatística — risco nº 2 da auditoria).

Invariantes que importam: o benchmark E[max SR] é 0 sem seleção (1 tentativa /
variância nula) e CRESCE com o nº de tentativas — logo o DSR só pode cair quando
se tenta mais. Registrar de novo a mesma configuração NÃO conta tentativa nova.
"""

import math
import random

import pytest
from predictor_core.stats import probabilistic_sharpe_ratio

from GarimpoInvestimentos.analyzers.trials import (
    FrozenFamilyError,
    _reject_frozen_family,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    load_trials,
    register_trial,
)


def _returns(n=60, mean=0.01, sd=0.02, seed=7):
    rng = random.Random(seed)
    return [rng.gauss(mean, sd) for _ in range(n)]


# ---------- expected_max_sharpe ----------


def test_sem_selecao_benchmark_zero():
    assert expected_max_sharpe(1, 1.0) == 0.0  # 1 tentativa: nada a descontar
    assert expected_max_sharpe(10, 0.0) == 0.0  # tentativas idênticas: idem


def test_benchmark_cresce_com_tentativas_e_variancia():
    v = 0.04
    e2, e10, e100 = (expected_max_sharpe(n, v) for n in (2, 10, 100))
    assert 0 < e2 < e10 < e100  # mais tentativas → máx-por-sorte maior
    assert expected_max_sharpe(10, 0.16) > e10  # mais dispersão entre tentativas → idem


# ---------- deflated_sharpe_ratio ----------


def test_uma_tentativa_dsr_equivale_ao_psr():
    rets = _returns()
    d = deflated_sharpe_ratio(rets, [0.3])
    assert d["sr0"] == 0.0 and d["n_trials"] == 1
    assert d["dsr"] == probabilistic_sharpe_ratio(rets, benchmark_sharpe=0.0)


def test_mais_tentativas_so_reduzem_o_dsr():
    rets = _returns()
    um = deflated_sharpe_ratio(rets, [0.3])
    dez = deflated_sharpe_ratio(rets, [0.3, -0.1, 0.2, 0.05, -0.3, 0.4, 0.1, -0.2, 0.25, 0.0])
    assert dez["sr0"] > 0
    assert dez["dsr"] < um["dsr"]  # o desconto existe e aperta


def test_sharpes_nulos_ou_infinitos_contam_no_n_mas_nao_na_variancia():
    rets = _returns()
    d = deflated_sharpe_ratio(rets, [None, float("inf"), 0.3])
    assert d["n_trials"] == 3
    assert math.isfinite(d["sr0"])  # var só dos finitos (1 → var 0 → sr0 0)
    assert d["sr0"] == 0.0


# ---------- registro versionado ----------


def test_registro_roundtrip_e_dedup_por_nome(tmp_path):
    p = tmp_path / "trials.json"
    # criação usa bypass explícito da trava de poder (mecânica do registro;
    # a trava tem testes próprios em test_experiment_registry)
    register_trial("cfg-a", params={"h": 7}, sharpe=0.1, path=p, power_attestation=False)
    register_trial("cfg-b", params={"h": 30}, path=p, power_attestation=False)
    register_trial(
        "cfg-a", params={"h": 7}, sharpe=0.15, notes="reavaliada com mais n", path=p
    )  # mesma config → atualiza
    trials = load_trials(p)
    assert [t["name"] for t in trials] == ["cfg-a", "cfg-b"]  # não duplicou
    assert trials[0]["sharpe"] == 0.15
    assert trials[1]["sharpe"] is None


def test_registro_semeado_do_projeto_existe_e_tem_2_tentativas():
    trials = load_trials()  # o trials.json versionado
    names = [t["name"] for t in trials]
    assert "v1-direct-gemini-h7" in names and "v2-dpl-gemini-h7" in names


# ------------------------------------------------------------------ #
# Congelamento por FAMÍLIA (auditoria 2026-09-05)                     #
#                                                                     #
# Até esta correção o freeze era aplicado só por NOME de trial das    #
# hipóteses fechadas. Bastava um nome novo declarando a mesma família #
# para reparametrizar H1-H3 sem que nada barrasse.                    #
# ------------------------------------------------------------------ #


def test_familia_congelada_e_rejeitada_por_nome_novo():
    """O buraco concreto que a auditoria explorou: nome inédito, família congelada."""
    with pytest.raises(FrozenFamilyError, match="CONGELADA"):
        _reject_frozen_family(
            "v3-hmm-funding-oi-fr45-reopen",
            {"family": "funding_oi_hmm_v3", "mechanism": "reparametriza", "success_criterion": "x"},
            ("funding_oi_hmm_v3",),
        )


def test_familia_nao_congelada_passa():
    _reject_frozen_family("h10-nova", {"family": "basis-asymmetry"}, ("funding_oi_hmm_v3",))


def test_trial_sem_family_declarada_passa():
    """Ausência de `family` não é o que este guard controla — não inventa bloqueio."""
    _reject_frozen_family("h10-nova", {"mechanism": "x"}, ("funding_oi_hmm_v3",))


def test_charter_do_projeto_congela_a_familia_h1_h3():
    """Amarra o guard ao charter real: se `funding_oi_hmm_v3` sair de
    frozen_families, este teste cai junto."""
    from GarimpoInvestimentos.governance import load_scientific_state

    assert "funding_oi_hmm_v3" in load_scientific_state().frozen_families


def test_register_trial_bloqueia_familia_congelada_no_registro_real(tmp_path, monkeypatch):
    """Integração: o guard tem que estar ligado no caminho de escrita real,
    não só existir como função solta."""
    import GarimpoInvestimentos.analyzers.trials as trials_mod

    p = tmp_path / "trials.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(trials_mod, "TRIALS_PATH", p)

    with pytest.raises(FrozenFamilyError, match="funding_oi_hmm_v3"):
        trials_mod.register_trial(
            "v3-hmm-funding-oi-fr45-reopen",
            params={"family": "funding_oi_hmm_v3"},
            path=p,
        )
    # e nada foi escrito
    assert p.read_text(encoding="utf-8") == "[]"
