"""Add the independently verifiable hash-chain table for prediction archives."""

NAME = "0017_archive_hash_chain"

SQL = """
    CREATE TABLE IF NOT EXISTS predictions_archive_chain (
        archive_id INTEGER PRIMARY KEY,
        chain_hash TEXT NOT NULL CHECK(length(chain_hash) = 64),
        FOREIGN KEY (archive_id) REFERENCES predictions_archive(archive_id)
    );
"""
