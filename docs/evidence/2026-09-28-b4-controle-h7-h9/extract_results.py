"""Controle do H7/H9 (B4 item 7): extrai os números dos logs do backtest_v3 para results.json.

Nenhum número é digitado: cada valor sai de uma linha do log citado (com sha256 do arquivo). Uso:
    python extract_results.py <pasta de logs da evidência> <results.json>
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

PATTERNS = {
    "feature_vectors": re.compile(r"(\d+) FeatureVectors construídos"),
    "dropped": re.compile(r"(\d+)/(\d+) timestamps descartados"),
    "folds": re.compile(r"Folds: (\d+) \| GO: (\d+) \| NO-GO: (\d+)"),
    "psr": re.compile(r"PSR agregado\s*:\s*(-?[\d.]+)"),
    "ic": re.compile(r"IC Spearman\s*:\s*(-?[\d.]+)\s+CI_lower:\s*(-?[\d.]+)"),
    "max_drawdown_pct": re.compile(r"Max Drawdown\s*:\s*(-?[\d.]+)%"),
    "sharpe": re.compile(r"Sharpe agregado:\s*(-?[\d.]+)"),
    "verdict": re.compile(r"VEREDICTO: (\S+)"),
    "error": re.compile(r"ERRO — (.+)$"),
}
FOLD = re.compile(
    r"fold (\d+): IC=(-?[\d.]+) \[(-?[\d.]+), (-?[\d.]+)\] PSR=(-?[\d.]+) MaxDD=(-?[\d.]+)% → (\S+)"
)
H9_REFERENCE = {
    "source": "GarimpoInvestimentos/trials.json (h9-oi-volume-ratio-hmm-v1) e docs/HYPOTHESES.md, 2026-09-04",
    "sharpe": -1.0041,
    "psr": 0.1621,
    "ic": 0.0283,
    "ic_ci_lower": -0.1476,
    "max_drawdown_pct": 11.49,
}


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    out: dict = {"log": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    for key, pattern in PATTERNS.items():
        m = None
        for line in text.splitlines():
            m = pattern.search(line) or m
        if m is None:
            continue
        if key == "folds":
            out["folds"], out["folds_go"], out["folds_no_go"] = map(int, m.groups())
        elif key == "dropped":
            out["dropped"], out["funding_records"] = map(int, m.groups())
        elif key == "ic":
            out["ic"], out["ic_ci_lower"] = map(float, m.groups())
        elif key in ("verdict", "error"):
            out[key] = m.group(1).strip()
        elif key == "feature_vectors":
            out[key] = int(m.group(1))
        else:
            out[key] = float(m.group(1))
    evaluable = [
        dict(
            zip(
                ("fold", "ic", "ic_lo", "ic_hi", "psr", "max_dd_pct", "status"),
                (int(g[0]), *map(float, g[1:6]), g[6]),
            )
        )
        for g in FOLD.findall(text)
        if g[6] in ("GO", "NO-GO")
    ]
    out["evaluable_folds"] = evaluable
    statuses: dict[str, int] = {}
    for g in FOLD.findall(text):
        statuses[g[6]] = statuses.get(g[6], 0) + 1
    no_signal = len(re.findall(r"fold \d+: sem sinais ativos no OOS", text))
    if statuses or no_signal:
        out["fold_status_counts"] = dict(sorted(statuses.items())) | {
            "SEM_SINAIS_ATIVOS": no_signal
        }
    return out


def main() -> int:
    logs, dest = Path(sys.argv[1]), Path(sys.argv[2])
    runs = {}
    for folder in sorted(p for p in logs.iterdir() if p.is_dir()):
        arms = {
            arm: parse(folder / f"controle_{arm}.log")
            for arm in ("A_baseline", "B_oivol")
            if (folder / f"controle_{arm}.log").exists()
        }
        if arms:
            runs[folder.name] = arms
    doc = {"schema": "cripto-b4-control/1", "h9_reference": H9_REFERENCE, "runs": runs}
    dest.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = [
        "| execução | braço | vetores | folds (avaliáveis) | Sharpe | PSR | IC [CI_lower] | MaxDD | erro |",
        "|---|---|--:|--:|--:|--:|--:|--:|---|",
    ]
    for name, arms in runs.items():
        for arm, r in arms.items():
            ic = f"{r['ic']:.4f} [{r['ic_ci_lower']:.4f}]" if "ic" in r else "-"
            folds = f"{r['folds']} ({r['folds_go'] + r['folds_no_go']})" if "folds" in r else "-"
            rows.append(
                f"| `{name}` | {arm} | {r.get('feature_vectors', '-')} | {folds} | {r.get('sharpe', '-')} | "
                f"{r.get('psr', '-')} | {ic} | {r.get('max_drawdown_pct', '-')}{'%' if 'max_drawdown_pct' in r else ''} | "
                f"{r.get('error', '')} |"
            )
    ref = H9_REFERENCE
    rows.append(
        f"| H9 (2026-09-04, produção) | B | - | 45 (1) | {ref['sharpe']} | {ref['psr']} | "
        f"{ref['ic']} [{ref['ic_ci_lower']}] | {ref['max_drawdown_pct']}% | |"
    )
    dest.with_name("results_table.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    for name, arms in runs.items():
        for arm, r in arms.items():
            print(
                name,
                arm,
                {
                    k: r.get(k)
                    for k in (
                        "feature_vectors",
                        "folds",
                        "folds_no_go",
                        "sharpe",
                        "psr",
                        "ic",
                        "ic_ci_lower",
                        "max_drawdown_pct",
                        "error",
                    )
                },
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
