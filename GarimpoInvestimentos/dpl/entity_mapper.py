"""EntityMapper — normaliza entidades (times, jogadores, estádios) entre fontes.

Mapeia (source, raw_name) → canonical_id via tabela DE/PARA curada. Princípio
inegociável (ADR-013): fuzzy matching SÓ SUGERE; nunca cria mapeamento sozinho. Nome
não-mapeado retorna None (o conector bloqueia a ingestão daquele registro em vez de
inventar uma entidade fantasma — o pior bug de futebol é juntar a estatística do time
errado). Persistência em SQLite (reusa predictor_core.infra). Versionado por curadoria.
"""

from __future__ import annotations

import difflib
import unicodedata
from pathlib import Path

from predictor_core import infra

_MIGRATIONS = [
    (
        "0001_entity_canonical",
        """
        CREATE TABLE IF NOT EXISTS entity_canonical (
            canonical_id TEXT NOT NULL,
            type         TEXT NOT NULL,
            display_name TEXT NOT NULL,
            PRIMARY KEY (canonical_id, type)
        );
    """,
    ),
    (
        "0002_entity_alias",
        """
        CREATE TABLE IF NOT EXISTS entity_alias (
            source        TEXT NOT NULL,
            type          TEXT NOT NULL,
            normalized    TEXT NOT NULL,
            canonical_id  TEXT NOT NULL,
            raw_name      TEXT NOT NULL,
            curated_by    TEXT,
            curated_at    TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (source, type, normalized)
        );
    """,
    ),
]


def normalize(name: str) -> str:
    """Lowercase, sem acentos, espaços colapsados — chave de lookup robusta."""
    nfkd = unicodedata.normalize("NFKD", name)
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(no_accent.lower().split())


class EntityMapper:
    def __init__(self, db_path: Path | str):
        self._conn = infra.connect(db_path)
        infra.run_migrations(self._conn, _MIGRATIONS)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # --- Curadoria -----------------------------------------------------------

    def add_canonical(self, canonical_id: str, type: str, display_name: str) -> None:
        self._conn.execute(
            """INSERT INTO entity_canonical (canonical_id, type, display_name)
               VALUES (?,?,?) ON CONFLICT(canonical_id, type)
               DO UPDATE SET display_name=excluded.display_name""",
            (canonical_id, type, display_name),
        )
        self._conn.commit()

    def add_alias(
        self,
        source: str,
        type: str,
        raw_name: str,
        canonical_id: str,
        curated_by: str | None = None,
    ) -> None:
        self._conn.execute(
            """INSERT INTO entity_alias
               (source, type, normalized, canonical_id, raw_name, curated_by)
               VALUES (?,?,?,?,?,?) ON CONFLICT(source, type, normalized)
               DO UPDATE SET canonical_id=excluded.canonical_id,
                 raw_name=excluded.raw_name, curated_by=excluded.curated_by""",
            (source, type, normalize(raw_name), canonical_id, raw_name, curated_by),
        )
        self._conn.commit()

    # --- Resolução -----------------------------------------------------------

    def resolve(self, source: str, raw_name: str, type: str = "team") -> str | None:
        """canonical_id ou None (não-mapeado). Nunca adivinha — só lookup exato/normalizado."""
        norm = normalize(raw_name)
        row = self._conn.execute(
            """SELECT canonical_id FROM entity_alias
               WHERE source=? AND type=? AND normalized=?""",
            (source, type, norm),
        ).fetchone()
        return row["canonical_id"] if row else None

    def suggest(self, raw_name: str, type: str = "team", n: int = 3) -> list[str]:
        """Sugestões de canonical_id por similaridade — APENAS para curadoria humana,
        nunca aplicado automaticamente."""
        norm = normalize(raw_name)
        rows = self._conn.execute(
            "SELECT DISTINCT canonical_id, display_name FROM entity_canonical WHERE type=?", (type,)
        ).fetchall()
        pool = {normalize(r["display_name"]): r["canonical_id"] for r in rows}
        matches = difflib.get_close_matches(norm, list(pool), n=n, cutoff=0.6)
        return [pool[m] for m in matches]
