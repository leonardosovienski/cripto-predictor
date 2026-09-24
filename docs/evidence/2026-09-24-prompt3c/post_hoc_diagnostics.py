"""Diagnóstico DESCRITIVO e pós-hoc (não pré-registrado): cobertura e largura do intervalo 10-90%
e viés da mediana, por previsor. Não muda nenhum status do Prompt 3c; só ajuda a ler o resultado.

Uso (na raiz do repositório): <python do venv> post_hoc_diagnostics.py <forecasts.json> <saida.json>
"""

import json
import statistics
import sys
from pathlib import Path

from GarimpoInvestimentos.research import fm_zero_shot as fz

prereg, _ = fz.load_preregistration()
series = fz.load_daily_series(prereg["data"])
period = prereg["evaluation_period"]
idx = fz.target_indices(
    series,
    first_ms=fz.parse_utc_ms(period["first_target_open_utc"]),
    last_ms=fz.parse_utc_ms(period["last_target_open_utc"]),
)
returns = fz.log_returns(series.close)
ys = [returns[j] for j in idx]
doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
forecasts = {"chronos_bolt_small": fz.candidate_forecasts(doc, prereg, series, idx)}
forecasts.update(fz.baseline_forecasts(returns, idx, prereg["forecast"]["quantile_levels"]))
out = {}
for name, fs in forecasts.items():
    inside = [f[0.1] <= y <= f[0.9] for y, f in zip(ys, fs, strict=True)]
    out[name] = {
        "coverage_10_90": sum(inside) / len(inside),
        "mean_width_10_90": statistics.fmean(f[0.9] - f[0.1] for f in fs),
        "mean_median": statistics.fmean(f[0.5] for f in fs),
        "share_median_positive": sum(f[0.5] > 0 for f in fs) / len(fs),
    }
out["realized"] = {
    "mean_log_return": statistics.fmean(ys),
    "stdev_log_return": statistics.stdev(ys),
}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(out, indent=1))
