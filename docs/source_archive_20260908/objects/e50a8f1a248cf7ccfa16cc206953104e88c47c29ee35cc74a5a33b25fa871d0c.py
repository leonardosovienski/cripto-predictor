"""Laço LLM-propõe-hipótese: o que importa testar aqui não é a aritmética, é o
CONJUNTO DE COISAS QUE ELE NÃO PODE FAZER.

Um laço que propõe hipóteses em volume é data snooping industrializado se as
travas falharem. Cada teste abaixo corresponde a uma trava declarada na
docstring do módulo.
"""

import asyncio
import json
from pathlib import Path

import pytest

from GarimpoInvestimentos.analyzers import hypothesis_loop as HL
from GarimpoInvestimentos.analyzers.hypothesis_loop import (
    ACCEPTED,
    REJECTED_DUPLICATE,
    REJECTED_INVALID,
    REJECTED_MALFORMED,
    Proposal,
    append_proposals,
    build_prompt,
    evaluate_proposal,
    load_proposals,
    parse_proposals,
    recipe_fingerprint,
    vocabulary_doc,
)

ROOT = Path(__file__).resolve().parents[1]
_ZSCORE = {"op": "zscore", "args": [{"op": "feature", "args": ["volume"]}, 5]}


def _parse(texto, **kw):
    kw.setdefault("proposed_at", "2026-08-21T00:00:00+00:00")
    kw.setdefault("proposer", "gemini")
    kw.setdefault("horizon_days", 7)
    return parse_proposals(texto, **kw)


# --- TRAVA 1: nunca registra trial ------------------------------------------


def test_modulo_nao_importa_nem_referencia_register_trial():
    """Estrutural de propósito: um teste comportamental só pegaria o caminho que
    ele exercita. Registrar trial sozinho tornaria o denominador do DSR algo que
    uma máquina infla à vontade."""
    fonte = (ROOT / "GarimpoInvestimentos" / "analyzers" / "hypothesis_loop.py").read_text(
        encoding="utf-8"
    )
    assert "register_trial" not in fonte
    assert "trials.json" not in fonte.replace("`trials.json`", "")  # só menção em prosa


# --- TRAVA 2: nunca emite veredito ------------------------------------------


def test_avaliacao_nao_contem_palavra_de_veredito():
    dados = {"volume": [float(i % 7) + 1 for i in range(40)]}
    retornos = [float((i * 13) % 5) - 2 for i in range(40)]
    ev = evaluate_proposal(
        Proposal("id", "t", "h", _ZSCORE, 7, "gemini", ACCEPTED), dados, retornos
    )
    texto = json.dumps(ev.__dict__, ensure_ascii=False).lower()
    for proibido in ("validado", "ruido", "go", "aprovado"):
        assert f'"{proibido}"' not in texto
    assert "NAO e veredito" in ev.nota


# --- TRAVA 3: rejeitadas também entram no denominador -----------------------


def test_recipe_invalida_e_REGISTRADA_e_nao_descartada():
    props = _parse(json.dumps([{"hypothesis": "h", "recipe": {"op": "olhar_futuro", "args": []}}]))
    assert len(props) == 1
    assert props[0].status == REJECTED_INVALID
    assert "desconhecida" in props[0].reason


def test_saida_malformada_do_llm_vira_registro_e_nao_excecao():
    """O modelo devolve lixo às vezes. Levantar aqui perderia a tentativa; e
    perder tentativa é mentir sobre quantas houve."""
    props = _parse("desculpe, nao posso ajudar com isso")
    assert len(props) == 1
    assert props[0].status == REJECTED_MALFORMED


def test_item_sem_recipe_e_registrado():
    props = _parse(json.dumps([{"hypothesis": "so prosa, sem recipe"}]))
    assert props[0].status == REJECTED_MALFORMED


# --- TRAVA 4: sem eval, whitelist manda -------------------------------------


def test_tentativa_de_injecao_na_recipe_e_rejeitada_como_operacao_desconhecida():
    props = _parse(json.dumps([{"hypothesis": "h", "recipe": {"op": "__import__", "args": []}}]))
    assert props[0].status == REJECTED_INVALID


def test_operacao_nao_causal_nao_existe_no_vocabulario_oferecido_ao_llm():
    """O prompt é gerado da whitelist real; se alguém adicionasse uma operação
    com lookahead, ela apareceria aqui — e o DSL a rejeitaria de qualquer forma."""
    vocab = vocabulary_doc()
    for proibida in ("lead", "future", "shift_forward", "centered"):
        assert proibida not in vocab
    assert "lag" in vocab and "zscore" in vocab


def test_prompt_carrega_o_vocabulario_gerado_e_o_historico_de_refutadas():
    p = build_prompt(features=["volume", "rsi"], horizon_days=7, historico="H5 REFUTADA: ...")
    assert vocabulary_doc() in p
    assert "H5 REFUTADA" in p
    assert "MECANISMO CAUSAL" in p


# --- TRAVA 5: duplicatas contam como duplicatas -----------------------------


def test_mesma_recipe_com_formatacao_diferente_tem_a_mesma_identidade():
    a = {"op": "lag", "args": [{"op": "feature", "args": ["x"]}, 2]}
    b = json.loads(json.dumps(a, indent=4))
    assert recipe_fingerprint(a) == recipe_fingerprint(b)


