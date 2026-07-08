"""Migração 0007 — versionamento de features (aditiva, idempotente).

Motivação (auditoria jul/2026): recalcular uma feature com lógica nova
sobrescrevia o histórico materializado (upsert na PK antiga), destruindo a
rastreabilidade de experimentos passados. Com `feature_version` na PK, versões
COEXISTEM: um backtest antigo continua lendo a versão que o gerou, e um backfill
com lógica nova escreve ao lado, nunca por cima.

Mesmo padrão da 0005 (ADR-017): nunca alterar migração publicada in-place —
esta TRANSFORMA o estado anterior, marcando todo o histórico como 'v1'.
"""

NAME = "0007_feature_version"

SQL = """
    CREATE TABLE IF NOT EXISTS features_aligned_v2 (
        symbol          TEXT NOT NULL,
        interval        TEXT NOT NULL,
        ts              TEXT NOT NULL,
        feature         TEXT NOT NULL,
        value           REAL,
        feature_version TEXT NOT NULL DEFAULT 'v1',
        PRIMARY KEY (symbol, interval, ts, feature, feature_version)
    );
    INSERT INTO features_aligned_v2 (symbol, interval, ts, feature, value, feature_version)
        SELECT symbol, interval, ts, feature, value, 'v1'
        FROM features_aligned;
    DROP TABLE features_aligned;
    ALTER TABLE features_aligned_v2 RENAME TO features_aligned;
"""
