"""Testes da Fase 5 (desenho) — EntityMapper, event-asof e Martj42 (CSV). Offline."""

import math
from datetime import UTC, datetime, timedelta

from GarimpoInvestimentos.dpl import EntityMapper, EventAlignmentEngine, SignalPoint
from GarimpoInvestimentos.dpl.entity_mapper import normalize
from GarimpoInvestimentos.dpl.events import MatchObservation
from GarimpoInvestimentos.dpl.providers.martj42 import Martj42Provider

UTC = UTC


# --- EntityMapper ------------------------------------------------------------


def test_normalize_remove_acento_e_caixa():
    assert normalize("  São   Paulo FC ") == "sao paulo fc"


def test_entity_mapper_resolve_e_unmapped(tmp_path):
    with EntityMapper(tmp_path / "em.db") as em:
        em.add_canonical("man_utd", "team", "Manchester United")
        em.add_alias("martj42", "team", "Man Utd", "man_utd")
        assert em.resolve("martj42", "man utd") == "man_utd"  # normalizado
        assert em.resolve("martj42", "Chelsea") is None  # não-mapeado, não adivinha


def test_entity_mapper_suggest_nao_aplica(tmp_path):
    with EntityMapper(tmp_path / "em.db") as em:
        em.add_canonical("man_utd", "team", "Manchester United")
        sugest = em.suggest("Manchester Utd", "team")
        assert "man_utd" in sugest  # sugere
        assert em.resolve("x", "Manchester Utd") is None  # mas NÃO mapeia sozinho


# --- Martj42 (CSV) -----------------------------------------------------------


def _mapper_com_times(tmp_path):
    em = EntityMapper(tmp_path / "em.db")
    em.add_canonical("brazil", "team", "Brazil")
    em.add_canonical("argentina", "team", "Argentina")
    em.add_alias("martj42", "team", "Brazil", "brazil")
    em.add_alias("martj42", "team", "Argentina", "argentina")
    return em


def test_martj42_parse_canonicaliza(tmp_path):
    em = _mapper_com_times(tmp_path)
    csv = (
        "date,home_team,away_team,home_score,away_score,tournament\n"
        "2026-06-01,Brazil,Argentina,2,1,Friendly\n"
    )
    obs = Martj42Provider(em).parse_csv(csv)
    assert len(obs) == 1
    assert obs[0].home_id == "brazil" and obs[0].away_id == "argentina"
    assert obs[0].payload["home_score"] == 2
    em.close()


def test_martj42_pula_nao_mapeado(tmp_path):
    em = _mapper_com_times(tmp_path)
    csv = (
        "date,home_team,away_team,home_score,away_score,tournament\n"
        "2026-06-01,Brazil,Narnia,3,0,Friendly\n"
    )  # Narnia não mapeado
    prov = Martj42Provider(em)
    obs = prov.parse_csv(csv)
    assert obs == []  # registro bloqueado
    assert ("martj42", "Narnia") in prov.unmapped  # registrado p/ curadoria
    em.close()


# --- EventAlignmentEngine (anti-vazamento pré-jogo) --------------------------


def _match(day, mid):
    ts = datetime(2026, 6, day, 18, tzinfo=UTC)
    return MatchObservation(
        "martj42", mid, ts, "brazil", "argentina", published_at=ts + timedelta(hours=3)
    )


def test_event_align_so_usa_info_antes_do_kickoff():
    matches = [_match(10, "m1"), _match(20, "m2")]
    # ranking publicado dia 5 (antes de m1) e dia 15 (antes de m2)
    rk = [
        SignalPoint(
            "rank", datetime(2026, 6, 5, tzinfo=UTC), 1.0, "fifa", datetime(2026, 6, 5, tzinfo=UTC)
        ),
        SignalPoint(
            "rank",
            datetime(2026, 6, 15, tzinfo=UTC),
            2.0,
            "fifa",
            datetime(2026, 6, 15, tzinfo=UTC),
        ),
    ]
    rows = EventAlignmentEngine().align(matches, {"rank": rk})
    assert rows[0]["rank"] == 1.0  # m1 (dia 10) só vê o ranking do dia 5
    assert rows[1]["rank"] == 2.0  # m2 (dia 20) vê o do dia 15


def test_event_align_nan_se_nada_publicado_antes():
    matches = [_match(1, "m0")]
    rk = [
        SignalPoint(
            "rank", datetime(2026, 6, 5, tzinfo=UTC), 1.0, "fifa", datetime(2026, 6, 5, tzinfo=UTC)
        )
    ]  # publicado DEPOIS do jogo
    rows = EventAlignmentEngine().align(matches, {"rank": rk})
    assert math.isnan(rows[0]["rank"])  # zero vazamento de informação futura
