"""build_portfolio_report() e a política de custo canônica."""

from datetime import UTC, datetime

import pytest

from GarimpoInvestimentos.trading.contracts import Direction, Instrument, Position
from GarimpoInvestimentos.trading.cost_policy import (
    PERP,
    SPOT,
    CostModelMismatch,
    UncalibratedCostModel,
    assert_verdict_grade,
    cost_model_for,
)
from GarimpoInvestimentos.trading.report import build_portfolio_report, render
from GarimpoInvestimentos.v3.costs import CostModel

ABERTO = datetime(2026, 8, 21, tzinfo=UTC)


def _pos(symbol, qty, price, venue="binance"):
    return Position(
        instrument=Instrument(symbol=symbol, venue=venue),
        direction=Direction.LONG,
        qty=qty,
        avg_entry_price=price,
        opened_at=ABERTO,
    )


# --- relatório de portfólio -------------------------------------------------


def test_compoe_as_metricas_em_vez_de_recalcular():
    pos = [_pos("BTCUSDT", 1.0, 100.0), _pos("ETHUSDT", 2.0, 50.0)]
    marks = {"binance:BTCUSDT": 100.0, "binance:ETHUSDT": 50.0}
    r = build_portfolio_report(pos, marks, equity=1000.0)
    assert r.n_positions == 2
    assert r.gross_notional == pytest.approx(200.0)
    assert r.gross_leverage == pytest.approx(0.2)
    assert r.exposure_by_venue == {"binance": pytest.approx(200.0)}


def test_correlacao_alta_vira_AVISO_porque_exposicao_individual_a_esconde():
    """Duas posições pequenas e correlacionadas são uma posição grande
    disfarçada — é exatamente o que nenhuma métrica isolada mostra."""
    pos = [_pos("AAA", 1.0, 100.0), _pos("BBB", 1.0, 100.0)]
    marks = {"binance:AAA": 100.0, "binance:BBB": 100.0}
    r = build_portfolio_report(
        pos,
        marks,
        equity=10_000.0,
        returns_by_asset={"AAA": [1.0, 2.0, 3.0, 4.0], "BBB": [1.0, 2.0, 3.0, 4.0]},
    )
    assert r.max_pairwise_correlation is not None
    a, b, v = r.max_pairwise_correlation
    assert v == pytest.approx(1.0)
    assert any("correlacao alta" in x for x in r.avisos)


def test_avisos_nao_sao_gate_e_o_relatorio_declara_isso():
    r = build_portfolio_report([], {}, equity=1000.0)
    assert "nao e gate" in r.nota.lower()
    assert "capital_authorized=false" in r.nota
    assert "nao e gate" in render(r).lower()


def test_portfolio_vazio_nao_quebra():
    r = build_portfolio_report([], {}, equity=1000.0)
    assert r.n_positions == 0 and r.gross_leverage == 0.0 and r.concentration_hhi == 0.0


def test_mark_price_ausente_e_erro_e_nao_zero():
    """Tratar mark ausente como zero subestimaria exposição em silêncio."""
    with pytest.raises(ValueError, match="mark price"):
        build_portfolio_report([_pos("BTCUSDT", 1.0, 100.0)], {}, equity=1000.0)


def test_leverage_acima_de_1_vira_aviso():
    pos = [_pos("BTCUSDT", 10.0, 100.0)]
    r = build_portfolio_report(pos, {"binance:BTCUSDT": 100.0}, equity=500.0)
    assert r.gross_leverage == pytest.approx(2.0)
    assert any("leverage bruta" in x for x in r.avisos)


# --- política de custo ------------------------------------------------------


def test_perp_usa_o_CostModel_com_funding():
    modelo = cost_model_for(Instrument(symbol="BTCUSDT", venue="binance", asset_class=PERP))
    assert isinstance(modelo, CostModel)


def test_spot_usa_walk_the_book_e_nao_o_CostModel():
    """Fundir os dois cobraria funding de spot — spot não tem funding."""
    modelo = cost_model_for(Instrument(symbol="BTCUSDT", venue="binance", asset_class=SPOT))
    assert not isinstance(modelo, CostModel)
    assert callable(modelo)


def test_classe_desconhecida_e_erro_e_nao_default_silencioso():
    """Aplicar custo errado por omissão equivale a não aplicar custo."""
    with pytest.raises(CostModelMismatch, match="desconhecida"):
        cost_model_for(Instrument(symbol="X", venue="v", asset_class="acoes"))


def test_spot_nao_pode_sustentar_veredito_porque_nao_esta_calibrado():
    """O walk-the-book é explicitamente não calibrado (override 2026-08-14);
    devolver número dele para veredito seria dar aparência oficial a algo que
    o próprio projeto marcou como não confiável."""
    spot = Instrument(symbol="BTCUSDT", venue="binance", asset_class=SPOT)
    with pytest.raises(UncalibratedCostModel, match="NAO CALIBRADO"):
        cost_model_for(spot, for_verdict=True)
    with pytest.raises(UncalibratedCostModel):
        assert_verdict_grade(spot)


def test_perp_sustenta_veredito_porque_foi_o_que_julgou_H1_H2_H3():
    perp = Instrument(symbol="BTCUSDT", venue="binance", asset_class=PERP)
    assert_verdict_grade(perp)  # não levanta
    assert isinstance(cost_model_for(perp, for_verdict=True), CostModel)


def test_default_do_Instrument_e_perp_entao_o_caminho_padrao_e_o_calibrado():
    """Instrument.asset_class default = crypto_perp; se o default caísse na
    classe não calibrada, o caminho fácil seria o errado."""
    assert Instrument(symbol="X", venue="v").asset_class == PERP
