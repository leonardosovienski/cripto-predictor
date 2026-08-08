"""Migration 0013 — enriched provenance for official SignalPoint storage."""

NAME = "0013_enriched_signals"

SQL = """
    ALTER TABLE raw_signals ADD COLUMN instrument TEXT NOT NULL DEFAULT '';
    ALTER TABLE raw_signals ADD COLUMN metric TEXT NOT NULL DEFAULT '';
    ALTER TABLE raw_signals ADD COLUMN unit TEXT NOT NULL DEFAULT '';
    ALTER TABLE raw_signals ADD COLUMN event_at TEXT;
    ALTER TABLE raw_signals ADD COLUMN ingested_at TEXT;
    ALTER TABLE raw_signals ADD COLUMN content_hash TEXT NOT NULL DEFAULT '';
    ALTER TABLE raw_signals ADD COLUMN collector_version TEXT NOT NULL DEFAULT '';
    ALTER TABLE raw_signals ADD COLUMN schema_version TEXT NOT NULL DEFAULT '';
    ALTER TABLE raw_signals ADD COLUMN quality_flags TEXT NOT NULL DEFAULT '[]';
    ALTER TABLE raw_signals ADD COLUMN scientific_state TEXT NOT NULL DEFAULT 'COLLECTION_ONLY';
"""
