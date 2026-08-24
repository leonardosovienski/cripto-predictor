"""Testes da cadeia de hash do ledger (migração 0017 + dpl/hash_chain.py) e
do PRAGMA recursive_triggers (P0 da auditoria externa 2026-08-24)."""

import sqlite3

import pytest

from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.hash_chain import (
    GENESIS,
    chain_manifest,
    seal_chain,
    verify_chain,
)


def _store(tmp_path):
    return FeatureStore(tmp_path / "fs.db")


def _pred(ativo="bitcoin", ts="2026-08-20 12:00:00", score=70.0):
    return {
        "ativo": ativo,
        "ts": ts,
        "score": score,
        "sentimento": "positivo",
        "resumo": "teste",
        "price_usd": 100_000.0,
        "juiz": "gemini:test:hash",
        "divergencia": 0,
        "fonte": "direct",
        "input_degradado": 0,
        "llm_fallback": 0,
        "news_provider": "gnews",
        "news_degraded_reason": None,
        "collection_policy": None,
    }


def test_seal_and_verify_roundtrip(tmp_path):
    with _store(tmp_path) as store:
        store.write_predictions([_pred()])
        assert seal_chain(store._conn) == 1
        report = verify_chain(store._conn)
        assert report.ok and report.checked == 1 and report.unsealed == 0
        m = chain_manifest(store._conn)
        assert m["entries"] == 1 and m["head"] and m["head"] != GENESIS


def test_seal_is_idempotent(tmp_path):
    with _store(tmp_path) as store:
        store.write_predictions([_pred()])
        assert seal_chain(store._conn) == 1
        assert seal_chain(store._conn) == 0  # nada novo para selar
        assert verify_chain(store._conn).ok


def test_chain_detects_retroactive_edit(tmp_path):
    with _store(tmp_path) as store:
        store.write_predictions([_pred(), _pred(ts="2026-08-21 12:00:00", score=60.0)])
        assert seal_chain(store._conn) == 2
        # Adultera a PRIMEIRA linha do archive (muda o score registrado).
        store._conn.execute(
            "UPDATE predictions_archive SET score = 999.0 WHERE archive_id = 1"
        )
        report = verify_chain(store._conn)
        assert not report.ok and report.first_bad_archive_id == 1


def test_chain_detects_retroactive_delete(tmp_path):
    with _store(tmp_path) as store:
        store.write_predictions([_pred(), _pred(ts="2026-08-21 12:00:00")])
        assert seal_chain(store._conn) == 2
        store._conn.execute("DELETE FROM predictions_archive WHERE archive_id = 1")
        report = verify_chain(store._conn)
        assert not report.ok and "AUSENTE" in report.detail


def test_seal_refuses_to_extend_broken_chain(tmp_path):
    with _store(tmp_path) as store:
        store.write_predictions([_pred()])
        seal_chain(store._conn)
        store._conn.execute(
            "UPDATE predictions_archive SET score = 1.0 WHERE archive_id = 1"
        )
        store.write_predictions([_pred(ts="2026-08-21 12:00:00")])
        with pytest.raises(RuntimeError, match="NÃO verifica"):
            seal_chain(store._conn)


def test_recursive_triggers_close_replace_hole(tmp_path):
    """Com recursive_triggers=ON (setado no __init__ da FeatureStore), um
    INSERT OR REPLACE em predictions executa o DELETE implícito do REPLACE,
    dispara o trigger BEFORE DELETE da 0016 e ABORTA — sem o PRAGMA, a linha
    seria substituída sem passar pelo archive (buraco do append-only)."""
    with _store(tmp_path) as store:
        store.write_predictions([_pred()])
        cols = (
            "ativo, ts, score, sentimento, resumo, price_usd, juiz, divergencia,"
            " fonte, input_degradado, llm_fallback, news_provider,"
            " news_degraded_reason, collection_policy"
        )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            store._conn.execute(
                f"INSERT OR REPLACE INTO predictions ({cols}) VALUES"
                " ('bitcoin', '2026-08-20 12:00:00', 10.0, 'x', 'x', 1.0,"
                " 'j', 0, 'direct', 0, 0, NULL, NULL, NULL)"
            )


def test_manifest_changes_only_when_head_changes(tmp_path):
    with _store(tmp_path) as store:
        m0 = chain_manifest(store._conn)
        assert m0["entries"] == 0 and m0["head"] is None
        store.write_predictions([_pred()])
        seal_chain(store._conn)
        m1 = chain_manifest(store._conn)
        assert m1["head"] != m0["head"]
