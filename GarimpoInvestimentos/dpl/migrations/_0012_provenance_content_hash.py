"""Migração 0012 — hash de conteúdo na proveniência (ADR-015).

Motivação: `ingestion_provenance` já registra `code_version`, mas não hash do
conteúdo ingerido — sem isso não dá pra provar que um re-ingest do mesmo
`code_version` reproduziu os MESMOS dados (reprodutibilidade bit-a-bit), só que
rodou o mesmo código. `content_hash` é o SHA-256 determinístico dos pontos
ingeridos (calculado em `ingest.py`, não aqui); linhas antigas ficam NULL
(pré-0012), sem backfill retroativo (dado bruto original não é reprocessado).

Mesmo padrão da 0007 (ADR-017): coluna aditiva, sem alterar migrações publicadas.
"""

NAME = "0012_provenance_content_hash"

SQL = """
    ALTER TABLE ingestion_provenance ADD COLUMN content_hash TEXT;
"""
