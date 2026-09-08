"""Make the prediction archive and its hash chain immutable at schema level."""

NAME = "0018_archive_immutable"

SQL = """
    CREATE TRIGGER IF NOT EXISTS predictions_archive_block_update
    BEFORE UPDATE ON predictions_archive
    BEGIN
        SELECT RAISE(ABORT, 'predictions_archive is immutable: UPDATE blocked');
    END;

    CREATE TRIGGER IF NOT EXISTS predictions_archive_block_delete
    BEFORE DELETE ON predictions_archive
    BEGIN
        SELECT RAISE(ABORT, 'predictions_archive is immutable: DELETE blocked');
    END;

    CREATE TRIGGER IF NOT EXISTS predictions_archive_chain_block_update
    BEFORE UPDATE ON predictions_archive_chain
    BEGIN
        SELECT RAISE(ABORT, 'predictions_archive_chain is immutable: UPDATE blocked');
    END;

    CREATE TRIGGER IF NOT EXISTS predictions_archive_chain_block_delete
    BEFORE DELETE ON predictions_archive_chain
    BEGIN
        SELECT RAISE(ABORT, 'predictions_archive_chain is immutable: DELETE blocked');
    END;
"""
