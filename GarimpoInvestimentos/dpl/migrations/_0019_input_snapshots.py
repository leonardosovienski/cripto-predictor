"""Preserve new market materializations and prediction inputs without rewriting legacy data."""

NAME = "0019_input_snapshots"
SQL = """
    CREATE TABLE IF NOT EXISTS market_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        interval TEXT NOT NULL,
        feature_version TEXT NOT NULL,
        collected_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS market_snapshots_lookup
        ON market_snapshots(symbol, interval, feature_version, collected_at);
    CREATE TABLE IF NOT EXISTS prediction_inputs (
        ativo TEXT NOT NULL,
        ts TEXT NOT NULL,
        input_hash TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        PRIMARY KEY (ativo, ts)
    );
    CREATE TRIGGER IF NOT EXISTS market_snapshots_no_update
    BEFORE UPDATE ON market_snapshots BEGIN
        SELECT RAISE(ABORT, 'market_snapshots is immutable');
    END;
    CREATE TRIGGER IF NOT EXISTS market_snapshots_no_delete
    BEFORE DELETE ON market_snapshots BEGIN
        SELECT RAISE(ABORT, 'market_snapshots is immutable');
    END;
    CREATE TRIGGER IF NOT EXISTS prediction_inputs_no_update
    BEFORE UPDATE ON prediction_inputs BEGIN
        SELECT RAISE(ABORT, 'prediction_inputs is immutable');
    END;
    CREATE TRIGGER IF NOT EXISTS prediction_inputs_no_delete
    BEFORE DELETE ON prediction_inputs BEGIN
        SELECT RAISE(ABORT, 'prediction_inputs is immutable');
    END;
    CREATE TRIGGER IF NOT EXISTS market_snapshots_no_replace
    BEFORE INSERT ON market_snapshots
    WHEN EXISTS (SELECT 1 FROM market_snapshots WHERE snapshot_id=NEW.snapshot_id
        AND (payload_json<>NEW.payload_json OR symbol<>NEW.symbol
             OR interval<>NEW.interval OR feature_version<>NEW.feature_version
             OR collected_at<>NEW.collected_at))
    BEGIN SELECT RAISE(ABORT, 'market_snapshots is immutable'); END;
    CREATE TRIGGER IF NOT EXISTS prediction_inputs_no_replace
    BEFORE INSERT ON prediction_inputs
    WHEN EXISTS (SELECT 1 FROM prediction_inputs WHERE ativo=NEW.ativo AND ts=NEW.ts
        AND (input_hash<>NEW.input_hash OR payload_json<>NEW.payload_json))
    BEGIN SELECT RAISE(ABORT, 'prediction_inputs is immutable'); END;
"""