def test_duplicata_e_marcada_e_nao_silenciada():
    props = _parse(
        json.dumps([{"hypothesis": "a", "recipe": _ZSCORE}, {"hypothesis": "b", "recipe": _ZSCORE}])
    )
    assert [p.status for p in props] == [ACCEPTED, REJECTED_DUPLICATE]


def test_duplicata_contra_o_historico_ja_gravado(tmp_path):
    destino = tmp_path / "props.json"
    append_proposals(
        [Proposal(recipe_fingerprint(_ZSCORE), "t", "h", _ZSCORE, 7, "g", ACCEPTED)], destino
    )
    vistos = {p["proposal_id"] for p in load_proposals(destino)}
    props = _parse(json.dumps([{"hypothesis": "reproposta", "recipe": _ZSCORE}]), vistos=vistos)
    assert props[0].status == REJECTED_DUPLICATE


# --- TRAVA 6: append-only ---------------------------------------------------


def test_append_nunca_remove_o_que_ja_estava(tmp_path):
    destino = tmp_path / "props.json"
    append_proposals([Proposal("a", "t", "h1", _ZSCORE, 7, "g", ACCEPTED)], destino)
    append_proposals([Proposal("b", "t", "h2", _ZSCORE, 7, "g", REJECTED_INVALID)], destino)
    ids = [p["proposal_id"] for p in load_proposals(destino)]
    assert ids == ["a", "b"]


def test_arquivo_corrompido_nao_derruba_a_leitura(tmp_path):
    destino = tmp_path / "props.json"
    destino.write_text("{lixo", encoding="utf-8")
    assert load_proposals(destino) == []


def test_traco_usa_json_e_nao_jsonl_que_e_gitignored():
    """`*.jsonl` está no .gitignore (linha 20). Um traço científico invisível ao
    git seria o mesmo buraco que o h6_status.json veio tapar."""
    assert HL.PROPOSALS_PATH.suffix == ".json"
    assert "*.jsonl" in (ROOT / ".gitignore").read_text(encoding="utf-8")


# --- TRAVA 7: avaliação determinística, warmup descartado -------------------


def test_warmup_do_fator_e_descartado_do_n():
    """Contar `None` de aquecimento como observação inflaria o n do backtest."""
    dados = {"volume": [float(i) for i in range(30)]}
    retornos = [1.0] * 30
    ev = evaluate_proposal(Proposal("id", "t", "h", _ZSCORE, 7, "g", ACCEPTED), dados, retornos)
    assert ev.warmup_dropped == 4  # zscore(janela=5) -> 5-1
    assert ev.n <= 30 - ev.warmup_dropped


def test_amostra_curta_devolve_None_em_vez_de_numero_inventado():
    ev = evaluate_proposal(
        Proposal("id", "t", "h", _ZSCORE, 7, "g", ACCEPTED),
        {"volume": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]},
        [1.0] * 6,
    )
    assert ev.rho is None and ev.ic_lower is None


# --- laço completo, com propositor injetado (offline) -----------------------


def test_run_round_registra_tudo_com_propositor_falso(tmp_path):
    destino = tmp_path / "props.json"

    async def propositor_falso(prompt):
        assert "MECANISMO CAUSAL" in prompt
        return json.dumps(
            [
                {"hypothesis": "boa", "recipe": _ZSCORE},
                {"hypothesis": "invalida", "recipe": {"op": "nope", "args": []}},
                {"hypothesis": "duplicada", "recipe": _ZSCORE},
            ]
        )

    props = asyncio.run(
        HL.run_round(
            features=["volume"],
            horizon_days=7,
            historico="H1-H5 refutadas",
            proposer=propositor_falso,
            path=destino,
        )
    )
    assert [p.status for p in props] == [ACCEPTED, REJECTED_INVALID, REJECTED_DUPLICATE]
    gravadas = load_proposals(destino)
    assert len(gravadas) == 3, "as 3 precisam entrar no denominador, nao so a aceita"


def test_run_round_nao_toca_o_trials_json_real(tmp_path):
    """Prova comportamental, complementar à estrutural: roda o laço inteiro e
    confere que o registro oficial ficou byte-idêntico."""
    trials = ROOT / "GarimpoInvestimentos" / "trials.json"
    antes = trials.read_bytes()

    async def propositor(prompt):
        return json.dumps([{"hypothesis": "h", "recipe": _ZSCORE}])

    asyncio.run(
        HL.run_round(
            features=["volume"],
            horizon_days=7,
            historico="",
            proposer=propositor,
            path=tmp_path / "props.json",
        )
    )
    assert trials.read_bytes() == antes


@pytest.mark.parametrize("cerca", ["```json\n{}\n```", "```\n{}\n```"])
def test_cerca_de_markdown_do_llm_e_tolerada(cerca):
    """Modelos envolvem JSON em bloco de código o tempo todo; tratar isso como
    malformado descartaria propostas legítimas e sujaria o denominador."""
    props = _parse(cerca.replace("{}", json.dumps([{"hypothesis": "h", "recipe": _ZSCORE}])))
    assert props[0].status == ACCEPTED
