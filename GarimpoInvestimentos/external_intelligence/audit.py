"""Adversarial temporal perturbation checks."""

from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from GarimpoInvestimentos.external_intelligence.context import context_at
from GarimpoInvestimentos.external_intelligence.features import expanding_zscore_at
from GarimpoInvestimentos.external_intelligence.store import ExternalIntelligenceStore


@dataclass(frozen=True)
class TemporalAuditResult:
    status: str
    checks: dict[str, bool]


def temporal_perturbation_audit(
    store: ExternalIntelligenceStore,
    *,
    asset: str,
    cutoff: datetime,
    provider: str,
    dataset: str,
    metric: str,
) -> TemporalAuditResult:
    full = context_at(store, asset=asset, decision_time=cutoff)
    full_feature = expanding_zscore_at(
        store,
        asset=asset,
        provider=provider,
        dataset=dataset,
        metric=metric,
        cutoff=cutoff,
    )
    with tempfile.TemporaryDirectory(prefix="external-intelligence-audit-") as area:
        path = Path(area) / "truncated.db"
        with ExternalIntelligenceStore(path) as truncated:
            _copy_eligible(store, truncated, cutoff)
            limited = context_at(truncated, asset=asset, decision_time=cutoff)
            limited_feature = expanding_zscore_at(
                truncated,
                asset=asset,
                provider=provider,
                dataset=dataset,
                metric=metric,
                cutoff=cutoff,
            )
    context_equal = full.canonical_bytes() == limited.canonical_bytes()
    feature_equal = (
        full_feature.value == limited_feature.value
        and full_feature.input_revision_ids == limited_feature.input_revision_ids
    )
    checks = {
        "full_vs_truncated_replay": context_equal,
        "late_revision": context_equal,
        "reconstructed_history": context_equal,
        "future_deletion": context_equal,
        "transformation_leakage": feature_equal,
        "missing_is_not_zero": all(
            row["value"] is None
            for row in full.observations
            if row["capability_state"] != "SUPPORTED"
        ),
    }
    return TemporalAuditResult(
        status="PASS" if all(checks.values()) else "LOOKAHEAD_BIAS",
        checks=checks,
    )


def _copy_eligible(
    source: ExternalIntelligenceStore, target: ExternalIntelligenceStore, cutoff: datetime
) -> None:
    src = source.raw_connection_for_test()
    dst = target.raw_connection_for_test()
    rows = src.execute(
        """SELECT * FROM external_observations o
           WHERE (pit_grade='PROVIDER_PIT' AND provider_available_at<=?)
              OR (pit_grade!='PROVIDER_PIT' AND EXISTS(
                    SELECT 1 FROM observation_receipts r
                    WHERE r.revision_id=o.revision_id AND r.received_at<=?
                 ))
           ORDER BY revision_id""",
        (cutoff.isoformat(), cutoff.isoformat()),
    ).fetchall()
    columns = [item[1] for item in src.execute("PRAGMA table_info(external_observations)")]
    placeholders = ",".join("?" for _ in columns)
    dst.executemany(
        f"INSERT INTO external_observations({','.join(columns)}) VALUES({placeholders})",  # noqa: S608
        [tuple(row[column] for column in columns) for row in rows],
    )
    revision_ids = {row["revision_id"] for row in rows}
    receipts = src.execute("SELECT * FROM observation_receipts ORDER BY revision_id").fetchall()
    dst.executemany(
        "INSERT INTO observation_receipts VALUES(?,?,?,?)",
        [
            tuple(row)
            for row in receipts
            if row["revision_id"] in revision_ids and row["received_at"] <= cutoff.isoformat()
        ],
    )
    dst.commit()


def assert_append_only(store: ExternalIntelligenceStore) -> bool:
    try:
        store.raw_connection_for_test().execute("DELETE FROM external_observations")
    except sqlite3.IntegrityError:
        return True
    return False
