"""Migration 0014 — auditable source-quality scorecard snapshots."""

NAME = "0014_source_quality_scorecards"

SQL = """
    CREATE TABLE IF NOT EXISTS source_quality_scorecards (
        source TEXT NOT NULL,
        window_start TEXT NOT NULL,
        window_end TEXT NOT NULL,
        calculated_at TEXT NOT NULL,
        state TEXT NOT NULL,
        scientific_state TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        PRIMARY KEY (source, window_start, window_end, calculated_at)
    );
"""
