"""Migration 0015 — metric-separated, idempotent observation scorecards."""

NAME = "0015_observation_scorecards"

SQL = """
    CREATE TABLE IF NOT EXISTS observation_scorecards (
        plan_id TEXT NOT NULL,
        source TEXT NOT NULL,
        metric TEXT NOT NULL,
        window_start TEXT NOT NULL,
        window_end TEXT NOT NULL,
        calculated_at TEXT NOT NULL,
        state TEXT NOT NULL,
        scientific_state TEXT NOT NULL CHECK (scientific_state = 'COLLECTION_ONLY'),
        payload_hash TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        PRIMARY KEY (plan_id, source, metric, window_start, window_end)
    );
"""
