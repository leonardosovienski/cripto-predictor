"""H7 (macro/DXY): build_macro_event_dummy / build_dxy_return — puras, sem rede."""

from datetime import UTC, date, datetime

import pytest

from GarimpoInvestimentos.dpl.macro_calendar import MacroEvent
from GarimpoInvestimentos.v3.feature_builder import FeatureVector
from GarimpoInvestimentos.v3.macro_features import (
    build_dxy_return,
    build_macro_event_dummy,
    dxy_coverage,
    load_dxy_daily_closes,
)


def _fv(day: date) -> FeatureVector:
    ts_ms = int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp() * 1000)
    return FeatureVector(
        timestamp_exchange_ms=ts_ms,
        asset="BTCUSDT",
        funding_rate_raw=0.0,
        oi_notional_usd=0.0,
        spot_close=1.0,
        funding_zscore=0.0,
        oi_log_delta=0.0,
        leverage_pressure=0.0,
        log_return_8h=0.0,
        realized_vol_24h=0.0,
        data_quality_score=1.0,
    )


class TestMacroEventDummy:
    def test_dentro_da_janela_marca_1(self):
        events = [MacroEvent(event_type="FOMC", event_date=date(2026, 9, 16))]
        vectors = [_fv(date(2026, 9, 15)), _fv(date(2026, 9, 16)), _fv(date(2026, 9, 17))]
        out = build_macro_event_dummy(vectors, window_days=1, events=events)
        assert out == [1.0, 1.0, 1.0]

    def test_fora_da_janela_marca_0(self):
        events = [MacroEvent(event_type="FOMC", event_date=date(2026, 9, 16))]
        vectors = [_fv(date(2026, 9, 1)), _fv(date(2026, 10, 1))]
        out = build_macro_event_dummy(vectors, window_days=1, events=events)
        assert out == [0.0, 0.0]

    def test_combina_tipos_com_or(self):
        events = [
            MacroEvent(event_type="CPI", event_date=date(2026, 9, 11)),
            MacroEvent(event_type="FOMC", event_date=date(2026, 9, 16)),
        ]
        vectors = [_fv(date(2026, 9, 11)), _fv(date(2026, 9, 16)), _fv(date(2026, 9, 13))]
        out = build_macro_event_dummy(vectors, window_days=0, events=events)
        assert out == [1.0, 1.0, 0.0]

    def test_window_days_negativo_e_erro(self):
        with pytest.raises(ValueError, match="negativo"):
            build_macro_event_dummy([], window_days=-1, events=[])


class TestDxyReturn:
    def test_retorno_calculado_com_lag(self):
        vectors = [_fv(date(2026, 9, 10))]
        closes = {
            date(2026, 9, 7): 100.0,
            date(2026, 9, 8): 102.0,  # (102-100)/100 = 2%
        }
        # ponto em 10/09, lag=1 -> cutoff=09/09 -> usa 08/09 (mais recente <= cutoff) vs 07/09
        out = build_dxy_return(vectors, closes, publish_lag_days=1)
        assert out == pytest.approx([2.0])

    def test_nunca_usa_dado_posterior_ao_cutoff(self):
        vectors = [_fv(date(2026, 9, 10))]
        closes = {
            date(2026, 9, 7): 100.0,
            date(2026, 9, 8): 102.0,
            date(2026, 9, 9): 999.0,  # == cutoff exato (10 - 1), USÁVEL
            date(2026, 9, 10): 1.0,  # posterior ao cutoff, NUNCA pode ser usado
        }
        out = build_dxy_return(vectors, closes, publish_lag_days=1)
        # usable = [07, 08, 09] -> latest=09 (999.0), prev=08 (102.0)
        assert out == pytest.approx([(999.0 - 102.0) / 102.0 * 100.0])

    def test_cobertura_insuficiente_retorna_zero_neutro(self):
        vectors = [_fv(date(2026, 1, 1))]  # nenhum dado DXY antes dessa data
        out = build_dxy_return(vectors, {date(2026, 9, 8): 102.0}, publish_lag_days=1)
        assert out == [0.0]

    def test_publish_lag_negativo_e_erro(self):
        with pytest.raises(ValueError, match="negativo"):
            build_dxy_return([], {}, publish_lag_days=-1)

    def test_fim_de_semana_nao_usa_close_de_sexta_ainda_nao_publicado(self):
        """Achado de auditoria externa (2026-09-05): com publish_lag_days=1 dia
        ÚTIL, o close de sexta-feira só é publicado na segunda seguinte —
        NUNCA pode ser usado num ponto de sábado ou domingo (seria olhar
        ~2 dias no futuro relativo à publicação real). 2026-09-04 é sexta,
        2026-09-05 sábado, 2026-09-06 domingo (calendário real)."""
        closes = {
            date(2026, 9, 2): 100.0,  # quarta
            date(2026, 9, 3): 101.0,  # quinta — publica sexta 09-04
            date(2026, 9, 4): 999.0,  # sexta — publica SEGUNDA 09-07, nao antes
        }
        sabado = build_dxy_return([_fv(date(2026, 9, 5))], closes, publish_lag_days=1)
        domingo = build_dxy_return([_fv(date(2026, 9, 6))], closes, publish_lag_days=1)
        esperado = (101.0 - 100.0) / 100.0 * 100.0  # quinta vs quarta, nunca sexta
        assert sabado == pytest.approx([esperado])
        assert domingo == pytest.approx([esperado])

    def test_segunda_ja_pode_usar_close_de_sexta(self):
        """No dia útil seguinte (segunda), o close de sexta já foi publicado —
        contraste direto com o teste de fim de semana acima."""
        closes = {
            date(2026, 9, 3): 101.0,  # quinta
            date(2026, 9, 4): 999.0,  # sexta — publica segunda 09-07
        }
        segunda = build_dxy_return([_fv(date(2026, 9, 7))], closes, publish_lag_days=1)
        esperado = (999.0 - 101.0) / 101.0 * 100.0
        assert segunda == pytest.approx([esperado])


