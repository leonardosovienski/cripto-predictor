"""Migração 0016 — proteção append-only para a tabela `predictions`.

Motivação (auditoria de 2026-08-19): os 440 registros brutos que sustentaram o
veredito de H5 foram perdidos — nenhuma das 5 cópias conhecidas de
`feature_store.db` retém as linhas individuais, só o resumo estatístico já
congelado em `trials.json`. Isso torna impossível qualquer reanálise
observação-a-observação (effective sample size, block bootstrap correto,
análise por regime/quantil/erro) para H5, retroativamente, para sempre.

`write_predictions` (feature_store.py) usa `INSERT ... ON CONFLICT DO UPDATE`
— upsert por PK (ativo, ts), necessário para a idempotência da coleta diária
(reexecução no mesmo dia não deve inflar o n). Mas isso também significa que,
tecnicamente, uma linha podia ser sobrescrita em silêncio sem deixar rastro do
valor anterior. Esta migração fecha essa lacuna sem mudar a semântica
operacional de upsert que a coleta diária depende:

  1. `predictions_archive` — tabela append-only (nunca UPDATE, nunca DELETE)
     que guarda:
     - o snapshot completo de toda linha nova inserida (`change_type=INSERT`);
     - o snapshot da linha ANTERIOR a cada UPDATE, capturado ANTES da
       sobrescrita (`change_type=PRE_UPDATE_SNAPSHOT`) — ou seja, todo estado
       que `predictions` já teve continua reconstruível: ou ainda está na
       tabela operacional, ou foi arquivado antes de ser substituído.
  2. Trigger `BEFORE DELETE` que ABORTA — `predictions` nunca permite DELETE
     via SQL comum. Uma limpeza/reset teria que primeiro remover o trigger
     explicitamente (ação deliberada e auditável, não um efeito colateral de
     rotina de limpeza).

Aditiva e idempotente (ADR-017 / C-04): nunca editar migração publicada.
`CREATE TABLE/TRIGGER IF NOT EXISTS` — seguro em `executescript` mesmo se
reexecutado (run_migrations já é idempotente por nome, mas o SQL em si
também precisa ser re-executável por statement, ver aviso em infra.run_migrations).
"""

NAME = "0016_predictions_append_only"

SQL = """
    CREATE TABLE IF NOT EXISTS predictions_archive (
        archive_id            INTEGER PRIMARY KEY AUTOINCREMENT,
        change_type           TEXT NOT NULL CHECK (change_type IN ('INSERT', 'PRE_UPDATE_SNAPSHOT')),
        archived_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        ativo                 TEXT NOT NULL,
        ts                    TEXT NOT NULL,
        score                 REAL,
        sentimento            TEXT,
        resumo                TEXT,
        price_usd             REAL,
        juiz                  TEXT,
        divergencia           INTEGER,
        fonte                 TEXT,
        input_degradado       INTEGER,
        llm_fallback          INTEGER,
        news_provider         TEXT,
        news_degraded_reason  TEXT,
        collection_policy     TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_predictions_archive_lookup
        ON predictions_archive (ativo, ts, archived_at);

    CREATE TRIGGER IF NOT EXISTS predictions_archive_on_insert
    AFTER INSERT ON predictions
    BEGIN
        INSERT INTO predictions_archive (
            change_type, ativo, ts, score, sentimento, resumo, price_usd, juiz,
            divergencia, fonte, input_degradado, llm_fallback, news_provider,
            news_degraded_reason, collection_policy
        ) VALUES (
            'INSERT', NEW.ativo, NEW.ts, NEW.score, NEW.sentimento, NEW.resumo,
            NEW.price_usd, NEW.juiz, NEW.divergencia, NEW.fonte, NEW.input_degradado,
            NEW.llm_fallback, NEW.news_provider, NEW.news_degraded_reason,
            NEW.collection_policy
        );
    END;

    CREATE TRIGGER IF NOT EXISTS predictions_archive_pre_update
    BEFORE UPDATE ON predictions
    BEGIN
        INSERT INTO predictions_archive (
            change_type, ativo, ts, score, sentimento, resumo, price_usd, juiz,
            divergencia, fonte, input_degradado, llm_fallback, news_provider,
            news_degraded_reason, collection_policy
        ) VALUES (
            'PRE_UPDATE_SNAPSHOT', OLD.ativo, OLD.ts, OLD.score, OLD.sentimento,
            OLD.resumo, OLD.price_usd, OLD.juiz, OLD.divergencia, OLD.fonte,
            OLD.input_degradado, OLD.llm_fallback, OLD.news_provider,
            OLD.news_degraded_reason, OLD.collection_policy
        );
    END;

    CREATE TRIGGER IF NOT EXISTS predictions_block_delete
    BEFORE DELETE ON predictions
    BEGIN
        SELECT RAISE(ABORT, 'predictions e append-only: DELETE bloqueado por design (migracao 0016). Nenhuma coorte prospectiva pode ser apagada em silencio.');
    END;
"""
