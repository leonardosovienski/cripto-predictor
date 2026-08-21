"""Harness de verdade plantada: afere o pipeline INTEIRO, não só o juiz.

O controle positivo existente (test_positive_control.py) injeta pares direto no
`_report` e valida o juiz estatístico. Este exercita o encanamento que ficava de
fora — store -> _load_rows -> enrich_with_realized_prices -> par — que é onde a
MEDIÇÃO acontece e que, verificado em 2026-08-21, nenhum teste importava.
"""

import asyncio

import pytest

import GarimpoInvestimentos.analyzers.backtest as bt
from GarimpoInvestimentos.analyzers.ground_truth_harness import (
    MAX_ROUNDING_ERROR_PP,
    compare_to_truth,
    plant_world,
    spearman_of,
)


def _rodar(tmp_path, monkeypatch, **kw):
    """Planta o mundo e roda o caminho REAL do backtest sobre ele."""
    db = tmp_path / "feature_store.db"
    world = plant_world(db, **kw)
    monkeypatch.setattr(bt, "FEATURE_STORE_DB", db)
    rows = bt._load_rows()
    enriched = asyncio.run(bt.enrich_with_realized_prices(rows))
    return world, enriched


# --- 1. ERRO DE MEDIÇÃO: a pergunta que ninguém estava fazendo ---------------


def test_retorno_medido_bate_com_o_plantado(tmp_path, monkeypatch):
    """Se `enrich_with_realized_prices` pegasse o preço do dia errado, TODO
    veredito já emitido estaria medindo outra coisa — e o controle positivo do
    juiz continuaria verde, porque nunca toca este caminho."""
    world, enriched = _rodar(tmp_path, monkeypatch)
    r = compare_to_truth(enriched, world)
    assert r.n_recovered > 0, "nada foi recuperado — o caminho está quebrado"
    assert r.max_measurement_error_pp is not None
    assert r.max_measurement_error_pp <= MAX_ROUNDING_ERROR_PP + 1e-9, (
        f"erro de medição de {r.max_measurement_error_pp:.6f}pp excede o quantum "
        f"de arredondamento ({MAX_ROUNDING_ERROR_PP}pp) — isso é dia/preço/fonte "
        "errados, não arredondamento"
    )
    assert r.measurement_ok


def test_granularidade_da_medicao_e_a_documentada():
    """`enrich_with_realized_prices` faz round(...,2): a medição é quantizada em
    0,01pp. Não é defeito, é formatação — mas não estava caracterizada em lugar
    nenhum, e uma aferição que não a conheça acusa bug onde há arredondamento
    (a primeira versão deste harness fez exatamente isso)."""
    import inspect

    fonte = inspect.getsource(bt.enrich_with_realized_prices)
    assert "round(" in fonte and ", 2)" in fonte, (
        "o arredondamento sumiu do enrich — MEASUREMENT_QUANTUM_PP ficou desatualizado"
    )
    assert MAX_ROUNDING_ERROR_PP == pytest.approx(0.005)


def test_nenhuma_previsao_madura_some_no_caminho(tmp_path, monkeypatch):
    """Perda silenciosa de amostra enviesaria o n de qualquer veredito."""
    world, enriched = _rodar(tmp_path, monkeypatch)
    r = compare_to_truth(enriched, world)
    assert r.lost_predictions == 0, f"{r.lost_predictions} previsão(ões) madura(s) sumiram"


def test_um_deslocamento_de_um_dia_seria_DETECTADO(tmp_path, monkeypatch):
    """Contraprova: se o teste acima passasse com qualquer coisa, não provaria
    nada. Aqui corrompemos a verdade em um dia e exigimos que a comparação
    ACUSE — garantindo que ela tem poder de detecção."""
    world, enriched = _rodar(tmp_path, monkeypatch)
    corrompida = {k: v + 0.5 for k, v in world.truth.items()}  # desloca 0.5pp
    falso = type(world)(
        db_path=world.db_path,
        truth=corrompida,
        n_predictions=world.n_predictions,
        horizon_days=world.horizon_days,
    )
    r = compare_to_truth(enriched, falso)
    assert not r.measurement_ok, "a comparação não detecta divergência — é decorativa"
    # 0,5 do deslocamento SOMADO ao quantum de arredondamento da própria medição.
    assert r.max_measurement_error_pp == pytest.approx(0.5, abs=MAX_ROUNDING_ERROR_PP + 1e-9)


# --- 2. PODER: sensibilidade e especificidade ponta a ponta ------------------


def test_edge_plantado_e_RECUPERADO_pelo_caminho_completo(tmp_path, monkeypatch):
    world, enriched = _rodar(tmp_path, monkeypatch, edge=0.08, seed=17)
    rho = spearman_of(enriched, world.horizon_days)
    assert rho is not None and rho > 0.5, (
        f"edge plantado não sobreviveu ao encanamento (rho={rho}) — o pipeline "
        "perderia sinal real se ele existisse"
    )


def test_mundo_nulo_nao_produz_correlacao(tmp_path, monkeypatch):
    """Especificidade: sem o par, o teste positivo sozinho passaria num pipeline
    que sempre diz 'sim'."""
    world, enriched = _rodar(tmp_path, monkeypatch, edge=0.0, seed=23)
    rho = spearman_of(enriched, world.horizon_days)
    assert rho is not None and abs(rho) < 0.25, f"correlação fabricada no nulo: rho={rho}"


def test_sensibilidade_e_especificidade_juntas(tmp_path, monkeypatch):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    w1, e1 = _rodar(tmp_path / "a", monkeypatch, edge=0.08, seed=17)
    w2, e2 = _rodar(tmp_path / "b", monkeypatch, edge=0.0, seed=23)
    com = spearman_of(e1, w1.horizon_days)
    sem = spearman_of(e2, w2.horizon_days)
    assert com > abs(sem), f"pipeline não discrimina: edge={com}, nulo={sem}"


# --- 3. o caminho exercitado é o REAL, não uma cópia -------------------------


def test_usa_as_funcoes_canonicas_do_backtest_oficial(tmp_path, monkeypatch):
    """Se o harness reimplementasse o caminho, mediria a própria cópia — que é o
    defeito que ele existe para pegar."""
    world, enriched = _rodar(tmp_path, monkeypatch)
    assert enriched, "o caminho canônico não produziu nada"
    # veio de _load_rows: campos de estratificação obrigatórios presentes
    for campo in ("ativo", "score", "pred_date", "fonte", "juiz"):
        assert campo in enriched[0], f"campo {campo} ausente — não veio de _load_rows"
    # veio de enrich: chaves de horizonte presentes
    assert any(f"var_d{h}_pct" in enriched[0] for h in bt.HORIZONS)


def test_todos_os_horizontes_resolvem_offline(tmp_path, monkeypatch):
    """`_realized_price` é offline-first mas cai na REDE (com sleep de 1,5s) quando
    a store não tem o dia. Se algum horizonte não estivesse coberto, o harness
    sairia para a rede centenas de vezes — foi o que aconteceu na primeira versão,
    que levava minutos. Todo var_dN_pct preenchido prova cobertura completa."""
    world, enriched = _rodar(tmp_path, monkeypatch)
    for h in bt.HORIZONS:
        preenchidos = sum(1 for r in enriched if r.get(f"var_d{h}_pct") is not None)
        assert preenchidos == len(enriched), (
            f"D+{h}: {len(enriched) - preenchidos} previsão(ões) sem preço na store "
            "— essas cairiam na rede"
        )
