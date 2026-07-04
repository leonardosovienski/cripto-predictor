"""Onda 0/1 — drift-check automático do vendor na suíte do consumidor.

Valida a integridade dos arquivos vendorizados de `vendor/predictor_core/` contra o
`CORE_MANIFEST.json`. Adulteração local de um arquivo do core dentro do domínio
(alguém "consertou" a matemática para mascarar um resultado), vendor dessincronizado
ou arquivo órfão viram FALHA de `pytest` — a detecção que o `sync_core.py --check` faz,
dentro do pytest de cada consumidor.

Onda 1: o manifesto passou a usar CAMINHOS RELATIVOS POSIX como chave (estrutura em
camadas kernel/ measurement/). Este teste valida diretamente o dict `files` do
manifesto — não replica a lógica de coleta do sync_core, só confere o que ele declarou.
"""
import hashlib
import json
from pathlib import Path

import pytest

VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "predictor_core"
MANIFEST = VENDOR / "CORE_MANIFEST.json"


def _iter_payload(root: Path):
    """Todos os arquivos vendorizados que contam como payload: *.py + VERSION,
    recursivo, ignorando __pycache__ e o próprio manifesto."""
    for p in root.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        if p.suffix == ".py" or p.name == "VERSION":
            yield p


@pytest.mark.skipif(not VENDOR.is_dir(), reason="domínio sem vendor/predictor_core/")
def test_vendor_manifest_present():
    assert MANIFEST.exists(), (
        "vendor/predictor_core/CORE_MANIFEST.json ausente — rode `sync_core.py --write`")


@pytest.mark.skipif(not MANIFEST.exists(), reason="manifesto ausente (coberto por outro teste)")
def test_each_file_hash_matches_manifest():
    """Cada arquivo listado no manifesto existe e seu sha256 bate (nada adulterado)."""
    files = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    for rel, expected in files.items():
        f = VENDOR / rel
        assert f.exists(), f"arquivo do manifesto ausente no vendor: {rel}"
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        assert got == expected, (
            f"DRIFT em {rel}: sha256 {got[:12]} != manifesto {expected[:12]} — "
            "o vendor foi editado localmente. NUNCA edite vendor/predictor_core/ à mão; "
            "corrija no canônico e rode o sync.")


@pytest.mark.skipif(not MANIFEST.exists(), reason="manifesto ausente")
def test_no_orphan_files_in_vendor():
    """Nenhum .py/VERSION no vendor além dos declarados no manifesto."""
    declared = set(json.loads(MANIFEST.read_text(encoding="utf-8"))["files"])
    present = {p.relative_to(VENDOR).as_posix() for p in _iter_payload(VENDOR)}
    assert present == declared, (
        f"árvore do vendor diverge do manifesto: "
        f"só no vendor={present - declared}, só no manifesto={declared - present}")


@pytest.mark.skipif(not MANIFEST.exists(), reason="manifesto ausente")
def test_aggregate_reproduces():
    """O agregado recalculado do dict de hashes bate com o declarado (mesma fórmula
    do sync_core.manifest: sha256(json.dumps(files, sort_keys=True))[:16])."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recomputed = hashlib.sha256(
        json.dumps(manifest["files"], sort_keys=True).encode()).hexdigest()[:16]
    assert recomputed == manifest["aggregate"]
