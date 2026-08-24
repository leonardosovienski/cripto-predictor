"""Cadeia de hash SHA-256 sobre `predictions_archive` — tamper-evidence.

Os triggers da migração 0016 garantem que todo estado de `predictions` é
arquivado (corretude operacional). Esta cadeia responde a pergunta seguinte:
**o archive foi adulterado retroativamente?** Cada linha selada carrega
`sha256(hash_anterior + "|" + serialização_canônica_da_linha)` — reescrever,
apagar ou reordenar qualquer linha antiga invalida todos os hashes seguintes.

Uso:
    seal_chain(conn)     → sela as linhas novas do archive (idempotente)
    verify_chain(conn)   → re-computa tudo e compara (detecta adulteração)
    chain_manifest(conn) → {"entries": n, "head": h} para publicar/commitar

O hash da ponta (`head`) é o anchor público: publicado em
`chain_manifest.json` pelo quality_snapshot e commitado à mão quando muda
(mesma convenção do `h6_status.json`). Quem tiver o manifest de ontem consegue
provar que nada anterior foi tocado — commit-and-reveal de uma pessoa só.

SQLite padrão não tem sha256, então o selo é computado aqui (Python), nunca
em trigger. A tabela da cadeia (migração 0017) é separada do archive de
propósito: o archive permanece 100% append-only, nem UPDATE de selo.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

GENESIS = "0" * 64

# Campos que entram na serialização canônica — espelha as colunas de
# predictions_archive (0016), na ordem declarada. archive_id NÃO entra no
# payload (já é a chave de ordenação); o encadeamento cobre a sequência.
_FIELDS = (
    "change_type",
    "archived_at",
    "ativo",
    "ts",
    "score",
    "sentimento",
    "resumo",
    "price_usd",
    "juiz",
    "divergencia",
    "fonte",
    "input_degradado",
    "llm_fallback",
    "news_provider",
    "news_degraded_reason",
    "collection_policy",
)


@dataclass(frozen=True)
class ChainReport:
    """Resultado de verify_chain. `ok=False` = adulteração detectada."""

    ok: bool
    checked: int  # linhas da cadeia verificadas
    unsealed: int  # linhas do archive ainda sem selo (normal entre selos)
    first_bad_archive_id: int | None = None
    detail: str = ""


def _canonical(row: sqlite3.Row) -> str:
    """Serialização determinística da linha do archive (ordem de chaves fixa,
    sem espaços — estável na mesma máquina/versão do Python, que é o caso de
    uso: verificação local contra o manifest publicado)."""
    payload = {f: row[f] for f in _FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(prev_hash: str, payload: str) -> str:
    return hashlib.sha256(f"{prev_hash}|{payload}".encode()).hexdigest()


def seal_chain(conn: sqlite3.Connection) -> int:
    """Sela as linhas do archive ainda sem hash. Idempotente; retorna quantas
    linhas novas foram seladas. Recusa selar se a ponta existente não
    verifica (selar sobre cadeia quebrada lavaria a adulteração)."""
    report = verify_chain(conn)
    if not report.ok:
        raise RuntimeError(
            f"cadeia de hash do archive NÃO verifica ({report.detail}) — "
            "selo recusado: investigue a adulteração antes de estender a cadeia"
        )
    cur = conn.execute(
        "SELECT chain_hash FROM predictions_archive_chain ORDER BY archive_id DESC LIMIT 1"
    ).fetchone()
    prev = cur[0] if cur else GENESIS
    rows = conn.execute(
        """SELECT a.* FROM predictions_archive a
           LEFT JOIN predictions_archive_chain c ON c.archive_id = a.archive_id
           WHERE c.archive_id IS NULL
           ORDER BY a.archive_id"""
    ).fetchall()
    sealed = 0
    for row in rows:
        prev = _digest(prev, _canonical(row))
        conn.execute(
            "INSERT INTO predictions_archive_chain (archive_id, chain_hash) VALUES (?, ?)",
            (row["archive_id"], prev),
        )
        sealed += 1
    if sealed:
        conn.commit()
    return sealed


def verify_chain(conn: sqlite3.Connection) -> ChainReport:
    """Re-computa a cadeia inteira e compara com o que está selado. Detecta:
    linha alterada (hash diverge), linha apagada do archive (archive_id
    selado ausente) e hash reescrito na tabela da cadeia."""
    chain = conn.execute(
        "SELECT archive_id, chain_hash FROM predictions_archive_chain ORDER BY archive_id"
    ).fetchall()
    if not chain:
        unsealed = conn.execute("SELECT COUNT(*) FROM predictions_archive").fetchone()[0]
        return ChainReport(ok=True, checked=0, unsealed=unsealed, detail="cadeia vazia")
    prev = GENESIS
    checked = 0
    for aid, expected in chain:
        row = conn.execute(
            "SELECT * FROM predictions_archive WHERE archive_id = ?", (aid,)
        ).fetchone()
        if row is None:
            return ChainReport(
                ok=False,
                checked=checked,
                unsealed=0,
                first_bad_archive_id=aid,
                detail=f"linha archive_id={aid} selada mas AUSENTE do archive (delete retroativo)",
            )
        actual = _digest(prev, _canonical(row))
        if actual != expected:
            return ChainReport(
                ok=False,
                checked=checked,
                unsealed=0,
                first_bad_archive_id=aid,
                detail=f"hash divergente em archive_id={aid} (linha ou cadeia reescrita)",
            )
        prev = expected
        checked += 1
    unsealed = conn.execute(
        """SELECT COUNT(*) FROM predictions_archive a
           LEFT JOIN predictions_archive_chain c ON c.archive_id = a.archive_id
           WHERE c.archive_id IS NULL"""
    ).fetchone()[0]
    return ChainReport(ok=True, checked=checked, unsealed=unsealed)


def chain_manifest(conn: sqlite3.Connection) -> dict:
    """Manifesto publicável (commit-and-reveal): nº de selos + hash da ponta.
    Quem guarda o manifest de ontem prova que nada anterior mudou."""
    cur = conn.execute(
        "SELECT archive_id, chain_hash FROM predictions_archive_chain "
        "ORDER BY archive_id DESC LIMIT 1"
    ).fetchone()
    return {
        "schema": 1,
        "sealed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "entries": conn.execute(
            "SELECT COUNT(*) FROM predictions_archive_chain"
        ).fetchone()[0],
        "head_archive_id": cur[0] if cur else None,
        "head": cur[1] if cur else None,
    }
