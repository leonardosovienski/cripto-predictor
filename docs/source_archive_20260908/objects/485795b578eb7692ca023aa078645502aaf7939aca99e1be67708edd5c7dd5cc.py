"""Gera/verifica o snapshot congelado e auditável da definição científica de H6.

Motivação: antes de retomar a coleta prospectiva de H6 (n=6 -> 30), o projeto
exige um registro imutável do que exatamente está sendo testado — para que
nenhuma mudança de runtime (correção operacional, refactor, bugfix) possa
alterar a semântica científica da hipótese em silêncio. Se o hash divergir do
gravado em `charters/h6_definition_frozen.json`, ISSO PRECISA SER INVESTIGADO
antes de deixar a coleta continuar: ou foi uma mudança inofensiva
(reformatação, docstring) e o snapshot deve ser regenerado com justificativa
no commit, ou a definição da hipótese mudou e H6 precisaria virar uma trial
NOVA em vez de continuar como H6.

Uso:
    python -m scripts.freeze_h6_definition            # gera/atualiza o snapshot
    python -m scripts.freeze_h6_definition --check     # falha (exit 1) se o hash
                                                        # atual do código divergir
                                                        # do snapshot gravado
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKTEST_PY = ROOT / "GarimpoInvestimentos" / "analyzers" / "backtest.py"
TRIALS_JSON = ROOT / "GarimpoInvestimentos" / "trials.json"
OUT_PATH = ROOT / "charters" / "h6_definition_frozen.json"

H6_TRIAL_NAME = "h6-sinal-invertido-d7"

# Nomes das funções cujo CÓDIGO (não docstring) define a semântica científica
# de H6: se uma delas mudar, a hipótese pode ter mudado. Marcadores textuais
# simples (início/fim) — não é um parser de AST, é deliberadamente literal:
# qualquer edição dentro do bloco muda o hash, inclusive uma reformatação
# inofensiva. Isso é intencional (fail-loud > fail-silent nesta trava).
_FUNCTIONS = ["close_h6_inverted_signal", "h6_spearman_verdict"]


def _extract_function_source(text: str, func_name: str) -> str:
    marker = f"def {func_name}("
    start = text.index(marker)
    # próxima definição de função/classe no nível de módulo fecha o bloco
    rest = text[start + len(marker) :]
    end_markers = ["\ndef ", "\nclass ", "\n\n\n"]
    end = len(rest)
    for m in end_markers:
        idx = rest.find(m, 1)
        if idx != -1:
            end = min(end, idx)
    return marker + rest[:end]


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def build_snapshot() -> dict:
    trials = json.loads(TRIALS_JSON.read_text(encoding="utf-8"))
    h6_trial = next((t for t in trials if t.get("name") == H6_TRIAL_NAME), None)
    if h6_trial is None:
        raise SystemExit(f"trial '{H6_TRIAL_NAME}' não encontrada em {TRIALS_JSON}")

    backtest_src = BACKTEST_PY.read_text(encoding="utf-8")
    function_sources = {fn: _extract_function_source(backtest_src, fn) for fn in _FUNCTIONS}

    constants = {}
    for name in ("H6_TRIAL_NAME", "H6_LIVE_FONTE", "H6_MIN_N"):
        for line in backtest_src.splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{name} ="):
                constants[name] = stripped.split("#", 1)[0].split("=", 1)[1].strip()
                break

    code_blob = "\n".join(function_sources[fn] for fn in _FUNCTIONS) + json.dumps(
        constants, sort_keys=True
    )
    code_hash = hashlib.sha256(code_blob.encode("utf-8")).hexdigest()

    trial_blob = json.dumps(h6_trial, sort_keys=True)
    trial_hash = hashlib.sha256(trial_blob.encode("utf-8")).hexdigest()

    return {
        "H6_DEFINITION_FROZEN": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "as_of_commit": _git_commit(),
        "trial_id": H6_TRIAL_NAME,
        "trials_json_entry": h6_trial,
        "trials_json_entry_sha256": trial_hash,
        "governing_code": {
            "file": str(BACKTEST_PY.relative_to(ROOT)),
            "functions": _FUNCTIONS,
            "constants": constants,
        },
        "governing_code_sha256": code_hash,
        "rules": {
            "registered_at_lock": (
                "close_h6_inverted_signal/h6_spearman_verdict só aceitam "
                "pred_date > registered_at (trials.json). Não pode ser alterado "
                "sem virar uma trial nova."
            ),
            "min_n_gate": "n >= H6_MIN_N (30) antes de qualquer veredito ser calculado/impresso.",
            "reserved_fonte": (
                "params.fonte = 'reserved:h6-inversao-sinal' nunca casa com o "
                "mecanismo genérico de fechamento de trial — só o dedicado."
            ),
            "no_silent_change": (
                "Qualquer mudança de threshold, horizonte, ativos, provider, "
                "score transformation ou filtro DEVE ser registrada como hipótese "
                "nova e prospectiva. H6 nunca é reaberta/reparametrizada."
            ),
        },
        "note": (
            "Rode 'python -m scripts.freeze_h6_definition --check' antes de "
            "reativar a coleta de H6 e a cada deploy subsequente enquanto H6 "
            "estiver ACTIVE_PROSPECTIVE. Um hash divergente é bloqueante até "
            "investigação humana."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Falha (exit 1) se o hash do código/trial divergir do snapshot gravado.",
    )
    args = parser.parse_args(argv)

    fresh = build_snapshot()

    if args.check:
        if not OUT_PATH.exists():
            print(f"FAIL: {OUT_PATH} não existe — rode sem --check primeiro.", file=sys.stderr)
            return 1
        frozen = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        mismatches = []
        if frozen["governing_code_sha256"] != fresh["governing_code_sha256"]:
            mismatches.append("governing_code_sha256")
        if frozen["trials_json_entry_sha256"] != fresh["trials_json_entry_sha256"]:
            mismatches.append("trials_json_entry_sha256")
        if mismatches:
            print(
                f"FAIL: definição de H6 divergiu do snapshot congelado: {mismatches}. "
                "Investigue antes de continuar a coleta.",
                file=sys.stderr,
            )
            return 1
        print("OK: definição de H6 confere com o snapshot congelado.")
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(fresh, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Snapshot gravado em {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
