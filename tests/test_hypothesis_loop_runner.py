"""H8 (docs/HYPOTHESES.md): testa o wiring que faltava em hypothesis_loop.py —
carregar dado real, montar `dados`/`retornos`, rodar uma rodada completa
(propõe→registra→avalia) e anexar ao traço de avaliações. Não testa a
aritmética do DSL/gate (já coberta em test_hypothesis_loop.py e
test_factor_dsl.py) — testa que este módulo liga as peças certas, sem
lookahead e sem promover nada sozinho.
"""

import asyncio
import json

import pytest

from GarimpoInvestimentos.analyzers.hypothesis_loop import ACCEPTED
from GarimpoInvestimentos.analyzers.hypothesis_loop_runner import (
    _build_dados_e_retornos,
    append_evaluations,
    load_evaluations,
    main,
    run_h8_round,
)
from GarimpoInvestimentos.v3.feature_builder import FeatureVector


def _fv(ts_ms: int, spot_close: float, **overrides) -> FeatureVector:
    base = dict(
        timestamp_exchange_ms=ts_ms,
        asset="BTCUSDT",
        funding_rate_raw=0.0001,
        oi_notional_usd=1_000_000.0,
        spot_close=spot_close,
        funding_zscore=0.5,
        oi_log_delta=0.01,
        leverage_pressure=0.2,
        log_return_8h=0.001,
        realized_vol_24h=0.02,
        data_quality_score=1.0,
    )
    base.update(overrides)
    return FeatureVector(**base)


def test_dados_expoe_os_campos_certos_de_feature_vector():
    fvs = [_fv(i, 100.0 + i, funding_zscore=float(i)) for i in range(10)]
    dados, _ = _build_dados_e_retornos(fvs, horizon_days=1)
    assert dados["funding_zscore"] == [float(i) for i in range(10)]
    assert set(dados) == {
        "funding_zscore",
        "oi_log_delta",
        "leverage_pressure",
        "log_return_8h",
        "realized_vol_24h",
    }


def test_retorno_forward_usa_apenas_close_futuro_dentro_da_serie():
    import math

    # horizon_days=1 -> passos = 3 (periodos de 8h). closes sobem 1/dia geometricamente.
    closes = [100.0 * (1.01**i) for i in range(12)]
    fvs = [_fv(i, c) for i, c in enumerate(closes)]
    _, retornos = _build_dados_e_retornos(fvs, horizon_days=1)
    passos = 3
    for i in range(len(closes) - passos):
        assert retornos[i] == pytest.approx(math.log(closes[i + passos] / closes[i]))
    # últimos `passos` pontos não têm retorno futuro observável — None, nunca inventado.
    for i in range(len(closes) - passos, len(closes)):
        assert retornos[i] is None


def test_retorno_com_close_nao_positivo_vira_none_nao_erro():
    fvs = [_fv(0, 100.0), _fv(1, 0.0), _fv(2, 100.0), _fv(3, 100.0)]
    _, retornos = _build_dados_e_retornos(fvs, horizon_days=0)
    # horizon_days=0 -> passos=0 -> j==i sempre; close[1]<=0 deve dar None no índice 1
    assert retornos[1] is None


def test_evaluations_trace_e_append_only(tmp_path):
    path = tmp_path / "hypothesis_evaluations.json"
    from GarimpoInvestimentos.analyzers.hypothesis_loop import Evaluation

    e1 = Evaluation("id1", n=40, rho=0.1, ic_lower=0.0, ic_upper=0.2, warmup_dropped=0)
    e2 = Evaluation("id2", n=35, rho=-0.05, ic_lower=-0.2, ic_upper=0.1, warmup_dropped=0)
    append_evaluations([e1], path=path)
    append_evaluations([e2], path=path)
    saved = load_evaluations(path)
    assert [s["proposal_id"] for s in saved] == ["id1", "id2"]


def test_load_evaluations_arquivo_inexistente_retorna_vazio(tmp_path):
    assert load_evaluations(tmp_path / "nao_existe.json") == []


@pytest.mark.parametrize("horizon_days", [7])
def test_run_h8_round_avalia_so_propostas_aceitas(tmp_path, monkeypatch, horizon_days):
    """Rodada completa: injeta feature vectors sintéticos e um proposer
    determinístico com 1 proposta válida + 1 malformada — só a válida deve
    virar Evaluation, e ela deve ir para o traço."""
    fvs = [_fv(i, 100.0 + i * 0.1) for i in range(200)]
    monkeypatch.setattr(
        "GarimpoInvestimentos.analyzers.hypothesis_loop_runner._load_feature_vectors",
        lambda symbol: fvs,
    )
    eval_path = tmp_path / "evaluations.json"
    proposals_path = tmp_path / "proposals.json"

    async def _proposer(_prompt: str) -> str:
        return json.dumps(
            [
                {
                    "hypothesis": "teste valido",
                    "recipe": {"op": "feature", "args": ["leverage_pressure"]},
                },
                {"hypothesis": "sem recipe"},
            ]
        )

    propostas, avaliacoes = asyncio.run(
        run_h8_round(
            symbol="BTCUSDT",
            horizon_days=horizon_days,
            proposer=_proposer,
            proposer_name="teste",
            now=None,
            proposals_path=proposals_path,
            evaluations_path=eval_path,
        )
    )
    assert len(propostas) == 2
    aceitas = [p for p in propostas if p.status == ACCEPTED]
    assert len(aceitas) == 1
    assert len(avaliacoes) == 1
    assert avaliacoes[0].proposal_id == aceitas[0].proposal_id

    saved = load_evaluations(eval_path)
    assert len(saved) == 1
    assert saved[0]["proposal_id"] == aceitas[0].proposal_id


def test_dry_run_nao_chama_llm_real_e_nao_quebra(tmp_path, monkeypatch):
    fvs = [_fv(i, 100.0 + i * 0.1) for i in range(200)]
    monkeypatch.setattr(
        "GarimpoInvestimentos.analyzers.hypothesis_loop_runner._load_feature_vectors",
        lambda symbol: fvs,
    )
    # main() usa PROPOSALS_PATH/EVALUATIONS_PATH deste módulo (a cópia importada,
    # não a de hypothesis_loop) — e --dry-run deriva ".dryrun.json" delas via
    # with_name, então redirecionar as bases pro tmp_path é o bastante.
    monkeypatch.setattr(
        "GarimpoInvestimentos.analyzers.hypothesis_loop_runner.PROPOSALS_PATH",
        tmp_path / "hypothesis_proposals.json",
    )
    monkeypatch.setattr(
        "GarimpoInvestimentos.analyzers.hypothesis_loop_runner.EVALUATIONS_PATH",
        tmp_path / "hypothesis_evaluations.json",
    )
    exit_code = main(["--dry-run", "--symbol", "BTCUSDT"])
    assert exit_code == 0
    assert (tmp_path / "hypothesis_proposals.dryrun.json").exists()
    assert (tmp_path / "hypothesis_evaluations.dryrun.json").exists()
    # o arquivo real (sem .dryrun) NUNCA deve ser tocado por --dry-run.
    assert not (tmp_path / "hypothesis_proposals.json").exists()
    assert not (tmp_path / "hypothesis_evaluations.json").exists()