class TestLoadDxyDailyCloses:
    def test_le_csv_valido(self, tmp_path):
        p = tmp_path / "dxy.csv"
        p.write_text("date,close\n2026-09-07,100.0\n2026-09-08,102.0\n", encoding="utf-8")
        out = load_dxy_daily_closes(p)
        assert out == {date(2026, 9, 7): 100.0, date(2026, 9, 8): 102.0}

    def test_linha_malformada_e_erro(self, tmp_path):
        p = tmp_path / "dxy.csv"
        p.write_text("date,close\n2026-09-07,100.0,extra\n", encoding="utf-8")
        with pytest.raises(ValueError, match="malformada"):
            load_dxy_daily_closes(p)

    def test_preco_invalido_e_erro(self, tmp_path):
        p = tmp_path / "dxy.csv"
        p.write_text("date,close\n2026-09-07,nao-e-numero\n", encoding="utf-8")
        with pytest.raises(ValueError, match="inválida"):
            load_dxy_daily_closes(p)

    def test_arquivo_vazio_e_erro(self, tmp_path):
        p = tmp_path / "dxy.csv"
        p.write_text("date,close\n", encoding="utf-8")
        with pytest.raises(ValueError, match="nenhum dado"):
            load_dxy_daily_closes(p)


class TestDxyLookaheadDiasUteis:
    """Regressão do look-ahead achado na auditoria de 2026-09-05.

    `build_dxy_return` contava a defasagem em dias CORRIDOS enquanto o
    `DXYProvider` já contava em dias ÚTEIS (PR #83). Num ponto de fim de semana
    a versão antiga usava o close de sexta, que só é publicado na segunda.
    """

    # 2026-09-04 = sexta | 05 = sábado | 06 = domingo | 07 = segunda
    CLOSES = {
        date(2026, 9, 2): 100.0,  # quarta
        date(2026, 9, 3): 101.0,  # quinta
        date(2026, 9, 4): 105.0,  # sexta — publicado só na segunda 07/09
    }

    def _ret_de_sexta(self) -> float:
        return (105.0 - 101.0) / 101.0 * 100.0

    @pytest.mark.parametrize("dia", [date(2026, 9, 5), date(2026, 9, 6)])
    def test_fim_de_semana_nao_enxerga_o_close_de_sexta(self, dia):
        """Sábado/domingo só conhecem quinta (03/09, publicada sexta)."""
        out = build_dxy_return([_fv(dia)], self.CLOSES, publish_lag_days=1)
        assert out != pytest.approx([self._ret_de_sexta()]), (
            f"{dia}: usou o close de sexta, que só é publicado na segunda — "
            "look-ahead de dias corridos voltou"
        )
        assert out == pytest.approx([(101.0 - 100.0) / 100.0 * 100.0])

    def test_segunda_ja_enxerga_o_close_de_sexta(self):
        """Na segunda 07/09 o dado de sexta está publicado — usar é correto."""
        out = build_dxy_return([_fv(date(2026, 9, 7))], self.CLOSES, publish_lag_days=1)
        assert out == pytest.approx([self._ret_de_sexta()])

    def test_lag_zero_nao_antecipa_publicacao(self):
        """Com lag=0 o close do próprio dia é conhecido no dia — mas nunca antes."""
        assert build_dxy_return([_fv(date(2026, 9, 4))], self.CLOSES, publish_lag_days=0) == (
            pytest.approx([self._ret_de_sexta()])
        )
        assert build_dxy_return([_fv(date(2026, 9, 3))], self.CLOSES, publish_lag_days=0) == (
            pytest.approx([(101.0 - 100.0) / 100.0 * 100.0])
        )


class TestDxyCoverage:
    def test_conta_pontos_imputados(self):
        closes = {date(2026, 9, 2): 100.0, date(2026, 9, 3): 101.0}
        vectors = [_fv(date(2026, 1, 1)), _fv(date(2026, 9, 4)), _fv(date(2026, 9, 7))]
        imputados, total = dxy_coverage(vectors, closes, publish_lag_days=1)
        assert (imputados, total) == (1, 3)  # só 01/01 fica sem dado suficiente

    def test_serie_vazia_imputa_tudo(self):
        vectors = [_fv(date(2026, 9, 7))]
        assert dxy_coverage(vectors, {}, publish_lag_days=1) == (1, 1)

    def test_lag_negativo_e_erro(self):
        with pytest.raises(ValueError, match="negativo"):
            dxy_coverage([], {}, publish_lag_days=-1)
