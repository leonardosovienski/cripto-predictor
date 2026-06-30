"""Testes da estratégia de migração aditiva (auditoria C-04 / ADR-017).

Garante que: (1) o schema final de raw_signals tem a PK com vintage; (2) reabrir o
mesmo DB (re-rodar migrações) é idempotente; (3) revisões coexistem após a migração.
"""
from datetime import datetime, timezone

from GarimpoInvestimentos.dpl import FeatureStore, SignalPoint
from GarimpoInvestimentos.dpl.feature_store import SCHEMA_VERSION

UTC = timezone.utc


def _pk_columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})") if r["pk"]]


def test_raw_signals_pk_inclui_vintage(tmp_path):
    with FeatureStore(tmp_path / "fs.db") as fs:
        pk = _pk_columns(fs._conn, "raw_signals")
    assert "vintage" in pk and "source" in pk and "name" in pk and "ts" in pk


def test_migracao_idempotente_ao_reabrir(tmp_path):
    db = tmp_path / "fs.db"
    ts = datetime(2026, 3, 31, tzinfo=UTC)
    with FeatureStore(db) as fs:
        fs.write_signals([SignalPoint("ipca", ts, 0.40, "bcb_sgs", ts, vintage=ts)])
    # Reabrir → run_migrations roda de novo; deve ser no-op (nada quebra, dado preservado)
    with FeatureStore(db) as fs2:
        got = fs2.read_signals("bcb_sgs", "ipca")
    assert len(got) == 1 and got[0].value == 0.40


def test_revisoes_coexistem_apos_migracao(tmp_path):
    ref = datetime(2026, 3, 31, tzinfo=UTC)
    v1 = SignalPoint("ipca", ref, 0.40, "bcb_sgs", datetime(2026, 4, 10, tzinfo=UTC),
                     vintage=datetime(2026, 4, 10, tzinfo=UTC))
    v2 = SignalPoint("ipca", ref, 0.43, "bcb_sgs", datetime(2026, 5, 15, tzinfo=UTC),
                     vintage=datetime(2026, 5, 15, tzinfo=UTC))
    with FeatureStore(tmp_path / "fs.db") as fs:
        fs.write_signals([v1, v2])
        assert len(fs.read_signals("bcb_sgs", "ipca")) == 2


def test_schema_version_exposto():
    assert SCHEMA_VERSION == 5
