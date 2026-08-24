"""Poder ao lado do veredito da H6 — sem tocar a definição congelada.

`h6_spearman_verdict` (a função que o gate usa de fato) continua byte-
idêntica: `h6_power_context`/`print_h6_power_context` vivem FORA do bloco que
`scripts/freeze_h6_definition.py` congela, deliberadamente. Este arquivo
prova as duas coisas: que o contexto de poder funciona, e que ele não força
um re-freeze — a barreira mais importante aqui é a última, porque é a que
qualquer edição futura descuidada poderia quebrar em silêncio.
"""

from __future__ import annotations

from GarimpoInvestimentos.analyzers.backtest import (
    H6_PUBLISHED_POWER_TABLE,
    h6_power_context,
    print_h6_power_context,
)


def test_abaixo_de_30_nao_ha_ponto_tabulado():
    assert h6_power_context(0) is None
    assert h6_power_context(29) is None


def test_exatamente_no_primeiro_ponto_tabulado():
    ctx = h6_power_context(30)
    assert ctx["n_referencia"] == 30
    assert ctx["poder"] == H6_PUBLISHED_POWER_TABLE[30]


def test_entre_dois_pontos_usa_o_menor_conservador():
    """n=45 fica entre as linhas 30 e 60 da tabela publicada; usar 60 aqui
    superestimaria o poder que o n atual de fato tem."""
    ctx = h6_power_context(45)
    assert ctx["n_referencia"] == 30


def test_acima_do_maior_ponto_tabulado_usa_o_maior():
    ctx = h6_power_context(10_000)
    assert ctx["n_referencia"] == 500
    assert ctx["poder"] == H6_PUBLISHED_POWER_TABLE[500]


def test_tabela_bate_com_o_b12_publicado_em_hypotheses_md():
    """As leituras vem de docs/HYPOTHESES.md B12 (medido em 2026-08-21) — não
    recalculadas aqui. Se esta tabela divergir do documento, uma diverge da
    outra e ninguém percebe; trava o número, não só a forma."""
    assert H6_PUBLISHED_POWER_TABLE[30][0.2] == 0.147
    assert H6_PUBLISHED_POWER_TABLE[120][0.3] == 0.827
    assert H6_PUBLISHED_POWER_TABLE[250][0.2] == 0.813
    assert H6_PUBLISHED_POWER_TABLE[500][0.1] == 0.653


def test_print_sem_erro_abaixo_do_gate(capsys):
    resultado = print_h6_power_context(6, "aguardando n>=30 (n=6)")
    assert resultado is None
    assert capsys.readouterr().out == ""


def test_print_mostra_rho_02_e_03(capsys):
    resultado = print_h6_power_context(45, "RUIDO (IC cruza 0)")
    saida = capsys.readouterr().out
    assert resultado is not None
    assert "14,7%" not in saida  # numeros vem formatados em %, nao em virgula pt-BR
    assert "rho=0,2" in saida and "rho=0,3" in saida
    assert "lembrete" in saida  # RUIDO deve disparar o aviso de poder


def test_print_valida_nao_dispara_lembrete_de_ruido(capsys):
    print_h6_power_context(45, "validado (IC nao cruza 0)")
    saida = capsys.readouterr().out
    assert "lembrete" not in saida


def test_h6_spearman_verdict_continua_confere_com_o_snapshot_congelado():
    """A barreira que de fato importa: rodar o proprio mecanismo de governanca
    e confirmar que o codigo de h6_spearman_verdict (e close_h6_inverted_
    signal) nao mudou um byte. Roda o script real em vez de reimplementar a
    logica de hash aqui — o que importa e' o script continuar dizendo OK."""
    from scripts.freeze_h6_definition import main as freeze_main

    assert freeze_main(["--check"]) == 0
