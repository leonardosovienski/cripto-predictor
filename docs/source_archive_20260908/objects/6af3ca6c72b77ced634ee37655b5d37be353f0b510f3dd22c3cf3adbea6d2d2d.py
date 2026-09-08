"""O README não pode divergir de `charters/scientific_state.json`.

Criado na auditoria de 2026-09-05. A tabela de hipóteses do README tinha
derivado do charter sem que nada percebesse:

  - H6 aparecia como "ATIVA / IMATURA" quando o charter já a marcava
    `CLOSED_NO_GO` (fechada em 2026-09-04, n=84);
  - H7 aparecia com trial "não registrada" quando `h7-macro-dxy-hmm-v1` existe
    no `trials.json` desde 2026-09-04;
  - H8 e H9 não apareciam de forma alguma;
  - o texto citava "7 tentativas" no denominador do DSR quando o registro já
    tinha 10 (e 26 após a reconciliação do mesmo dia).

O README é a porta de entrada do repositório: alguém lendo a tabela concluiria
que uma hipótese fechada continua aberta. O charter é a fonte de verdade —
travada em código —, então o README tem que segui-lo, não o contrário.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
CHARTER = REPO / "charters" / "scientific_state.json"

# Linha da tabela: | H7 | descrição | `trial` ou texto | **STATUS** — ... |
_LINHA = re.compile(r"^\|\s*(H\d+)\s*\|([^|]*)\|([^|]*)\|(.*)\|\s*$", re.MULTILINE)


def _linhas_do_readme() -> dict[str, tuple[str, str]]:
    """`{"H1": (coluna_trial, coluna_status)}` para cada linha H<N> do README."""
    texto = README.read_text(encoding="utf-8")
    return {m.group(1): (m.group(3).strip(), m.group(4).strip()) for m in _LINHA.finditer(texto)}


def _charter() -> dict:
    return json.loads(CHARTER.read_text(encoding="utf-8"))


def test_readme_lista_todas_as_hipoteses_do_charter():
    """Uma hipótese nova no charter sem linha no README deixa a porta de entrada
    do projeto incompleta — foi o que aconteceu com H8 e H9."""
    faltando = set(_charter()["hypotheses"]) - set(_linhas_do_readme())
    assert not faltando, (
        f"hipóteses no charter sem linha no README: {sorted(faltando)}. "
        "Acrescente a linha na tabela de 'Estado das hipóteses pré-registradas'."
    )


def test_readme_nao_inventa_hipotese_fora_do_charter():
    sobrando = set(_linhas_do_readme()) - set(_charter()["hypotheses"])
    assert not sobrando, f"README lista hipóteses que o charter não conhece: {sorted(sobrando)}"


def test_status_do_readme_bate_com_o_charter():
    """O caso concreto que a auditoria pegou: H6 anunciada como ATIVA no README
    enquanto o charter já dizia CLOSED_NO_GO."""
    charter = _charter()["hypotheses"]
    divergentes = []
    for h, (_, status_readme) in sorted(_linhas_do_readme().items()):
        esperado = charter[h]
        if esperado not in status_readme:
            divergentes.append(f"{h}: charter={esperado!r} mas README diz {status_readme[:60]!r}")
    assert not divergentes, "README divergente do charter:\n  " + "\n  ".join(divergentes)


def test_trial_citada_no_readme_bate_com_o_charter():
    """H7 aparecia como 'não registrada' com a trial já existindo no trials.json."""
    trials = _charter()["hypothesis_trials"]
    divergentes = []
    for h, (coluna_trial, _) in sorted(_linhas_do_readme().items()):
        if trials[h] not in coluna_trial:
            divergentes.append(f"{h}: esperado {trials[h]!r}, README traz {coluna_trial!r}")
    assert not divergentes, "coluna de trial divergente:\n  " + "\n  ".join(divergentes)
