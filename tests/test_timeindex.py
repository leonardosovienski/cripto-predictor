"""timeindex (C5): paridade com as 3 cópias antigas + bordas do bisect."""
from GarimpoInvestimentos.v3.timeindex import SortedTimeIndex, nearest_value


def test_exact_hit():
    assert nearest_value({1000: 5.0, 2000: 7.0}, 2000) == 7.0


def test_nearest_within_tolerance():
    idx = {0: 1.0, 600_000: 2.0}
    assert nearest_value(idx, 250_000) == 1.0        # 250k de distância <= 300k
    assert nearest_value(idx, 350_000) == 2.0        # mais perto do 600k


def test_none_outside_tolerance():
    assert nearest_value({0: 1.0}, 1_000_000) is None


def test_empty_index():
    assert nearest_value({}, 123) is None


def test_tolerance_parametrizavel():
    idx = {0: 1.0}
    assert nearest_value(idx, 400_000, tolerance_ms=500_000) == 1.0
    assert nearest_value(idx, 400_000, tolerance_ms=100_000) is None


def test_bordas_do_bisect():
    """Alvo antes do primeiro e depois do último timestamp."""
    idx = {1_000_000: 1.0, 2_000_000: 2.0}
    assert nearest_value(idx, 900_000) == 1.0
    assert nearest_value(idx, 2_100_000) == 2.0


def test_sorted_index_reutilizavel():
    ti = SortedTimeIndex({0: 1.0, 300_000: 2.0})
    assert ti.nearest(10_000) == 1.0
    assert ti.nearest(290_000) == 2.0
