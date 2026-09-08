"""Lógica pura da equivalência DPL vs direto (compare_asset — sem rede)."""

from GarimpoInvestimentos.analyzers.equivalence import compare_asset
from GarimpoInvestimentos.dpl.feature_engineering import INDICATOR_KEYS

_IND = {k: 10.0 for k in INDICATOR_KEYS}
_CHG = {"change_24h": 1.5, "change_7d": 8.0, "change_30d": -3.0}


def test_series_identicas_sao_equivalentes():
    r = compare_asset(dict(_IND), dict(_IND) | dict(_CHG), dict(_CHG))
    assert r["ok"]
    assert all(d == 0.0 for d in r["indicadores"].values())


def test_divergencia_de_indicador_reprova():
    dpl = dict(_IND) | dict(_CHG)
    dpl["rsi_14"] = 10.0001  # dados diferentes → reprova
    r = compare_asset(dict(_IND), dpl, dict(_CHG))
    assert not r["ok"]


def test_diff_de_change_e_reportado_mas_nao_reprova():
    # rolling vs calendário: divergência SEMÂNTICA — quantificada, não é falha
    dpl = dict(_IND) | {"change_24h": 0.9, "change_7d": 8.0, "change_30d": -3.0}
    r = compare_asset(dict(_IND), dpl, dict(_CHG))
    assert r["ok"]
    assert r["changes"]["change_24h"] == (1.5, 0.9, 0.6)


def test_indicador_ausente_dos_dois_lados_ok_de_um_so_reprova():
    sem = {k: v for k, v in _IND.items() if k != "sma_200"}
    ok = compare_asset(dict(sem), dict(sem) | dict(_CHG), dict(_CHG))
    assert ok["ok"]  # série curta nos DOIS lados: coerente
    torto = compare_asset(dict(_IND), dict(sem) | dict(_CHG), dict(_CHG))
    assert not torto["ok"]  # só um lado tem SMA-200: dados difere
