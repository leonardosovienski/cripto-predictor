"""Gate técnico de reabertura de hipótese/família encerrada.

Trava do bloco 19 do congelamento científico: nenhuma família em
``frozen_families`` (charters/scientific_state.json) pode ser reaberta ou
reparametrizada silenciosamente. Este script é o mecanismo TÉCNICO que faz
valer essa política escrita — sem ele, "não reabrir sem dossiê completo" é
só uma frase em markdown que ninguém é obrigado a obedecer.

Uso:
    python -m scripts.check_reopen_dossier --family funding_oi_hmm_v3 \\
        --dossier path/to/dossier.json

O dossiê precisa ser um JSON com os seis campos exigidos, todos não-vazios:
    previous_result
    closure_reason
    new_information
    causal_reason
    why_old_test_no_longer_answers_question
    new_protocol

Sem dossiê válido para uma família listada em ``frozen_families``, o script
sai com código 1 e a família continua fechada. Isto NÃO decide se a
reabertura é uma boa ideia — só impede reabertura silenciosa sem o mínimo de
documentação causal exigido. A decisão de mérito continua humana.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARTER_PATH = ROOT / "charters" / "scientific_state.json"

REQUIRED_FIELDS = (
    "previous_result",
    "closure_reason",
    "new_information",
    "causal_reason",
    "why_old_test_no_longer_answers_question",
    "new_protocol",
)


def load_frozen_families(charter_path: Path = CHARTER_PATH) -> list[str]:
    charter = json.loads(charter_path.read_text(encoding="utf-8"))
    return list(charter.get("frozen_families", []))


def validate_dossier(dossier: dict) -> list[str]:
    """Retorna a lista de problemas encontrados; lista vazia = dossiê válido."""
    problems = []
    for field in REQUIRED_FIELDS:
        value = dossier.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            problems.append(f"campo obrigatório ausente ou vazio: {field}")
    return problems


def check_reopen(family: str, dossier_path: Path | None) -> int:
    frozen = load_frozen_families()
    if family not in frozen:
        print(f"'{family}' não está em frozen_families — nada a validar aqui.")
        return 0

    if dossier_path is None or not dossier_path.exists():
        print(
            f"BLOQUEADO: família '{family}' está congelada (frozen_families) e "
            f"nenhum dossiê de reabertura foi fornecido. Reabertura silenciosa "
            f"não é permitida (bloco 19)."
        )
        return 1

    dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
    problems = validate_dossier(dossier)
    if problems:
        print(f"BLOQUEADO: dossiê de reabertura de '{family}' está incompleto:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(
        f"Dossiê de reabertura de '{family}' contém os seis campos exigidos. "
        f"Isto NÃO aprova a reabertura — só confirma que a documentação causal "
        f"mínima existe. A decisão de mérito segue sendo humana."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, help="Nome da família (frozen_families)")
    parser.add_argument(
        "--dossier", type=Path, default=None, help="Caminho do JSON com o dossiê de reabertura"
    )
    args = parser.parse_args()
    return check_reopen(args.family, args.dossier)


if __name__ == "__main__":
    sys.exit(main())
