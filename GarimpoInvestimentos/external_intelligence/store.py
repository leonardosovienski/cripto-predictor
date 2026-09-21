"""Isolated append-only SQLite ledger for external research evidence."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from predictor_core.kernel import infra

from GarimpoInvestimentos.external_intelligence.contracts import (
    AssetMapping,
    CapabilitySnapshot,
    CollectionRun,
    ExternalObservationV1,
    ExternalResearchDocumentV1,
    RightsPolicy,
    canonical,
    digest,
    utc,
)

_MIGRATIONS = [
    (
        "0001_external_intelligence_v1",
        """
        CREATE TABLE IF NOT EXISTS collection_runs(
          collection_run_id TEXT NOT NULL,
          collection_run_revision TEXT NOT NULL,
          provider TEXT NOT NULL,
          started_at TEXT NOT NULL,
          finished_at TEXT NOT NULL,
          status TEXT NOT NULL,
          manifest_json TEXT NOT NULL,
          manifest_hash TEXT NOT NULL,
          PRIMARY KEY(collection_run_id, collection_run_revision)
        );
        CREATE TABLE IF NOT EXISTS provider_capability_snapshots(
          snapshot_id TEXT PRIMARY KEY,
          provider TEXT NOT NULL,
          state TEXT NOT NULL,
          received_at TEXT NOT NULL,
          scope_json TEXT NOT NULL,
          evidence_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS asset_mappings(
          mapping_id TEXT PRIMARY KEY,
          provider TEXT NOT NULL,
          canonical_asset_id TEXT NOT NULL,
          provider_asset_id TEXT NOT NULL,
          chain TEXT,
          contract TEXT,
          mapping_type TEXT NOT NULL,
          status TEXT NOT NULL,
          mapping_version TEXT NOT NULL,
          UNIQUE(provider, canonical_asset_id, provider_asset_id, chain, contract, mapping_version)
        );
        CREATE TABLE IF NOT EXISTS external_observations(
          observation_id TEXT NOT NULL,
          revision_id TEXT NOT NULL UNIQUE,
          provider TEXT NOT NULL,
          dataset TEXT NOT NULL,
          canonical_asset_id TEXT NOT NULL,
          provider_asset_id TEXT NOT NULL,
          metric TEXT NOT NULL,
          metric_version TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          provider_available_at TEXT,
          received_at TEXT NOT NULL,
          effective_available_at TEXT NOT NULL,
          pit_grade TEXT NOT NULL,
          capability_state TEXT NOT NULL,
          value_json TEXT,
          unit TEXT,
          dimensions_json TEXT NOT NULL,
          payload_reference TEXT,
          payload_hash TEXT,
          content_hash TEXT NOT NULL,
          collector_version TEXT NOT NULL,
          collection_run_id TEXT NOT NULL,
          collection_run_revision TEXT NOT NULL,
          rights_json TEXT NOT NULL,
          metadata_json TEXT NOT NULL,
          PRIMARY KEY(observation_id, revision_id)
        );
        CREATE INDEX IF NOT EXISTS external_observations_cutoff
          ON external_observations(canonical_asset_id, effective_available_at, observation_id);
        CREATE INDEX IF NOT EXISTS external_observations_metric
          ON external_observations(provider, dataset, metric, observed_at);
        CREATE TABLE IF NOT EXISTS external_documents(
          document_id TEXT NOT NULL,
          revision_id TEXT NOT NULL UNIQUE,
          provider TEXT NOT NULL,
          published_at TEXT,
          received_at TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          payload_reference TEXT,
          rights_json TEXT NOT NULL,
          provenance_json TEXT NOT NULL,
          PRIMARY KEY(document_id, revision_id)
        );
        CREATE TABLE IF NOT EXISTS dataset_snapshots(
          dataset_snapshot_revision TEXT PRIMARY KEY,
          cutoff TEXT NOT NULL,
          selection_json TEXT NOT NULL,
          manifest_json TEXT NOT NULL,
          manifest_hash TEXT NOT NULL CHECK(dataset_snapshot_revision = manifest_hash)
        );
        """,
    ),
    (
        "0002_append_only_guards",
        """
        CREATE TRIGGER IF NOT EXISTS external_observations_no_update
        BEFORE UPDATE ON external_observations BEGIN
          SELECT RAISE(ABORT, 'external observations are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS external_observations_no_delete
        BEFORE DELETE ON external_observations BEGIN
          SELECT RAISE(ABORT, 'external observations are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS external_documents_no_update
        BEFORE UPDATE ON external_documents BEGIN
          SELECT RAISE(ABORT, 'external documents are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS external_documents_no_delete
        BEFORE DELETE ON external_documents BEGIN
          SELECT RAISE(ABORT, 'external documents are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS capability_snapshots_no_update
        BEFORE UPDATE ON provider_capability_snapshots BEGIN
          SELECT RAISE(ABORT, 'capability snapshots are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS capability_snapshots_no_delete
        BEFORE DELETE ON provider_capability_snapshots BEGIN
          SELECT RAISE(ABORT, 'capability snapshots are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS collection_runs_no_update
        BEFORE UPDATE ON collection_runs BEGIN
          SELECT RAISE(ABORT, 'collection run revisions are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS collection_runs_no_delete
        BEFORE DELETE ON collection_runs BEGIN
          SELECT RAISE(ABORT, 'collection run revisions are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS dataset_snapshots_no_update
        BEFORE UPDATE ON dataset_snapshots BEGIN
          SELECT RAISE(ABORT, 'dataset snapshots are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS dataset_snapshots_no_delete
        BEFORE DELETE ON dataset_snapshots BEGIN
          SELECT RAISE(ABORT, 'dataset snapshots are immutable');
        END;
        """,
    ),
    (
        "0003_observation_receipts",
        """
        CREATE TABLE IF NOT EXISTS observation_receipts(
          revision_id TEXT NOT NULL,
          collection_run_id TEXT NOT NULL,
          collection_run_revision TEXT NOT NULL,
          received_at TEXT NOT NULL,
          PRIMARY KEY(revision_id, collection_run_id, collection_run_revision)
        );
        CREATE TRIGGER IF NOT EXISTS observation_receipts_no_update
        BEFORE UPDATE ON observation_receipts BEGIN
          SELECT RAISE(ABORT, 'observation receipts are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS observation_receipts_no_delete
        BEFORE DELETE ON observation_receipts BEGIN
          SELECT RAISE(ABORT, 'observation receipts are append-only');
        END;
        """,
    ),
]


class ExternalIntelligenceStore:
    """A database physically separate from the canonical Feature Store."""

    def __init__(self, path: str | Path, *, read_only: bool = False):
        self.path = Path(path)
        if read_only:
            self._conn = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA query_only=ON")
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = infra.connect(self.path)
            self._conn.execute("PRAGMA recursive_triggers=ON")
            infra.run_migrations(self._conn, _MIGRATIONS)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> ExternalIntelligenceStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def record_collection_run(self, run: CollectionRun) -> bool:
        encoded = canonical(run.manifest).decode("utf-8")
        revision = run.collection_run_revision
        existing = self._conn.execute(
            "SELECT manifest_json FROM collection_runs WHERE collection_run_id=? AND collection_run_revision=?",
            (run.collection_run_id, revision),
        ).fetchone()
        if existing:
            if existing["manifest_json"] != encoded:
                raise ValueError("collection run revision collision")
            return False
        self._conn.execute(
            "INSERT INTO collection_runs VALUES(?,?,?,?,?,?,?,?)",
            (
                run.collection_run_id,
                revision,
                run.provider,
                run.started_at.isoformat(),
                run.finished_at.isoformat(),
                run.status,
                encoded,
                digest(encoded.encode()),
            ),
        )
        self._conn.commit()
        return True

    def record_capability(self, snapshot: CapabilitySnapshot) -> bool:
        before = self._conn.total_changes
        self._conn.execute(
            "INSERT OR IGNORE INTO provider_capability_snapshots VALUES(?,?,?,?,?,?)",
            (
                snapshot.snapshot_id,
                snapshot.provider,
                snapshot.state.value,
                snapshot.received_at.isoformat(),
                canonical(snapshot.scope).decode(),
                canonical(snapshot.evidence).decode(),
            ),
        )
        self._conn.commit()
        return self._conn.total_changes > before

    def record_asset_mapping(self, mapping: AssetMapping) -> bool:
        before = self._conn.total_changes
        self._conn.execute(
            "INSERT OR IGNORE INTO asset_mappings VALUES(?,?,?,?,?,?,?,?,?)",
            (
                mapping.mapping_id,
                mapping.provider,
                mapping.canonical_asset_id,
                mapping.provider_asset_id,
                mapping.chain,
                mapping.contract,
                mapping.mapping_type,
                mapping.status.value,
                mapping.mapping_version,
            ),
        )
        self._conn.commit()
        return self._conn.total_changes > before

    def add_observation(self, observation: ExternalObservationV1) -> bool:
        payload = observation.as_dict()
        existing = self._conn.execute(
            "SELECT * FROM external_observations WHERE revision_id=?",
            (observation.revision_id,),
        ).fetchone()
        if existing:
            if existing["content_hash"] != observation.content_hash:
                raise ValueError("observation revision collision")
            self._record_observation_receipt(observation)
            return False
        self._conn.execute(
            "INSERT INTO external_observations VALUES(" + ",".join("?" for _ in range(25)) + ")",
            (
                observation.observation_id,
                observation.revision_id,
                observation.provider,
                observation.dataset,
                observation.canonical_asset_id,
                observation.provider_asset_id,
                observation.metric,
                observation.metric_version,
                observation.observed_at.isoformat(),
                observation.provider_available_at.isoformat()
                if observation.provider_available_at
                else None,
                observation.received_at.isoformat(),
                observation.effective_available_at.isoformat(),
                observation.pit_grade.value,
                observation.capability_state.value,
                canonical(observation.value).decode() if observation.value is not None else None,
                observation.unit,
                canonical(observation.dimensions).decode(),
                observation.payload_reference,
                observation.payload_hash,
                observation.content_hash,
                observation.collector_version,
                observation.collection_run_id,
                observation.collection_run_revision,
                canonical(payload["rights"]).decode(),
                canonical(observation.metadata).decode(),
            ),
        )
        self._record_observation_receipt(observation, commit=False)
        self._conn.commit()
        return True

    def add_document(self, document: ExternalResearchDocumentV1) -> bool:
        existing = self._conn.execute(
            "SELECT content_hash FROM external_documents WHERE revision_id=?",
            (document.revision_id,),
        ).fetchone()
        if existing:
            if existing["content_hash"] != document.content_hash:
                raise ValueError("document revision collision")
            return False
        self._conn.execute(
            "INSERT INTO external_documents VALUES(?,?,?,?,?,?,?,?,?)",
            (
                document.document_id,
                document.revision_id,
                document.provider,
                document.published_at.isoformat() if document.published_at else None,
                document.received_at.isoformat(),
                document.content_hash,
                document.payload_reference,
                canonical(document.rights.as_dict()).decode(),
                canonical(document.provenance).decode(),
            ),
        )
        self._conn.commit()
        return True

    def _record_observation_receipt(
        self, observation: ExternalObservationV1, *, commit: bool = True
    ) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO observation_receipts VALUES(?,?,?,?)",
            (
                observation.revision_id,
                observation.collection_run_id,
                observation.collection_run_revision,
                observation.received_at.isoformat(),
            ),
        )
        if commit:
            self._conn.commit()

    def observations_at(
        self,
        cutoff: datetime,
        *,
        canonical_asset_id: str | None = None,
        providers: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        cutoff = utc(cutoff, label="cutoff")
        clauses = ["causal_available_at<=?"]
        params: list[Any] = [cutoff.isoformat()]
        if canonical_asset_id is not None:
            clauses.append("canonical_asset_id=?")
            params.append(canonical_asset_id)
        provider_values = tuple(sorted(set(providers or ())))
        if provider_values:
            clauses.append("provider IN (" + ",".join("?" for _ in provider_values) + ")")
            params.extend(provider_values)
        rows = self._conn.execute(
            "SELECT * FROM (SELECT o.*, CASE WHEN o.pit_grade='PROVIDER_PIT' "
            "THEN o.provider_available_at ELSE (SELECT MIN(r.received_at) "
            "FROM observation_receipts r WHERE r.revision_id=o.revision_id) "
            "END AS causal_available_at FROM external_observations o) WHERE "
            + " AND ".join(clauses)
            + " ORDER BY observation_id,causal_available_at,received_at,revision_id",
            params,
        ).fetchall()
        latest: dict[str, sqlite3.Row] = {}
        for row in rows:
            latest[row["observation_id"]] = row
        return [self._decode_observation(latest[key]) for key in sorted(latest)]

    @staticmethod
    def _decode_observation(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        if result.get("causal_available_at"):
            result["effective_available_at"] = result.pop("causal_available_at")
        for key in ("value_json", "dimensions_json", "rights_json", "metadata_json"):
            result[key.removesuffix("_json")] = json.loads(result.pop(key)) if result[key] else None
        return result

    def materialize_snapshot(
        self,
        cutoff: datetime,
        *,
        canonical_asset_id: str | None = None,
        providers: Iterable[str] | None = None,
        feature_definition_revisions: Iterable[str] = (),
        cohort: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cutoff = utc(cutoff, label="cutoff")
        provider_values = tuple(sorted(set(providers or ())))
        rows = self.observations_at(
            cutoff,
            canonical_asset_id=canonical_asset_id,
            providers=provider_values,
        )
        selection = {
            "cutoff": cutoff.isoformat(),
            "canonical_asset_id": canonical_asset_id,
            "providers": list(provider_values),
            "cohort": cohort or {},
        }
        manifest = {
            "schema_version": "ExternalIntelligenceSnapshotV1",
            "selection": selection,
            "observation_revision_ids": sorted(row["revision_id"] for row in rows),
            "document_revision_ids": [],
            "feature_definition_revisions": sorted(set(feature_definition_revisions)),
            "pit_summary": self._counts(rows, "pit_grade"),
            "rights_summary": self._rights_summary(rows),
            "content_hashes": sorted(row["content_hash"] for row in rows),
        }
        revision = digest(manifest)
        encoded = canonical(manifest).decode()
        self._conn.execute(
            "INSERT OR IGNORE INTO dataset_snapshots VALUES(?,?,?,?,?)",
            (revision, cutoff.isoformat(), canonical(selection).decode(), encoded, revision),
        )
        self._conn.commit()
        return {**manifest, "dataset_snapshot_revision": revision}

    @staticmethod
    def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for row in rows:
            value = str(row[key])
            result[value] = result.get(value, 0) + 1
        return dict(sorted(result.items()))

    @staticmethod
    def _rights_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
        summary = {"cain_read_allowed": 0, "cain_generate_allowed": 0, "raw_export_allowed": 0}
        for row in rows:
            rights = row["rights"]
            summary["cain_read_allowed"] += int(bool(rights["cain_read"]))
            summary["cain_generate_allowed"] += int(bool(rights["cain_generate"]))
            summary["raw_export_allowed"] += int(bool(rights["raw_export"]))
        return summary

    def snapshot(self, revision: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT manifest_json FROM dataset_snapshots WHERE dataset_snapshot_revision=?",
            (revision,),
        ).fetchone()
        if row is None:
            raise KeyError(revision)
        return {**json.loads(row["manifest_json"]), "dataset_snapshot_revision": revision}

    def raw_connection_for_test(self) -> sqlite3.Connection:
        """Testing-only handle used to assert database-enforced immutability."""
        return self._conn


def rights_from_row(value: dict[str, Any]) -> RightsPolicy:
    checked = datetime.fromisoformat(value["checked_at"]) if value.get("checked_at") else None
    return RightsPolicy(**{**value, "checked_at": checked})
