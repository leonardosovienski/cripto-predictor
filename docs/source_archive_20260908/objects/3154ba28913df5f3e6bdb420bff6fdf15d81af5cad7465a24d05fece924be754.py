"""Migração 0006 — predictions: a Feature Store vira o histórico OFICIAL (passo 4).

Aposenta o garimpo_historico.csv como repositório canônico de previsões. Cada
linha = uma previsão do pipeline (ativo + timestamp), com o carimbo do juiz
(reprodutibilidade) e o carimbo fonte (estratificação — a equivalência provou
diffs de até 7.8pp nos change_* entre fontes; poolar sem estratificar contamina
o backtest). PK (ativo, ts): reexecução/cache hit não infla o n estatístico —
mesma semântica do dedup que o CSV tinha.

Aditiva e idempotente (ADR-017 / C-04): nunca editar migração publicada.
"""

NAME = "0006_predictions"

SQL = """
    CREATE TABLE IF NOT EXISTS predictions (
        ativo       TEXT NOT NULL,
        ts          TEXT NOT NULL,
        score       REAL NOT NULL,
        sentimento  TEXT,
        resumo      TEXT,
        price_usd   REAL,
        juiz        TEXT,
        divergencia INTEGER NOT NULL DEFAULT 0,
        fonte       TEXT NOT NULL DEFAULT 'direct',
        PRIMARY KEY (ativo, ts)
    );
"""
