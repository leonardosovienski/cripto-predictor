"""H7 (macro/DXY): build_macro_event_dummy / build_dxy_return — puras, sem rede."""

from datetime import UTC, date, datetime

import pytest

from GarimpoInvestimentos.dpl.macro_calendar import MacroEvent
from GarimpoInvestimentos.v3.feature_builder import FeatureVector
from GarimpoInvestimentos.v3.macro_features import (
    build_dxy_return,
    build_macro_event_dummy,
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
