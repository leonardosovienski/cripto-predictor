"""Instante canônico do funding e o arquivo de preços com nome antigo.

O fundingRate do data.binance.vision grava calc_time alguns ms depois da hora programada. Com a checagem de
cadência exata de 8h do feature_builder, dados do próprio vision_ingest davam 0 vetores (controle do H7/H9,
docs/evidence/2026-09-28-b4-controle-h7-h9). O instante do evento passa a ser a hora cheia quando o desvio é de até
100 ms (o observado é 0–47 ms); acima disso fica como veio, para que uma anomalia real continue visível.
"""

import random

import pytest

from GarimpoInvestimentos.v3 import backtest_v3 as wfa
from GarimpoInvestimentos.v3.collectors.funding_collector import (
    FundingRecord,
    load_funding_csv,
    save_funding_csv,
    scheduled_funding_time,
)
from GarimpoInvestimentos.v3.collectors.oi_collector import OIRecord, save_oi_csv
from GarimpoInvestimentos.v3.collectors.spot_collector import KlineRecord, save_spot_csv
from GarimpoInvestimentos.v3.feature_builder import build_feature_vectors

HOUR = 3_600_000
ORIGIN = 1_609_459_200_000  # 2021-01-01T00:00:00Z


def test_scheduled_funding_time_keeps_only_the_recording_jitter_out():
    assert scheduled_funding_time(ORIGIN) == ORIGIN
    assert scheduled_funding_time(ORIGIN + 2) == ORIGIN
    assert scheduled_funding_time(ORIGIN + 47) == ORIGIN
    assert scheduled_funding_time(ORIGIN - 3) == ORIGIN
    assert scheduled_funding_time(ORIGIN + 100) == ORIGIN
    # acima do ruído de gravação: não arredonda
    assert scheduled_funding_time(ORIGIN + 101) == ORIGIN + 101
    assert scheduled_funding_time(1_000) == 1_000  # instante sintético qualquer, fora da tolerância
    assert scheduled_funding_time(ORIGIN + 8 * HOUR - 5) == ORIGIN + 8 * HOUR


def _jittered_funding(n: int, rng: random.Random) -> list[FundingRecord]:
    return [
        FundingRecord(
            "BTCUSDT", ORIGIN + i * 8 * HOUR + rng.randint(0, 47), rng.uniform(-1e-3, 1e-3), 0.0
        )
        for i in range(n)
    ]


def test_csv_with_raw_vision_times_is_read_on_the_hour(tmp_path):
    rng = random.Random(7)
    raw = _jittered_funding(10, rng)
    path = tmp_path / "funding.csv"
    save_funding_csv(raw, path)
    loaded = load_funding_csv(path)
    assert [r.funding_time_ms for r in loaded] == [ORIGIN + i * 8 * HOUR for i in range(10)]
    assert [r.funding_rate for r in loaded] == [r.funding_rate for r in raw]


def test_feature_builder_builds_vectors_from_vision_funding(tmp_path):
    rng = random.Random(11)
    n = 130
    funding = _jittered_funding(n, rng)
    hours = n * 8 + 2
    oi = {ORIGIN + k * 5 * 60_000: 2e9 + rng.uniform(-1e7, 1e7) for k in range(-30, hours * 12)}
    spot = {ORIGIN + h * HOUR: 30_000.0 * (1 + rng.uniform(-0.01, 0.01)) for h in range(-30, hours)}
    rates = [r.funding_rate for r in funding]

    raw_times = [r.funding_time_ms for r in funding]
    assert build_feature_vectors(raw_times, rates, oi, spot, "BTCUSDT", fr_window=90) == []

    path = tmp_path / "funding.csv"
    save_funding_csv(funding, path)
    canonical = [r.funding_time_ms for r in load_funding_csv(path)]
    vectors = build_feature_vectors(canonical, rates, oi, spot, "BTCUSDT", fr_window=90)
    assert len(vectors) == n - 90 + 1


def test_backtest_names_the_legacy_spot_file(tmp_path, monkeypatch):
    rng = random.Random(3)
    sym_dir = tmp_path / "BTCUSDT"
    sym_dir.mkdir()
    save_funding_csv(_jittered_funding(400, rng), sym_dir / "funding.csv")
    save_oi_csv(
        [OIRecord("BTCUSDT", ORIGIN + i * HOUR, 30_000.0, 1e9) for i in range(400 * 8)],
        sym_dir / "oi.csv",
    )
    save_spot_csv(
        [KlineRecord("BTCUSDT", ORIGIN + i * HOUR, 30_000.0, 10.0) for i in range(400 * 8)],
        sym_dir / "spot_1h.csv",
    )
    monkeypatch.setattr(wfa, "_DATA_ROOT", tmp_path)
    monkeypatch.setenv("CRIPTO_RUN_LEDGER", str(tmp_path / "runs.jsonl"))
    with pytest.raises(FileNotFoundError, match="spot_1h.csv"):
        wfa.run_wfa("BTCUSDT")
