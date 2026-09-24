"""Mutantes do CPCV: cada um precisa derrubar ao menos um teste do Prompt 3b.

Uso (na raiz do repositório): <python do venv> mutation_check.py
Nada é gravado: cada mutante é compilado em memória e trocado no módulo de teste.
"""

import sys
import types
from pathlib import Path

import tests.test_evaluation_protocol_3b as t

SOURCE = Path("GarimpoInvestimentos/research/cpcv.py").read_text(encoding="utf-8")
PURGE = "if any(label.start <= t1 and label.available >= t0"
EMBARGO = "elif any(t1 < label.start <= t1 + embargo"
MUTANTS = {
    "sem_purga": (PURGE, "if False and " + PURGE.removeprefix("if ")),
    "purga_por_end": ("label.available >= t0", "label.end >= t0"),
    "janela_por_end": (
        "max(labels[i].available for i in idx)",
        "max(labels[i].end for i in idx)",
    ),
    "sem_embargo": (EMBARGO, "elif False and " + EMBARGO.removeprefix("elif ")),
    "embargo_curto": ("t1 < label.start <= t1 + embargo", "t1 < label.start < t1 + embargo"),
}
PROPERTY = "test_no_forbidden_pair_with_irregular_labels_and_late_availability"
TESTS = [
    name
    for name in dir(t)
    if name.startswith("test_") and any(k in name for k in ("purge", "pair", "embargo", "paths"))
]

all_killed = True
for mutant, (old, new) in MUTANTS.items():
    assert SOURCE.count(old) == 1, mutant
    module = types.ModuleType("cpcv_mutant")
    sys.modules["cpcv_mutant"] = module
    exec(compile(SOURCE.replace(old, new), "cpcv_mutant", "exec"), module.__dict__)
    t.cpcv = module
    failed = []
    for name in TESTS:
        cases = [{"seed": s} for s in range(25)] if name == PROPERTY else [{}]
        for kwargs in cases:
            try:
                getattr(t, name)(**kwargs)
            except AssertionError:
                failed.append(name)
                break
    print(f"{mutant}: {'MORTO' if failed else 'SOBREVIVEU'} {sorted(failed)}")
    all_killed &= bool(failed)
print("TODOS_MORTOS" if all_killed else "HA_SOBREVIVENTE")
