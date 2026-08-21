"""Adapter SignalRecord -> TradeIntent.

A trava que mais importa aqui não é de tipo, é científica: `v3/signal_engine.py`
produz sinais da família `funding_oi_hmm_v3`, que está CONGELADA porque
H1/H2/H3 foram refutadas. Converter isso em intenção de trade em silêncio seria
transformar "não funciona" em "pretendo operar", por conveniência de tipos.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from GarimpoInvestimentos.trading.contracts import Direction, ExitRule, Instrument
from GarimpoInvestimentos.trading.signal_adapter import FrozenFamilyError, to_trade_intent

INSTRUMENTO = Instrument(symbol="BTCUSDT", venue="binance", asset_class="crypto_perp")
# 2026-08-21T12:00:00Z
TS_MS = int(datetime(2026, 8, 21, 12, 0, tzinfo=UTC).timestamp() * 1000)


@dataclass(frozen=True)
class FakeSignal:
    """Espelha os campos que o adapter lê do SignalRecord real."""

    event_id: str = "evt-1"
    timestamp_signal_ms: int = TS_MS
    direction: int = 1
    strength: float = 0.8
    active: bool = True
    regime_is_uncertain: bool = False


def _intent(sinal=None, **kw):
    kw.setdefault("family", "familia_nao_congelada")
    kw.setdefault("instrument", INSTRUMENTO)
    kw.setdefault("holding_period_hours", 24.0)
    return to_trade_intent(sinal or FakeSignal(), **kw)


# --- a trava científica -----------------------------------------------------


def test_familia_congelada_LEVANTA_em_vez_de_devolver_none():
    """Falhar alto, não silenciosamente: isto não é ausência de sinal, é uso
    indevido de resultado refutado."""
    with pytest.raises(FrozenFamilyError, match="congelada"):
        _intent(family="funding_oi_hmm_v3")


def test_escape_da_familia_congelada_existe_mas_precisa_ser_explicito():
    intent = _intent(family="funding_oi_hmm_v3", allow_frozen_family=True)
    assert intent is not None


def test_familia_congelada_e_lida_do_charter_e_nao_de_lista_hardcoded():
    """Se alguém congelar outra família amanhã, a trava tem que valer para ela
    sem mudar este código."""
    from GarimpoInvestimentos.governance import load_scientific_state

    assert "funding_oi_hmm_v3" in load_scientific_state().frozen_families


# --- ausências legítimas: None, não exceção ---------------------------------


def test_sinal_inativo_nao_vira_intencao():
    """Dados degradados que virassem intenção seriam pior que sinal nenhum."""
    assert _intent(FakeSignal(active=False)) is None


def test_direcao_flat_nao_vira_intencao():
    assert _intent(FakeSignal(direction=0)) is None


def test_regime_incerto_e_pulado_por_default():
    """O próprio motor declara baixa convicção; operar contra isso é escolha."""
    assert _intent(FakeSignal(regime_is_uncertain=True)) is None
    assert _intent(FakeSignal(regime_is_uncertain=True), skip_uncertain_regime=False) is not None


def test_strength_zero_nao_vira_intencao():
    assert _intent(FakeSignal(strength=0.0)) is None


# --- conversão correta ------------------------------------------------------


def test_direcao_e_mapeada_nos_dois_sentidos():
    assert _intent(FakeSignal(direction=1)).direction is Direction.LONG
    assert _intent(FakeSignal(direction=-1)).direction is Direction.SHORT


def test_tamanho_e_strength_vezes_teto_e_o_teto_default_e_conservador():
    """Sizing não tem gate validado neste projeto; o default precisa ser baixo
    em vez de 1.0 só porque o contrato permite."""
    intent = _intent(FakeSignal(strength=0.5))
    assert intent.target_position_fraction == pytest.approx(0.5 * 0.05)
    assert _intent(FakeSignal(strength=1.0)).target_position_fraction == pytest.approx(0.05)


def test_rastreabilidade_ate_o_sinal_de_origem():
    """`source_signal_id` existia no contrato e nada preenchia."""
    assert _intent(FakeSignal(event_id="evt-xyz")).source_signal_id == "evt-xyz"


def test_janela_de_entrada_nunca_comeca_antes_da_geracao():
    """Anti-lookahead: o TradeIntent já rejeitaria, mas a construção também
    não deve tentar."""
    intent = _intent()
    assert intent.entry_window_start == intent.generated_at
    assert intent.entry_window_end > intent.entry_window_start


def test_timestamp_do_sinal_vira_datetime_utc_correto():
    intent = _intent()
    assert intent.generated_at == datetime(2026, 8, 21, 12, 0, tzinfo=UTC)


def test_strength_fora_do_intervalo_e_erro_explicito():
    with pytest.raises(ValueError, match="strength"):
        _intent(FakeSignal(strength=1.5))


def test_exit_rule_price_stop_exige_stop_loss_pelo_contrato():
    """A validação vive no TradeIntent; o adapter não pode contorná-la."""
    with pytest.raises(ValueError, match="stop_loss_pct"):
        _intent(exit_rule=ExitRule.PRICE_STOP)
    # stop_loss_pct e FRACAO em (0,1), apesar do sufixo _pct no nome — o contrato
    # rejeita 2.0. Registrado aqui porque o nome induz ao erro (eu cai nele).
    assert _intent(exit_rule=ExitRule.PRICE_STOP, stop_loss_pct=0.02) is not None


def test_stop_loss_fora_de_zero_um_e_rejeitado_pelo_contrato():
    """Trava contra a leitura errada do sufixo _pct: 2.0 seria 200%."""
    with pytest.raises(ValueError, match=r"\(0, 1\)"):
        _intent(exit_rule=ExitRule.PRICE_STOP, stop_loss_pct=2.0)
