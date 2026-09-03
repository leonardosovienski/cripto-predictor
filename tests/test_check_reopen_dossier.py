"""Gate técnico do bloco 19: reabertura de família congelada exige dossiê completo."""

import json

from scripts.check_reopen_dossier import (
    REQUIRED_FIELDS,
    check_reopen,
    load_frozen_families,
    validate_dossier,
)

COMPLETE_DOSSIER = {
    "previous_result": "CLOSED_NO_GO, PSR 0.445, líquido -0.09bps",
    "closure_reason": "custos eliminaram o edge bruto aparente",
    "new_information": "novo dataset com 2 anos adicionais de funding rate",
    "causal_reason": "hipótese de mecanismo distinta: squeeze de OI em altcoins, não BTC/ETH",
    "why_old_test_no_longer_answers_question": "universo testado antes era só BTC/ETH perp",
    "new_protocol": "trial nova registrada com critério de sucesso pré-declarado",
}


def test_familia_atual_esta_em_frozen_families():
    assert "funding_oi_hmm_v3" in load_frozen_families()


def test_familia_congelada_sem_dossie_e_bloqueada():
    assert check_reopen("funding_oi_hmm_v3", dossier_path=None) == 1


def test_familia_nao_congelada_passa_sem_dossie():
    assert check_reopen("familia_inexistente_qualquer", dossier_path=None) == 0


def test_dossie_completo_valida_sem_problemas():
    assert validate_dossier(COMPLETE_DOSSIER) == []


def test_dossie_com_campo_vazio_e_rejeitado():
    for field in REQUIRED_FIELDS:
        incompleto = dict(COMPLETE_DOSSIER)
        incompleto[field] = ""
        problems = validate_dossier(incompleto)
        assert any(field in p for p in problems)


def test_dossie_com_campo_ausente_e_rejeitado():
    for field in REQUIRED_FIELDS:
        incompleto = {k: v for k, v in COMPLETE_DOSSIER.items() if k != field}
        problems = validate_dossier(incompleto)
        assert any(field in p for p in problems)


def test_check_reopen_aceita_dossie_completo_em_disco(tmp_path):
    dossier_path = tmp_path / "dossier.json"
    dossier_path.write_text(json.dumps(COMPLETE_DOSSIER), encoding="utf-8")
    assert check_reopen("funding_oi_hmm_v3", dossier_path=dossier_path) == 0


def test_check_reopen_rejeita_dossie_incompleto_em_disco(tmp_path):
    incompleto = dict(COMPLETE_DOSSIER)
    del incompleto["causal_reason"]
    dossier_path = tmp_path / "dossier.json"
    dossier_path.write_text(json.dumps(incompleto), encoding="utf-8")
    assert check_reopen("funding_oi_hmm_v3", dossier_path=dossier_path) == 1
