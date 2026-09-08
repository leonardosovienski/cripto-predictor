"""Guarda de sanidade numérica dos providers (dpl/providers/_validation.py).

Fecha uma lacuna real: MarketDataPoint.__post_init__ (vendor) valida `high >= low`,
mas essa comparação com NaN é sempre False — um preço NaN passaria pela guarda "falha
explícita" sem ser pego, e corromperia silenciosamente consensus_median/mean (mediana
com NaN tem resultado indefinido, sem exceção). JSON padrão não tem NaN, mas o parser
`json` do Python aceita os tokens literais NaN/Infinity se a API os emitir. Corrigido
na fronteira do provider (domínio), não no vendor: um valor não-finito vira ValueError,
que o Router já trata como falha normal desse provedor.
"""

import math

import pytest

from GarimpoInvestimentos.dpl.providers._validation import require_finite


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_require_finite_rejects_non_finite_values(bad):
    with pytest.raises(ValueError, match="não-finito"):
        require_finite(bad, field="close", provider="binance", symbol="bitcoin")


@pytest.mark.parametrize("good", [0.0, 1.0, -1.0, 42_000.5, 1e-9])
def test_require_finite_passes_through_finite_values(good):
    assert require_finite(good, field="close", provider="binance", symbol="bitcoin") == good


def test_require_finite_error_message_identifies_field_provider_symbol():
    with pytest.raises(ValueError) as exc_info:
        require_finite(math.nan, field="volume", provider="kraken", symbol="solana")
    msg = str(exc_info.value)
    assert "volume" in msg and "kraken" in msg and "solana" in msg
