"""Migração 0016 — predictions nunca perde estado em silêncio.

Motivação: os 440 registros brutos de H5 foram perdidos (nenhuma cópia de
feature_store.db retém as linhas individuais). Estes testes provam que, daqui
para frente, isso é estruturalmente impossível dentro do SQLite: todo UPDATE
arquiva o estado anterior antes de sobrescrever, todo INSERT é arquivado, e
DELETE é bloqueado.
"""

import sqlite3
from pathlib import Path

import pytest
from predictor_core import infra

from GarimpoInvestimentos.dpl import FeatureStore
from GarimpoInvestimentos.dpl.feature_store import _MIGRATIONS
from GarimpoInvestimentos.dpl.migrations import ADDITIVE_MIGRATIONS

_ROW = {
    "ativo": "bitcoin",
    "ts": "2026-08-19 00:00:00",
    "score": 70.0,
    "sentimento": "positivo",
    "resumo": "primeira previsao",
    "price_usd": 50000.0,
    "juiz": "gemini",
    "divergencia": 0,
    "fonte": "direct",
}


@pytest.fixture
def store(tmp_path: Path):
    with FeatureStore(str(tmp_path / "feature_store.db")) as fs:
        yield fs


def test_insert_e_arquivado(store):
    store.write_predictions([_ROW])
    rows = store._conn.execute("SELECT change_type, score FROM predictions_archive").fetchall()
    assert [dict(r) for r in [dict(zip(("change_type", "score"), r)) for r in rows]] == [
        {"change_type": "INSERT", "score": 70.0}
    ]


def test_upsert_preserva_valor_anterior_no_archive(store):
    store.write_predictions([_ROW])
    corrected = dict(_ROW, score=40.0, resumo="correcao operacional")
    store.write_predictions([corrected])

    archived = store._conn.execute(
        "SELECT change_type, score, resumo FROM predictions_archive ORDER BY archive_id"
    ).fetchall()
    assert len(archived) == 2
    assert archived[0]["change_type"] == "INSERT"
    assert archived[0]["score"] == 70.0
    assert archived[0]["resumo"] == "primeira previsao"
    assert archived[1]["change_type"] == "PRE_UPDATE_SNAPSHOT"
    assert archived[1]["score"] == 70.0  # o valor ANTES de virar 40.0
    assert archived[1]["resumo"] == "primeira previsao"

    live = store._conn.execute(
        "SELECT score, resumo FROM predictions WHERE ativo='bitcoin' AND ts=?",
        (_ROW["ts"],),
    ).fetchone()
    assert live["score"] == 40.0  # tabela operacional reflete a correção
    assert live["resumo"] == "correcao operacional"


def test_reexecucao_mesmo_dia_mesma_linha_ainda_arquiva_antes_de_sobrescrever(store):
    """Idempotência da coleta diária (mesma PK, mesmo valor) continua funcionando
    como upsert — mas mesmo um upsert "sem mudança real" fica registrado no
    archive, nunca silenciosamente perdido."""
    store.write_predictions([_ROW])
    store.write_predictions([_ROW])  # reexecução idêntica
    n = store._conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    assert n == 1  # PK não duplica a tabela operacional
    n_archive = store._conn.execute("SELECT COUNT(*) FROM predictions_archive").fetchone()[0]
    assert n_archive == 2  # INSERT + PRE_UPDATE_SNAPSHOT (mesmo idêntico)


def test_delete_e_bloqueado(store):
    store.write_predictions([_ROW])
    with pytest.raises(Exception, match="append-only"):
        store._conn.execute("DELETE FROM predictions WHERE ativo='bitcoin'")


def test_migracao_e_idempotente_em_db_ja_migrado(tmp_path):
    """Reabrir um DB já migrado não deve falhar (CREATE ... IF NOT EXISTS)."""
    db_path = str(tmp_path / "feature_store.db")
    with FeatureStore(db_path) as fs:
        fs.write_predictions([_ROW])
    with FeatureStore(db_path) as fs:
        fs.write_predictions([dict(_ROW, score=10.0)])
    with FeatureStore(db_path) as fs:
        n = fs._conn.execute("SELECT COUNT(*) FROM predictions_archive").fetchone()[0]
    assert n == 2


