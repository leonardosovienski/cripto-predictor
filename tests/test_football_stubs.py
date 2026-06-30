"""Testes offline dos contratos da Fase 5 — MatchDataProvider e os stubs de rede.

Os provedores de rede (Sofascore, FBref, odds, clima) permanecem stubs, mas suas
INTERFACES são exercidas: confirmamos que cumprem o contrato MatchDataProvider, têm
nome estável, integram o EntityMapper e falham de forma previsível (NotImplementedError)
até serem implementados quando wc-predictor-v2 sair do PARKED.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from GarimpoInvestimentos.dpl import EntityMapper, EventAlignmentEngine, MatchObservation
from GarimpoInvestimentos.dpl.events import MatchDataProvider
from GarimpoInvestimentos.dpl.providers.football_stubs import (
    FBrefProvider,
    OddsProvider,
    SofascoreProvider,
    WeatherProvider,
)

UTC = timezone.utc
_STUBS = [SofascoreProvider, FBrefProvider, OddsProvider, WeatherProvider]


def test_stubs_implementam_o_contrato(tmp_path):
    em = EntityMapper(tmp_path / "em.db")
    for cls in _STUBS:
        prov = cls(em)
        assert isinstance(prov, MatchDataProvider)
        assert prov.name and prov.name != "abstract_match"  # nome estável
    em.close()


def test_stubs_nomes_unicos(tmp_path):
    em = EntityMapper(tmp_path / "em.db")
    nomes = {cls(em).name for cls in _STUBS}
    assert nomes == {"sofascore", "fbref", "odds", "weather"}
    em.close()


def test_stub_de_rede_falha_previsivel(tmp_path):
    em = EntityMapper(tmp_path / "em.db")
    prov = SofascoreProvider(em)
    with pytest.raises(NotImplementedError):
        asyncio.run(prov.fetch_matches(limit=5))
    em.close()


def test_match_observation_pre_e_pos_jogo():
    """O contrato permite pré-jogo (published_at < kickoff) e pós-jogo (>)."""
    ts = datetime(2026, 6, 10, 18, tzinfo=UTC)
    pre = MatchObservation("odds", "m1", ts, "brazil", "argentina",
                           published_at=ts - timedelta(hours=2), payload={"odd_home": 1.8})
    pos = MatchObservation("fbref", "m1", ts, "brazil", "argentina",
                           published_at=ts + timedelta(hours=2), payload={"xg_home": 2.1})
    assert pre.published_at < pre.kickoff < pos.published_at


def test_event_align_ignora_observacao_pos_jogo():
    """Garantia central: estatística pós-jogo (published_at > kickoff) NÃO entra na
    própria partida (seria vazamento)."""
    from GarimpoInvestimentos.dpl import SignalPoint
    ts = datetime(2026, 6, 10, 18, tzinfo=UTC)
    m = MatchObservation("martj42", "m1", ts, "brazil", "argentina",
                         published_at=ts + timedelta(hours=3))
    # xg só publicado APÓS o jogo
    xg = [SignalPoint("xg", ts, 2.1, "fbref", ts + timedelta(hours=2))]
    rows = EventAlignmentEngine().align([m], {"xg": xg})
    import math
    assert math.isnan(rows[0]["xg"])  # pós-jogo não vaza para a própria partida
