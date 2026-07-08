"""Higiene do repositório — guarda contra o bug da classe "clone quebrado".

Incidente (2026-07-07): a regra não-ancorada `data/` no .gitignore engolia o
PACOTE vendor/predictor_core/data/ (código, não dados). O commit 20128f6
converteu dpl/* em shims que importam de predictor_core.data, mas o diretório
nunca entrou no git — qualquer clone fresco quebrava com 22 erros de coleta.
A suíte passava na máquina do autor (arquivos presentes, só que untracked),
então NENHUM teste pegava. Este módulo fecha essa lacuna: todo arquivo .py
importável do projeto precisa estar VISÍVEL ao git (não-ignorado).

Usa `git check-ignore` (barato, offline). Se o git não estiver disponível
(ex.: sdist sem .git), os testes são pulados — a CI, que roda num clone,
é o ponto de aplicação real.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_git = shutil.which("git")
_is_repo = (ROOT / ".git").exists()

pytestmark = pytest.mark.skipif(
    not (_git and _is_repo), reason="git indisponível ou fora de um clone")


def _python_payload() -> list[Path]:
    """Todos os .py dos pacotes de código do projeto (fora de venvs/caches)."""
    files = []
    for pkg in ("GarimpoInvestimentos", "vendor", "tests"):
        base = ROOT / pkg
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            parts = p.parts
            if "__pycache__" in parts or "env" in parts or ".venv_v3" in parts:
                continue
            files.append(p)
    return files


def test_no_code_file_is_gitignored():
    """Nenhum .py de pacote de código pode casar com regra do .gitignore.

    `git check-ignore` sai 0 quando ALGUM caminho passado está ignorado e
    imprime quais — a asserção mostra a lista exata para o diagnóstico.
    """
    files = _python_payload()
    assert files, "payload vazio — layout do repositório mudou?"
    rels = [str(p.relative_to(ROOT)) for p in files]
    # Em lotes, para não estourar o limite de linha de comando do Windows.
    ignored: list[str] = []
    for i in range(0, len(rels), 100):
        proc = subprocess.run(
            [_git, "-C", str(ROOT), "check-ignore", *rels[i:i + 100]],
            capture_output=True, text=True)
        if proc.returncode == 0:
            ignored.extend(proc.stdout.splitlines())
    assert not ignored, (
        "arquivos de CÓDIGO ignorados pelo .gitignore (clone fresco quebraria): "
        f"{ignored} — ancore a regra (ex.: '/data/' em vez de 'data/')")


def test_vendor_manifest_files_are_tracked():
    """Todo arquivo do CORE_MANIFEST está rastreado pelo git (não só presente).

    Presente-mas-untracked foi exatamente o modo de falha do incidente: a
    suíte local passa e o clone quebra. `git ls-files` é a verdade do índice.
    """
    import json
    manifest = ROOT / "vendor" / "predictor_core" / "CORE_MANIFEST.json"
    if not manifest.exists():
        pytest.skip("sem manifesto do vendor")
    declared = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    proc = subprocess.run(
        [_git, "-C", str(ROOT), "ls-files", "vendor/predictor_core"],
        capture_output=True, text=True, check=True)
    tracked = set(proc.stdout.splitlines())
    missing = [f"vendor/predictor_core/{rel}" for rel in declared
               if f"vendor/predictor_core/{rel}" not in tracked]
    assert not missing, (
        f"arquivos do manifesto NÃO rastreados pelo git: {missing} — "
        "commite-os (um clone fresco não os terá)")
