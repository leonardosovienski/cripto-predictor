"""A/B: com os defaults (spread 0), o modelo do run_wfa dá o MESMO resultado no main e na branch.

Uso: <python do venv> ab_model_unchanged.py <dir_saida>
Dados: CSVs sintéticos determinísticos (mesmo gerador dos testes do Prompt 3a), HMM real.
"""

import json
import math
import os
import random
import sys
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

HOUR = 3_600_000
START = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() * 1000)
out = Path(sys.argv[1])
root = Path(tempfile.mkdtemp()) / "v3"
sym = root / "BTCUSDT"
sym.mkdir(parents=True)
rng = random.Random(7)
days = 250
with (sym / "funding.csv").open("w", encoding="utf-8") as f:
    f.write("symbol,funding_time_ms,funding_rate,mark_price\n")
    for i in range(days * 3):
        spike = 0.02 if i % 17 == 0 else 0.0
        f.write(f"BTCUSDT,{START + i * 8 * HOUR},{rng.gauss(0, 0.00005) + spike:.8f},{30000.0 + 500.0 * math.sin(i / 13.0):.2f}\n")
with (sym / "oi.csv").open("w", encoding="utf-8") as f:
    f.write("symbol,timestamp_ms,oi_contracts,oi_notional_usd\n")
    for i in range(days * 3):
        n = 1_000_000.0 + 50_000.0 * math.sin(i / 11.0)
        f.write(f"BTCUSDT,{START + i * 8 * HOUR},{n / 30000.0:.4f},{n:.2f}\n")
with (sym / "spot_binance_1h.csv").open("w", encoding="utf-8") as f:
    f.write("symbol,open_ms,close,volume\n")
    for i in range(days * 24):
        f.write(f"BTCUSDT,{START + i * HOUR},{30000.0 + 500.0 * math.sin(i / 104.0) + 40.0 * math.sin(i / 3.0):.2f},100.0\n")
os.environ["CRIPTO_RUN_LEDGER"] = str(root.parent / "ledger.jsonl")

from GarimpoInvestimentos.v3 import backtest_v3 as wfa  # noqa: E402

wfa._DATA_ROOT = root
r = wfa.run_wfa("BTCUSDT", fr_zscore_threshold=0.1, min_regime_confidence=0.0)
artifact = json.loads(Path(r.returns_artifact).read_text(encoding="utf-8"))
keys = ["n_folds", "aggregate_psr", "aggregate_ic", "aggregate_ic_ci_lower", "aggregate_max_dd", "aggregate_sharpe",
        "aggregate_sortino", "aggregate_calmar", "aggregate_gross_return", "aggregate_net_return", "net_ci_lower",
        "net_ci_upper", "diagnostic_verdict", "final_verdict"]
summary = {k: getattr(r, k) for k in keys}
summary["folds"] = [{k: v for k, v in asdict(f).items() if k not in ("is_last_train_ms", "oos_first_test_ms")} for f in r.folds]
summary["net_series"] = artifact["net"]
summary["gross_series"] = artifact["gross"]
out.write_text(json.dumps(summary, sort_keys=True, indent=1), encoding="utf-8")
print(json.dumps({k: summary[k] for k in keys}))
