"""Contrato do pre-filtro de custo: puramente local, determinístico e opt-in."""
from GarimpoInvestimentos.analyzers import prefilter


def _data(**overrides):
    data = {
        "volume_usd": 20_000_000.0,
        "change_7d": 5.0,
        "indicadores": {"preco_vs_sma200_pct": 2.0, "macd_histogram": 0.1},
    }
    data.update(overrides)
    return data


def test_desligado_preserva_todos_os_ativos(monkeypatch):
    monkeypatch.setattr(prefilter.settings, "LLM_PREFILTER_ENABLED", False)
    assert prefilter.decide({}).selected
    assert prefilter.decide({}).reason == "disabled"


def test_seleciona_movimento_bull_e_bear(monkeypatch):
    monkeypatch.setattr(prefilter.settings, "LLM_PREFILTER_ENABLED", True)
    assert prefilter.decide(_data()).reason == "technical_bull"
    bear = _data(change_7d=-5.0, indicadores={"preco_vs_sma200_pct": -2.0, "macd_histogram": -0.1})
    assert prefilter.decide(bear).reason == "technical_bear"


def test_exclui_com_motivo_auditavel(monkeypatch):
    monkeypatch.setattr(prefilter.settings, "LLM_PREFILTER_ENABLED", True)
    assert prefilter.decide(_data(volume_usd=1.0)).reason == "low_or_missing_volume"
    assert prefilter.decide(_data(change_7d=0.5)).reason == "weak_7d_momentum"
    assert prefilter.decide(_data(indicadores={})).reason == "neutral_or_missing_technical_direction"
