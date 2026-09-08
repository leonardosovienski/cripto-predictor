"""DSL de fatores: prova de causalidade, não afirmação de causalidade.

Método herdado da auditoria de look-ahead do HMM (docs/AUDITORIA_HMM.md):
invariância sob mutilação do futuro, MAIS contraprova. A contraprova é o que
impede o teatro — um teste de leakage que passaria também para uma implementação
vazada não prova nada, e é exatamente o erro que a auditoria de 2026-08-19 pegou
em outros pontos deste projeto (asserção que não podia falhar).
"""

import random

import pytest

from GarimpoInvestimentos.analyzers import factor_dsl as F
from GarimpoInvestimentos.analyzers.factor_dsl import RecipeError, evaluate, from_recipe, to_recipe

# Um exemplar de CADA operação do vocabulário. Se alguém adicionar uma operação
# nova e não a incluir aqui, test_vocabulario_inteiro_coberto falha.
CASOS = {
    "feature": F.feature("x"),
    "const": F.const(2.0),
    "lag": F.lag(F.feature("x"), 3),
    "rolling_mean": F.rolling_mean(F.feature("x"), 5),
    "rolling_std": F.rolling_std(F.feature("x"), 5),
    "zscore": F.zscore(F.feature("x"), 5),
    "sign": F.sign(F.feature("x")),
    "add": F.add(F.feature("x"), F.feature("y")),
    "sub": F.sub(F.feature("x"), F.feature("y")),
    "mul": F.mul(F.feature("x"), F.feature("y")),
    "div": F.div(F.feature("x"), F.feature("y")),
    "composto": F.zscore(F.sub(F.feature("x"), F.lag(F.feature("x"), 1)), 7),
}


def _dados(n=60, seed=3):
    rng = random.Random(seed)
    return {"x": [rng.gauss(0, 1) for _ in range(n)], "y": [rng.gauss(5, 1) for _ in range(n)]}


def _mutila_futuro(dados, corte, seed=99):
    """Reescreve TUDO a partir de `corte` com valores completamente diferentes."""
    rng = random.Random(seed)
    return {k: v[:corte] + [rng.gauss(1000, 500) for _ in v[corte:]] for k, v in dados.items()}


@pytest.mark.parametrize("nome", sorted(CASOS))
def test_passado_e_invariante_a_mutilacao_do_futuro(nome):
    """A prova. Se qualquer operação olhasse para frente, o valor em algum
    índice < corte mudaria quando o futuro muda."""
    fator, dados, corte = CASOS[nome], _dados(), 30
    original = evaluate(fator, dados)
    mutilado = evaluate(fator, _mutila_futuro(dados, corte))
    assert original[:corte] == mutilado[:corte], f"{nome} vazou futuro para o passado"


def test_contraprova_o_teste_detecta_vazamento_de_verdade():
    """Sem isto, o teste acima poderia estar passando por acidente. Uma função
    deliberadamente NÃO-causal (média centrada, que olha adiante) tem que
    FALHAR o mesmo critério."""

    def media_centrada_vazada(serie, janela=5):
        meio = janela // 2
        out = []
        for i in range(len(serie)):
            bloco = serie[max(0, i - meio) : i + meio + 1]  # <-- lê i+meio: FUTURO
            out.append(sum(bloco) / len(bloco))
        return out

    dados, corte = _dados(), 30
    original = media_centrada_vazada(dados["x"])
    mutilado = media_centrada_vazada(_mutila_futuro(dados, corte)["x"])
    assert original[:corte] != mutilado[:corte], (
        "a contraprova NAO detectou vazamento — o teste de invariancia acima "
        "nao tem poder e todos os resultados dele sao vazios"
    )


def test_vocabulario_inteiro_coberto():
    """Trava contra operação nova entrar sem prova de causalidade."""
    assert set(F._BUILDERS) <= set(CASOS), (
        f"operacoes sem caso de teste de leakage: {set(F._BUILDERS) - set(CASOS)}"
    )


def test_janela_e_fechada_no_instante_atual():
    """rolling_mean(3) em [1..6] no índice 2 deve ser média de (1,2,3) — se
    fosse (2,3,4) a janela estaria adiantada em um passo."""
    dados = {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]}
    out = evaluate(F.rolling_mean(F.feature("x"), 3), dados)
    assert out[:2] == [None, None]  # warmup
    assert out[2] == pytest.approx(2.0)
    assert out[5] == pytest.approx(5.0)


def test_lag_desloca_para_tras():
    dados = {"x": [1.0, 2.0, 3.0, 4.0]}
    assert evaluate(F.lag(F.feature("x"), 1), dados) == [None, 1.0, 2.0, 3.0]


def test_warmup_bate_com_os_None_reais():
    """warmup existe para cortar o começo antes de medir edge; se divergir do
    número real de None, o n do backtest sairia inflado."""
    dados = _dados()
    for nome, fator in CASOS.items():
        out = evaluate(fator, dados)
        nones = 0
        for v in out:
            if v is None:
                nones += 1
            else:
                break
        assert nones == F.warmup(fator), f"{nome}: warmup={F.warmup(fator)} mas {nones} None"


def test_none_propaga_como_ausencia_e_nao_como_zero():
    """A DPL usa NULL == NaN para stale/ausente. Virar zero inventaria observação."""
    dados = {"x": [1.0, None, 3.0], "y": [1.0, 1.0, 1.0]}
    assert evaluate(F.add(F.feature("x"), F.feature("y")), dados) == [2.0, None, 4.0]


def test_divisao_por_zero_vira_none_e_nao_explode():
    dados = {"x": [1.0, 2.0], "y": [0.0, 2.0]}
    assert evaluate(F.div(F.feature("x"), F.feature("y")), dados) == [None, 1.0]


def test_zscore_com_desvio_zero_e_none():
    """Série constante: z indefinido. Devolver 0.0 afirmaria 'na média' com
    variância nula, o que é diferente de 'não dá pra dizer'."""
    assert evaluate(F.zscore(F.feature("x"), 3), {"x": [5.0] * 5})[2:] == [None, None, None]


def test_recipe_roundtrip_e_estavel():
    """Guardar a hipótese no registro append-only só tem significado se ela
    reconstrói exatamente."""
    for fator in CASOS.values():
        assert from_recipe(to_recipe(fator)) == fator


def test_operacao_desconhecida_e_erro_explicito():
    with pytest.raises(RecipeError, match="desconhecida"):
        from_recipe({"op": "olhar_o_futuro", "args": [{"op": "feature", "args": ["x"]}]})


def test_aridade_errada_e_erro_explicito():
    with pytest.raises(RecipeError, match="espera 2"):
        from_recipe({"op": "lag", "args": [{"op": "feature", "args": ["x"]}]})


def test_lag_zero_ou_negativo_e_recusado():
    with pytest.raises(RecipeError, match="k >= 1"):
        F.lag(F.feature("x"), 0)


def test_janela_menor_que_dois_e_recusada():
    with pytest.raises(RecipeError, match="janela"):
        F.rolling_mean(F.feature("x"), 1)


def test_feature_ausente_falha_em_vez_de_devolver_serie_vazia():
    with pytest.raises(RecipeError, match="feature ausente"):
        evaluate(F.feature("nao_existe"), {"x": [1.0]})


def test_recipe_nao_usa_eval():
    """Uma recipe é dado, não código. Se o construtor executasse a string, isto
    levantaria algo diferente de RecipeError."""
    with pytest.raises(RecipeError):
        from_recipe({"op": "__import__('os').system('echo vazou')", "args": []})
