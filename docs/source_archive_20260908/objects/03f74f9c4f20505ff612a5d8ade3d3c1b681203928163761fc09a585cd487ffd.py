"""dpl/business_days — fonte única da semântica de defasagem de publicação.

Criado na auditoria de 2026-09-05: a duplicação dessa regra entre o
`DXYProvider` e `v3/macro_features` já causou um look-ahead real (o PR #83
corrigiu só uma das cópias). Estes testes travam a regra num lugar só.
"""

from datetime import UTC, date, datetime

import pytest

from GarimpoInvestimentos.dpl.business_days import add_business_days, published_at


class TestAddBusinessDays:
    def test_lag_zero_e_identidade(self):
        assert add_business_days(date(2026, 9, 4), 0) == date(2026, 9, 4)

    def test_sexta_mais_um_dia_util_e_segunda(self):
        """O caso que motivou tudo: sexta + 1 dia ÚTIL = segunda, não sábado."""
        assert add_business_days(date(2026, 9, 4), 1) == date(2026, 9, 7)

    def test_dia_util_comum_avanca_um_dia(self):
        assert add_business_days(date(2026, 9, 2), 1) == date(2026, 9, 3)

    def test_atravessa_fim_de_semana_acumulando(self):
        # quinta + 3 úteis -> sex, seg, ter
        assert add_business_days(date(2026, 9, 3), 3) == date(2026, 9, 8)

    def test_partindo_de_sabado_cai_na_segunda(self):
        assert add_business_days(date(2026, 9, 5), 1) == date(2026, 9, 7)

    def test_preserva_o_tipo_datetime(self):
        """O provider carimba `published_at` com datetime; as features do V3
        usam date. Uma implementação serve os dois."""
        out = add_business_days(datetime(2026, 9, 4, 12, 30, tzinfo=UTC), 1)
        assert isinstance(out, datetime)
        assert out == datetime(2026, 9, 7, 12, 30, tzinfo=UTC)

    def test_n_negativo_e_erro(self):
        with pytest.raises(ValueError, match="negativo"):
            add_business_days(date(2026, 9, 4), -1)


class TestPublishedAt:
    def test_close_de_sexta_so_publica_na_segunda(self):
        assert published_at(date(2026, 9, 4), 1) == date(2026, 9, 7)

    def test_predicado_de_disponibilidade_barra_o_fim_de_semana(self):
        """A forma como os consumidores devem usar: `published_at(obs) <= t`."""
        sexta = date(2026, 9, 4)
        assert not published_at(sexta, 1) <= date(2026, 9, 5)  # sábado
        assert not published_at(sexta, 1) <= date(2026, 9, 6)  # domingo
        assert published_at(sexta, 1) <= date(2026, 9, 7)  # segunda

    def test_lag_zero_publica_no_proprio_dia(self):
        assert published_at(date(2026, 9, 4), 0) == date(2026, 9, 4)


def test_dxy_provider_usa_o_helper_canonico():
    """Trava anti-divergência: se o provider voltar a ter cópia própria da
    regra, este teste cai — foi a divergência que criou o look-ahead."""
    from GarimpoInvestimentos.dpl.providers import dxy

    assert dxy._add_business_days is add_business_days
