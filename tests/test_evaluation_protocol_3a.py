"""Prompt 3a: custos explícitos, walk-forward estrito, baselines no mesmo protocolo e manifesto.

Todos os testes rodam o `run_wfa` REAL sobre CSVs sintéticos gravados no tmp do teste (sem rede,
sem credenciais). Só o HMM e o gerador de sinal são trocados onde o teste mede contabilidade
(custos, separação temporal, crash); a reprodutibilidade usa o HMM real.
"""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from GarimpoInvestimentos.run_ledger import RunLedger, canonical_sha256
from GarimpoInvestimentos.v3 import backtest_v3 as wfa
from GarimpoInvestimentos.v3.cost_spec import CostSpec
from GarimpoInvestimentos.v3.costs import CostModel
from GarimpoInvestimentos.v3.timeindex import SortedTimeIndex

HOUR = 3_600_000
DAY = 24 * HOUR
START = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() * 1000)
TOTAL_DAYS = 250  # 2 folds: IS 180 + purga 7 + OOS 30 = 217; passo 30 -> 247


def _write_data(data_root, *, seed: int = 7, days: int = TOTAL_DAYS) -> None:
    sym = data_root / "BTCUSDT"
    sym.mkdir(parents=True)
    rng = random.Random(seed)
    n = days * 3
    with (sym / "funding.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "funding_time_ms", "funding_rate", "mark_price"])
        for i in range(n):
            spike = 0.02 if i % 17 == 0 else 0.0
            price = 30000.0 + 500.0 * math.sin(i / 13.0)
            w.writerow(
                [
                    "BTCUSDT",
                    START + i * 8 * HOUR,
                    f"{rng.gauss(0, 0.00005) + spike:.8f}",
                    f"{price:.2f}",
                ]
            )
    with (sym / "oi.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "timestamp_ms", "oi_contracts", "oi_notional_usd"])
        for i in range(n):
            notional = 1_000_000.0 + 50_000.0 * math.sin(i / 11.0)
            w.writerow(
                ["BTCUSDT", START + i * 8 * HOUR, f"{notional / 30000.0:.4f}", f"{notional:.2f}"]
            )
    with (sym / "spot_binance_1h.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "open_ms", "close", "volume"])
        for i in range(days * 24):
            price = 30000.0 + 500.0 * math.sin(i / 104.0) + 40.0 * math.sin(i / 3.0)
            w.writerow(["BTCUSDT", START + i * HOUR, f"{price:.2f}", "100.0"])


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    root = tmp_path / "data" / "v3"
    _write_data(root)
    monkeypatch.setattr(wfa, "_DATA_ROOT", root)
    monkeypatch.delenv("CRIPTO_RUN_LEDGER", raising=False)
    return root


def _ledger(data_root) -> RunLedger:
    return RunLedger(data_root.parent / "research_ledger" / "runs.jsonl")


class _NoRegimeEngine:
    """HMM trocado só nos testes de contabilidade: nenhum regime, nenhum ajuste."""

    def __init__(self, *, extra_features):
        self.extra_features = extra_features

    def fit(self, returns, volatility, *, extra_covariates):
        return None

    def predict_series(self, returns, volatility, *, extra_covariates):
        return [None] * len(returns)


def _stub_signals(monkeypatch, *, alternate: bool) -> None:
    counter = {"i": 0}

    def signal(feature, regime, **kwargs):
        counter["i"] += 1
        direction = (1 if counter["i"] % 2 else -1) if alternate else 1
        return SimpleNamespace(active=True, direction=direction, strength=1.0)

    monkeypatch.setattr(wfa, "RegimeEngine", _NoRegimeEngine)
    monkeypatch.setattr(wfa, "generate_signal", signal)


# ------------------------------------------------------------------ custos


def test_cost_spec_without_spread_is_the_historical_cost_model():
    spec = CostSpec()
    legacy = CostModel()
    for position, ratio in ((1.0, 1.0), (-0.5, 1.03), (0.2, 0.97)):
        assert spec.to_cost_model().friction(position, exit_price_ratio=ratio) == legacy.friction(
            position, exit_price_ratio=ratio
        )
    assert spec.per_leg_bps == 15.0
    assert CostSpec(taker_fee_bps=10, spread_bps=4, slippage_bps=5).per_leg_bps == 17.0
    with pytest.raises(ValueError):
        CostSpec(spread_bps=-1)


@pytest.mark.parametrize(
    "component", ["taker_fee_bps", "spread_bps", "slippage_bps"], ids=lambda c: c
)
def test_net_result_is_monotonic_non_increasing_in_each_cost(data_root, monkeypatch, component):
    """Estratégia sintética de turnover alto (direção alterna a cada decisão)."""
    _stub_signals(monkeypatch, alternate=True)
    base = {"taker_fee_bps": 0.0, "spread_bps": 0.0, "slippage_bps": 0.0}
    nets, gross, always_long = [], set(), []
    for level in (0.0, 1.0, 5.0, 20.0, 80.0):
        costs = {**base, component: level}
        result = wfa.run_wfa("BTCUSDT", fr_window=3, **costs)
        nets.append(result.aggregate_net_return)
        gross.add(round(result.aggregate_gross_return, 15))
        always_long.append(result.baselines["always_long"]["mean_net"])
    assert len(gross) == 1  # custo não muda o bruto
    assert all(b <= a for a, b in zip(nets, nets[1:])), nets
    assert all(b <= a for a, b in zip(always_long, always_long[1:])), always_long
    assert nets[-1] < nets[0]  # e o custo de fato morde com turnover alto


# ------------------------------------------------------------ walk-forward


def test_no_test_timestamp_is_at_or_before_the_last_training_timestamp(data_root, monkeypatch):
    _stub_signals(monkeypatch, alternate=False)
    result = wfa.run_wfa("BTCUSDT", fr_window=3)
    assert result.n_folds == 2
    for fold in result.folds:
        assert fold.is_last_train_ms < fold.is_end_ms <= fold.oos_start_ms <= fold.oos_first_test_ms
        assert fold.oos_first_test_ms > fold.is_last_train_ms
        assert fold.oos_first_test_ms - fold.is_last_train_ms >= wfa._PURGE_DAYS * DAY


def test_overlapping_folds_fail_closed_and_are_recorded(data_root, monkeypatch):
    _stub_signals(monkeypatch, alternate=False)
    monkeypatch.setattr(wfa, "_PURGE_DAYS", -8)  # OOS começaria dentro do IS
    with pytest.raises(RuntimeError, match="separação temporal estrita"):
        wfa.run_wfa("BTCUSDT", fr_window=3)
    last = _ledger(data_root).records()[-1]
    assert last["status"] == "CRASHED" and last["error"]["type"] == "RuntimeError"


# --------------------------------------------------------------- baselines


def test_baselines_use_the_same_decisions_costs_and_accounting_as_the_model(data_root, monkeypatch):
    _stub_signals(monkeypatch, alternate=False)  # modelo = sempre comprado, strength 1
    result = wfa.run_wfa("BTCUSDT", fr_window=3, taker_fee_bps=10, spread_bps=4, slippage_bps=5)
    b = result.baselines
    assert set(b) == {"random_walk", "naive_persistence", "always_long", "buy_and_hold", "protocol"}
    # mesmo protocolo: o baseline sempre-comprado reproduz o modelo sempre-comprado
    assert b["always_long"]["mean_net"] == pytest.approx(result.aggregate_net_return, rel=1e-12)
    assert b["always_long"]["mean_gross"] == pytest.approx(result.aggregate_gross_return, rel=1e-12)
    # passeio aleatório: previsão 0 -> nenhuma posição, nenhum custo
    assert b["random_walk"]["mean_net"] == 0.0 and b["random_walk"]["psr"] is None
    assert b["random_walk"]["n"] == b["always_long"]["n"] + b["always_long"]["n_unobservable"]
    assert b["buy_and_hold"]["n_folds"] == result.n_folds
    for fold in b["buy_and_hold"]["per_fold"]:
        # comprado paga o funding positivo dos dados sintéticos e um round trip de fricção
        assert fold["net"] < fold["gross"]
    assert b["protocol"]["costs"]["per_leg_bps"] == 17.0


def test_naive_persistence_uses_only_past_prices():
    base = {START + h * HOUR: 100.0 + h for h in range(48)}  # sobe até t
    t = START + 30 * HOUR
    for future in (-50.0, 50.0):  # o futuro não pode mudar a decisão
        prices = dict(base)
        prices.update({START + h * HOUR: 100.0 + h + future for h in range(30, 48)})
        assert wfa._naive_persistence_direction(t, 24, SortedTimeIndex(prices)) == 1
    falling = {k: 200.0 - (k - START) / HOUR for k in base}
    assert wfa._naive_persistence_direction(t, 24, SortedTimeIndex(falling)) == -1


# ------------------------------------------------------- reprodutibilidade


def test_same_config_dataset_and_seed_give_the_same_result(data_root):
    pytest.importorskip("hmmlearn")
    pytest.importorskip("sklearn")
    kwargs = {"fr_zscore_threshold": 0.1, "min_regime_confidence": 0.0}
    first = wfa.run_wfa("BTCUSDT", **kwargs)
    second = wfa.run_wfa("BTCUSDT", **kwargs)
    # Mesmo processo, mesma plataforma, seeds fixas (42..46): a expectativa é igualdade exata.
    # Tolerância 1e-12 relativa só absorve reordenação de ponto flutuante em BLAS.
    assert first.n_folds == second.n_folds >= 1
    for name in (
        "aggregate_psr",
        "aggregate_sharpe",
        "aggregate_net_return",
        "aggregate_gross_return",
        "aggregate_ic",
    ):
        assert getattr(first, name) == pytest.approx(getattr(second, name), rel=1e-12, abs=1e-15), (
            name
        )
    assert json.dumps(first.baselines, sort_keys=True) == json.dumps(
        second.baselines, sort_keys=True
    )
    started = [r for r in _ledger(data_root).records() if r["status"] == "STARTED"]
    completed = [r for r in _ledger(data_root).records() if r["status"] == "COMPLETED"]
    assert [r["attempt"] for r in started] == [1, 2]
    assert started[0]["config_sha256"] == started[1]["config_sha256"]
    assert completed[0]["dataset"]["dataset_sha256"] == completed[1]["dataset"]["dataset_sha256"]
    assert first.run_id != second.run_id


# ------------------------------------------------------- manifesto / ledger


def test_every_run_writes_a_complete_manifest(data_root, monkeypatch):
    _stub_signals(monkeypatch, alternate=True)
    result = wfa.run_wfa("BTCUSDT", fr_window=3, spread_bps=2)
    started, completed = _ledger(data_root).records()[-2:]
    assert started["run_id"] == completed["run_id"] == result.run_id
    assert started["status"] == "STARTED" and completed["status"] == "COMPLETED"
    for key in (
        "code",
        "config",
        "config_sha256",
        "costs",
        "validation_protocol",
        "model",
        "seeds",
        "policy",
        "attempt",
    ):
        assert key in started, key
    assert set(started["code"]) == {"package_version", "commit", "dirty", "source"}
    assert started["config"]["spread_bps"] == 2
    assert started["seeds"] == [42, 43, 44, 45, 46]
    assert started["policy"]["status"] == "NOT_DEFINED"
    assert started["validation_protocol"]["purge_days"] == wfa._PURGE_DAYS
    assert set(completed["dataset"]["input_sha256"]) == {
        "funding.csv",
        "oi.csv",
        "spot_binance_1h.csv",
    }
    assert completed["dataset"]["interval"]["funding_first_utc"].startswith("2026-01-01")
    assert completed["metrics"]["n_folds"] == result.n_folds
    assert completed["baselines"]["always_long"]["n"] > 0
    assert completed["artifacts"]["returns_json"] == result.returns_artifact


def test_crashed_run_is_recorded_and_the_error_propagates(data_root, monkeypatch):
    class _Broken(_NoRegimeEngine):
        def fit(self, returns, volatility, *, extra_covariates):
            raise FloatingPointError("EM não convergiu (sintético)")

    monkeypatch.setattr(wfa, "RegimeEngine", _Broken)
    with pytest.raises(FloatingPointError):
        wfa.run_wfa("BTCUSDT", fr_window=3)
    started, crashed = _ledger(data_root).records()[-2:]
    assert started["status"] == "STARTED" and crashed["status"] == "CRASHED"
    assert crashed["run_id"] == started["run_id"]
    assert crashed["error"]["type"] == "FloatingPointError"
    assert crashed["dataset"]["dataset_sha256"]  # insumos já identificados antes do crash


def test_invalid_configuration_is_recorded_as_crashed(data_root):
    with pytest.raises(ValueError):
        wfa.run_wfa("BTCUSDT", spread_bps=-1.0)
    started, crashed = _ledger(data_root).records()[-2:]
    assert started["costs"] is None and crashed["status"] == "CRASHED"
    assert crashed["error"]["type"] == "ValueError"


def test_ledger_is_append_only_and_hash_chained(data_root, monkeypatch):
    _stub_signals(monkeypatch, alternate=False)
    path = data_root.parent / "research_ledger" / "runs.jsonl"
    wfa.run_wfa("BTCUSDT", fr_window=3)
    before = path.read_bytes()
    wfa.run_wfa("BTCUSDT", fr_window=3, taker_fee_bps=12)
    after = path.read_bytes()
    assert after.startswith(before) and len(after) > len(before)  # nada reescrito, só acrescentado
    ledger = RunLedger(path)
    assert ledger.verify_chain() == []
    lines = after.decode().splitlines()
    tampered = json.loads(lines[0])
    tampered["attempt"] = 99
    forged = path.with_name("forged.jsonl")
    forged.write_text("\n".join([json.dumps(tampered)] + lines[1:]) + "\n", encoding="utf-8")
    assert RunLedger(forged).verify_chain()  # alteração de linha antiga é detectada
    assert canonical_sha256({"b": 1, "a": 2}) == canonical_sha256({"a": 2, "b": 1})
