"""Calibração por juiz (B11a): descritivo sobre dado existente.

O ponto sensível deste módulo não é a aritmética — é o que ele se RECUSA a
reportar. A partição de juízes é fixa por ativo, então não existe observação
pareada; qualquer "correlação entre juízes" seria pareamento inventado.
"""

import pytest

from GarimpoInvestimentos.analyzers.judge_calibration import (
    calibration_by_judge,
    render,
    spread,
)


def _row(juiz, score, ativo="bitcoin"):
    return {"juiz": juiz, "score": score, "ativo": ativo}


def test_agrupa_pelo_PROVEDOR_e_nao_pelo_carimbo_inteiro():
    """O carimbo é provider:modelo:hash — um bump de modelo mudaria o carimbo
    inteiro e fragmentaria o mesmo provedor em duas linhas."""
    stats = calibration_by_judge(
        [
            _row("gemini:gemini-2.5-flash:abc", 70.0),
            _row("gemini:gemini-3.0-pro:xyz", 50.0),
            _row("groq:llama:abc", 40.0),
        ]
    )
    assert [s.juiz for s in stats] == ["gemini", "groq"]
    assert stats[0].n == 2


def test_estatisticas_basicas():
    stats = calibration_by_judge(
        [_row("g:m:h", 40.0, "btc"), _row("g:m:h", 60.0, "eth"), _row("g:m:h", 80.0, "sol")],
        limiar=60.0,
    )
    (s,) = stats
    assert s.n == 3
    assert s.n_ativos == 3
    assert s.media == 60.0
    assert s.mediana == 60.0
    assert s.minimo == 40.0 and s.maximo == 80.0
    assert s.frac_acima_limiar == pytest.approx(2 / 3, abs=1e-4)  # 60 e 80
    assert s.frac_abaixo_invertido == pytest.approx(1 / 3, abs=1e-4)  # só o 40


def test_score_ausente_nao_derruba_nem_conta():
    stats = calibration_by_judge([_row("g:m:h", 50.0), {"juiz": "g:m:h", "ativo": "x"}])
    assert stats[0].n == 1


def test_juiz_vazio_vira_desconhecido_em_vez_de_sumir():
    """Linha sem carimbo é anomalia de dado; descartá-la em silêncio esconderia
    o problema, e agrupá-la com um juiz real contaminaria a régua dele."""
    stats = calibration_by_judge([{"juiz": "", "score": 50.0, "ativo": "x"}])
    assert stats[0].juiz == "desconhecido"


def test_spread_exige_dois_juizes():
    um = calibration_by_judge([_row("g:m:h", 50.0)])
    assert spread(um) is None
    dois = calibration_by_judge([_row("g:m:h", 30.0), _row("k:m:h", 70.0)])
    assert spread(dois)["amplitude_media"] == 40.0


def test_relatorio_declara_que_concordancia_nao_e_computavel():
    """Trava de honestidade: se alguém futuramente adicionar uma 'correlação
    entre juízes' calculada por pareamento inventado, este teste continua
    exigindo que a limitação real esteja escrita no relatório."""
    texto = render(calibration_by_judge([_row("g:m:h", 50.0), _row("k:m:h", 60.0)]), 60.0)
    assert "NAO e computavel" in texto
    assert "particao e fixa" in texto
    assert "B11b" in texto


def test_render_com_amostra_vazia_nao_quebra():
    assert "sem previsoes" in render(calibration_by_judge([]), 60.0)
