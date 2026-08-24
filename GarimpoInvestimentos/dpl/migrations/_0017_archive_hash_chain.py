"""Migração 0017 — cadeia de hash (tamper-evidence) sobre `predictions_archive`.

Motivação (auditoria externa 2026-08-24, inspirada no padrão audit ledger):
os triggers da 0016 garantem que todo estado de `predictions` é arquivado,
mas NADA impede que alguém edite/apague linhas do próprio archive — a
proteção é de corretude operacional, não de adulteração. Esta migração cria
a tabela que ancora uma **cadeia de hash SHA-256** (cada linha carrega o hash
da linha anterior, estilo blockchain mínimo): qualquer reescrita, remoção ou
reordenação retroativa do archive quebra a cadeia e é detectada por
`dpl/hash_chain.verify_chain`.

A tabela é deliberadamente SEPARADA do archive (não é uma coluna nova nele):
manter o append-only do archive intocado — nem UPDATE para "selar". O selo
é computado em Python (SQLite padrão não tem sha256) por
`dpl/hash_chain.seal_chain`, chamado pelo quality_snapshot diário; o hash da
ponta (`head`) é publicado em `chain_manifest.json` (mesma convenção do
h6_status.json: commitado à mão quando muda) — é o anchor público da cadeia.

Aditiva e idempotente (ADR-017 / C-04): nunca editar migração publicada.
"""

NAME = "0017_archive_hash_chain"

SQL = """
    CREATE TABLE IF NOT EXISTS predictions_archive_chain (
        -- Sem REFERENCES de propósito: a FK bloquearia o DELETE retroativo com
        -- erro genérico; sem ela, verify_chain detecta a remoção e reporta a
        -- adulteração com mensagem forense clara (linha selada ausente).
        archive_id  INTEGER PRIMARY KEY,
        chain_hash  TEXT NOT NULL
    );
"""
