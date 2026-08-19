"""Migração 0016 — predictions nunca perde estado em silêncio.

Motivação: os 440 registros brutos de H5 foram perdidos (nenhuma cópia de
feature_store.db retém as linhas individuais). Estes testes provam que, daqui
para frente, isso é estruturalmente impossível dentro do SQLite: todo UPDATE
arquiva o estado anterior antes de sobrescrever, todo INSERT é arquivado, e
DELETE é bloqueado.
"""

from pathlib import Path

import pytest

from GarimpoInvestimentos.dpl import FeatureStore

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
