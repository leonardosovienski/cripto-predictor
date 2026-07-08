"""Guard temporal bidirecional na inserção + versionamento de features (0007).

Duas pontas do guard (auditoria jul/2026):
  - published_at < timestamp  → look-ahead de ROTULAGEM (publicou antes de
    observar) — vazamento na origem que o Alignment Engine, correto, propagaria;
  - published_at > timestamp + teto → staleness/rotulagem anômala.

Versionamento (migração 0007): recalcular uma feature com lógica nova NÃO pode
sobrescrever o histórico que experimentos passados leram — versões coexistem.
"""
from datetime import datetime, timedelta, timezone

import pytest

from GarimpoInvestimentos.dpl import FeatureStore, MarketDataPoint, SignalPoint

UTC = timezone.utc
TS = datetime(2026, 1, 10, tzinfo=UTC)


def _candle(published_at) -> MarketDataPoint:
    return MarketDataPoint(
        symbol="bitcoin", timestamp=TS, open=10, high=11, low=9, close=10,
        volume=100.0, source="binance", interval="1d", published_at=published_at)


def _signal(published_at) -> SignalPoint:
    return SignalPoint(name="fear_greed", timestamp=TS, value=50,
                       source="alternative.me", published_at=published_at)


@pytest.fixture
def store(tmp_path):
    with FeatureStore(tmp_path / "fs.db") as s:
        yield s


# --- guard temporal ------------------------------------------------------------

# O limite inferior tem DUAS cintas: o construtor do contrato (MarketDataPoint/
# SignalPoint) já rejeita published_at < timestamp na criação do ponto; o guard
# da store repete o cheque na inserção (defesa em profundidade contra pontos
# construídos por caminhos que contornem o contrato). O match aceita qualquer cinta.
_LOOKAHEAD = "look-ahead de rotulagem|anterior ao timestamp"


def test_candle_publicado_antes_de_observar_e_rejeitado(store):
    with pytest.raises(ValueError, match=_LOOKAHEAD):
        store.write_raw([_candle(TS - timedelta(seconds=1))])
    assert store.read_raw("bitcoin", "1d") == []  # nada entrou


def test_sinal_publicado_antes_de_observar_e_rejeitado(store):
    with pytest.raises(ValueError, match=_LOOKAHEAD):
        store.write_signals([_signal(TS - timedelta(days=1))])


def test_publicacao_alem_do_teto_e_rejeitada(store):
    with pytest.raises(ValueError, match="rotulagem anômala"):
        store.write_raw([_candle(TS + timedelta(days=46))])


def test_lags_legitimos_passam(store):
    assert store.write_raw([_candle(TS)]) == 1                       # no próprio ts
    assert store.write_signals([_signal(TS + timedelta(days=2))]) == 1  # lag curto


def test_teto_e_ajustavel_por_instancia(tmp_path):
    """Domínio de lag maior (ex.: macro anual) sobe o teto explicitamente."""
    with FeatureStore(tmp_path / "fs.db",
                      max_publication_lag=timedelta(days=400)) as s:
        assert s.write_raw([_candle(TS + timedelta(days=100))]) == 1


# --- feature_version -----------------------------------------------------------

def test_versoes_de_feature_coexistem_sem_sobrescrever(store):
    store.write_features("bitcoin", "1d", [{"ts": TS, "rsi": 30.0}])
    store.write_features("bitcoin", "1d", [{"ts": TS, "rsi": 55.0}],
                         feature_version="v2")
    v1 = store.read_features("bitcoin", "1d")
    v2 = store.read_features("bitcoin", "1d", feature_version="v2")
    assert v1[0]["rsi"] == 30.0   # histórico de v1 intacto
    assert v2[0]["rsi"] == 55.0


def test_mesma_versao_continua_upsert_idempotente(store):
    store.write_features("bitcoin", "1d", [{"ts": TS, "rsi": 30.0}])
    store.write_features("bitcoin", "1d", [{"ts": TS, "rsi": 31.0}])
    rows = store.read_features("bitcoin", "1d")
    assert len(rows) == 1 and rows[0]["rsi"] == 31.0


def test_serving_default_le_v1(store):
    store.write_features("bitcoin", "1d", [{"ts": TS, "rsi": 30.0}])
    store.write_features("bitcoin", "1d", [{"ts": TS, "rsi": 99.0}],
                         feature_version="v2")
    assert store.latest_features("bitcoin", "1d")["rsi"] == 30.0
