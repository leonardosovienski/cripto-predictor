"""Migração 0005 — evolui raw_signals para o schema bitemporal (aditiva, idempotente).

Corrige o débito da auditoria (C-04): em vez de alterar a migração 0002 in-place
(o que quebraria a idempotência para DBs já criados), esta migração TRANSFORMA o
estado anterior:
  - cria raw_signals_v2 com reference_date, vintage e PK (source, name, ts, vintage)
    — permitindo que múltiplas revisões (vintages) do mesmo ponto coexistam;
  - copia os dados existentes (vintage='' = sem revisão, ex.: Fear&Greed);
  - substitui a tabela antiga.

Nome de módulo com prefixo '_' porque identificadores Python não podem começar com
dígito; o nome lógico da migração (NAME) preserva o número de ordem.
"""

NAME = "0005_fix_raw_signals"

SQL = """
    CREATE TABLE IF NOT EXISTS raw_signals_v2 (
        source         TEXT NOT NULL,
        name           TEXT NOT NULL,
        ts             TEXT NOT NULL,
        reference_date TEXT,
        value          REAL NOT NULL,
        published_at   TEXT NOT NULL,
        vintage        TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (source, name, ts, vintage)
    );
    INSERT INTO raw_signals_v2 (source, name, ts, reference_date, value, published_at, vintage)
        SELECT source, name, ts, NULL, value, published_at, ''
        FROM raw_signals;
    DROP TABLE raw_signals;
    ALTER TABLE raw_signals_v2 RENAME TO raw_signals;
"""
