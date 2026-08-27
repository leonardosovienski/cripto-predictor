"""Adapter `SignalRecord` -> `TradeIntent` — a peça declarada como ausente desde
o handoff de 2026-08-14.

O campo `source_signal_id` do TradeIntent existia para rastreabilidade, mas nada
preenchia: não havia função que convertesse a saída de `v3/signal_engine.py` numa
intenção executável. Este módulo é essa função.

=== A TRAVA QUE ELE CARREGA, e por que ela é o ponto ===

`v3/signal_engine.py` produz sinais da família `funding_oi_hmm_v3` — que está em
`frozen_families` no `charters/scientific_state.json`, porque H1/H2/H3 foram
REFUTADAS. Um adapter ingênuo converteria sinal de família refutada em intenção
de trade sem que ninguém percebesse: seria transformar "isto não funciona" em
"pretendo operar isto", em silêncio, por conveniência de tipos.

Por isso `to_trade_intent` EXIGE família, trial e fingerprint, confronta a família
com o charter e incorpora no próprio tipo a política de custo usada. Família
congelada => recusa sem escape no adapter executável.

=== O QUE ISTO NÃO É ===

TradeIntent é TIPO, não ordem. Este módulo não envia nada, não toca venue, não
altera gate e não autoriza capital — `capital_authorized` segue `false` e nada
aqui o consulta para pedir permissão, porque não há permissão a pedir. Faz parte
da camada construída por override de governança 2026-08-14
(docs/HYPOTHESES.md), cuja premissa declarada é: infraestrutura pode existir
antes de edge validado, desde que não se disfarce de autorização.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from GarimpoInvestimentos.governance import load_scientific_state
from GarimpoInvestimentos.trading.cost_policy import cost_model_for
from GarimpoInvestimentos.trading.contracts import (
    Direction,
    ExitRule,
    Instrument,
    TradeIntent,
    new_id,
)


class FrozenFamilyError(ValueError):
    """Sinal de família cientificamente congelada não vira intenção por default."""


def _direction(valor: int) -> Direction | None:
    if valor > 0:
        return Direction.LONG
    if valor < 0:
        return Direction.SHORT
    return None


def to_trade_intent(
    signal,
    *,
    family: str,
    trial_id: str,
    pipeline_fingerprint: str,
    instrument: Instrument,
    holding_period_hours: float,
    entry_window_minutes: float = 30.0,
    max_position_fraction: float = 0.05,
    exit_rule: ExitRule = ExitRule.TIME_STOP,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    slippage_limit_bps: float = 50.0,
    skip_uncertain_regime: bool = True,
    charter_path=None,
) -> TradeIntent | None:
    """Converte um `SignalRecord` em `TradeIntent`, ou devolve None quando o sinal
    não deve virar intenção nenhuma.

    Devolve None (não levanta) para as ausências LEGÍTIMAS de sinal, porque elas
    são o caso normal e não são erro:
      - `active=False`  : sinal ausente ou dados degradados. Um sinal degradado
                          que virasse intenção seria pior que nenhum sinal.
      - `direction == 0`: flat é uma decisão, não uma posição.
      - regime incerto  : com `skip_uncertain_regime` (default True). O
                          `regime_is_uncertain` existe porque o próprio motor
                          declara baixa convicção; operar contra essa declaração
                          precisa ser escolha explícita.

    LEVANTA `FrozenFamilyError` para família congelada, porque isso não é
    ausência de sinal — é uso indevido de um resultado já refutado, e falhar
    alto é a única forma de não passar despercebido.

    `target_position_fraction` = `strength` x `max_position_fraction`. O teto é
    parâmetro obrigatório-por-default baixo (5%): sizing não tem gate validado
    neste projeto, então o default precisa ser conservador em vez de "1.0 porque
    o contrato permite".
    """
    estado = load_scientific_state(charter_path) if charter_path else load_scientific_state()
    if family in estado.frozen_families:
        raise FrozenFamilyError(
            f"familia '{family}' esta congelada em frozen_families "
            f"({estado.frozen_families}): sinal de hipotese REFUTADA nao vira "
            "intencao de trade. O adapter executavel nao possui bypass."
        )

    # Uma intenção executável só nasce de modelo calibrado para veredito. Isso
    # torna impossível esquecer o guard e carregar custo apenas "por convenção".
    cost_model = cost_model_for(instrument, for_verdict=True)

    if not getattr(signal, "active", False):
        return None
    direcao = _direction(int(getattr(signal, "direction", 0)))
    if direcao is None:
        return None
    if skip_uncertain_regime and getattr(signal, "regime_is_uncertain", False):
        return None

    forca = float(getattr(signal, "strength", 0.0))
    if not 0.0 <= forca <= 1.0:
        raise ValueError(f"SignalRecord.strength fora de [0,1]: {forca}")
    fracao = forca * max_position_fraction
    if fracao <= 0:
        return None

    gerado_em = datetime.fromtimestamp(int(signal.timestamp_signal_ms) / 1000, tz=UTC)
    return TradeIntent(
        intent_id=new_id("intent"),
        instrument=instrument,
        direction=direcao,
        generated_at=gerado_em,
        # A janela NUNCA começa antes de `generated_at` — o próprio TradeIntent
        # rejeitaria, mas construir assim deixa a intenção explícita aqui também.
        entry_window_start=gerado_em,
        entry_window_end=gerado_em + timedelta(minutes=entry_window_minutes),
        holding_period_hours=holding_period_hours,
        target_position_fraction=fracao,
        exit_rule=exit_rule,
        scientific_family=family,
        trial_id=trial_id,
        pipeline_fingerprint=pipeline_fingerprint,
        cost_model_id="v3.costs.CostModel",
        estimated_round_trip_friction=cost_model.friction(fracao),
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        slippage_limit_bps=slippage_limit_bps,
        source_signal_id=str(getattr(signal, "event_id", "")),
    )


__all__ = ["FrozenFamilyError", "to_trade_intent"]