def test_upgrade_de_banco_pre_0016_com_predictions_ja_populado(tmp_path):
    """Cenário real de produção: um feature_store.db criado ANTES da migração 0016
    existir, com previsões já gravadas pelo pipeline antigo (linhas cruas, sem
    nenhuma proteção). Confirma que: (1) abrir esse banco com o código atual não
    perde as linhas já existentes; (2) a partir da migração, a proteção passa a
    valer para NOVAS escritas na mesma linha antiga."""
    db_path = tmp_path / "feature_store.db"

    # Simula o estado "pré-0016": aplica todas as migrações MENOS a append-only.
    migration_0016 = next(
        i
        for i, (name, _sql) in enumerate(ADDITIVE_MIGRATIONS)
        if name == "0016_predictions_append_only"
    )
    pre_0016 = ADDITIVE_MIGRATIONS[:migration_0016]
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    infra.run_migrations(conn, _MIGRATIONS + pre_0016)
    conn.execute(
        """INSERT INTO predictions
           (ativo, ts, score, sentimento, resumo, price_usd, juiz, divergencia, fonte)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            _ROW["ativo"],
            _ROW["ts"],
            _ROW["score"],
            _ROW["sentimento"],
            _ROW["resumo"],
            _ROW["price_usd"],
            _ROW["juiz"],
            _ROW["divergencia"],
            _ROW["fonte"],
        ),
    )
    conn.commit()
    conn.close()

    # Reabre com o código ATUAL (aplica 0016 em cima do banco pré-existente).
    with FeatureStore(str(db_path)) as fs:
        # (1) a linha antiga sobrevive à migração
        old_row = fs._conn.execute(
            "SELECT score FROM predictions WHERE ativo='bitcoin' AND ts=?", (_ROW["ts"],)
        ).fetchone()
        assert old_row["score"] == 70.0

        # a migração NÃO retroage sobre o que já existia (não inventa um INSERT
        # arquivado pra uma linha que ela nunca viu nascer) — só protege dali pra frente
        n_archive_antes = fs._conn.execute("SELECT COUNT(*) FROM predictions_archive").fetchone()[0]
        assert n_archive_antes == 0

        # (2) a partir de agora, sobrescrever a linha antiga arquiva corretamente
        fs.write_predictions([dict(_ROW, score=99.0)])
        archived = fs._conn.execute("SELECT change_type, score FROM predictions_archive").fetchall()
        assert len(archived) == 1
        assert archived[0]["change_type"] == "PRE_UPDATE_SNAPSHOT"
        assert archived[0]["score"] == 70.0  # o valor que a migracao encontrou

        # (3) DELETE também passa a ser bloqueado na linha antiga
        with pytest.raises(Exception, match="append-only"):
            fs._conn.execute("DELETE FROM predictions WHERE ativo='bitcoin'")


def test_migration_falha_no_meio_nao_deixa_banco_inconsistente(tmp_path):
    """Se o processo morrer no meio da lista de migrações aditivas, reabrir o
    banco depois (rodando a lista completa de novo) tem que terminar num estado
    consistente — nem trigger duplicada, nem tabela faltando."""
    db_path = tmp_path / "feature_store.db"
    # Aplica só até a migração anterior à 0016 (simula uma "queda" no meio do deploy).
    migration_0016 = next(
        i
        for i, (name, _sql) in enumerate(ADDITIVE_MIGRATIONS)
        if name == "0016_predictions_append_only"
    )
    partial = ADDITIVE_MIGRATIONS[:migration_0016]
    conn = sqlite3.connect(str(db_path))
    infra.run_migrations(conn, _MIGRATIONS + partial)
    conn.close()

    # Reabrir com a lista completa (0016 incluída) não deve levantar exceção.
    with FeatureStore(str(db_path)) as fs:
        fs.write_predictions([_ROW])
        tables = {
            r[0]
            for r in fs._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "predictions_archive" in tables
        triggers = {
            r[0]
            for r in fs._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            ).fetchall()
        }
        assert {
            "predictions_archive_on_insert",
            "predictions_archive_pre_update",
            "predictions_block_delete",
        } <= triggers

    # Reabrir DE NOVO (segunda vez) não duplica nada nem falha.
    with FeatureStore(str(db_path)) as fs:
        fs.write_predictions([dict(_ROW, score=5.0)])
        n = fs._conn.execute("SELECT COUNT(*) FROM predictions_archive").fetchone()[0]
        assert n == 2  # INSERT original + PRE_UPDATE_SNAPSHOT da segunda escrita
