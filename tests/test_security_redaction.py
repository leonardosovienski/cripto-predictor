import logging
import sys

from GarimpoInvestimentos.security.redaction import REDACTED, RedactingFilter, safe_redact_text


def test_redacts_query_header_and_known_value():
    secret = "synthetic-secret-value-123456"
    text = f"https://example.test?q=btc&api_key={secret} Authorization: Bearer {secret}"
    cleaned = safe_redact_text(text, [secret])
    assert secret not in cleaned
    assert cleaned.count(REDACTED) >= 2
    assert "q=btc" in cleaned


def test_filter_redacts_logging_arguments():
    secret = "synthetic-secret-value-123456"
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "token=%s", (secret,), None)
    assert RedactingFilter([secret]).filter(record)
    assert secret not in record.getMessage()


def test_no_secret_in_exception_representation():
    secret = "synthetic-secret-value-123456"
    message = safe_redact_text(f"provider failed api_key={secret}")
    assert secret not in repr(RuntimeError(message))


def test_filter_redacts_chained_traceback_and_cached_exception():
    secret = "synthetic-secret-value-123456"
    try:
        try:
            raise ValueError(secret)
        except ValueError as original:
            raise RuntimeError("provider rejected") from original
    except RuntimeError:
        record = logging.LogRecord("test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())
    assert RedactingFilter([secret]).filter(record)
    assert secret not in logging.Formatter().format(record)
    record.exc_text = secret
    assert RedactingFilter([secret]).filter(record)
    assert secret not in logging.Formatter().format(record)


def test_error_event_is_redacted_before_persistence(monkeypatch, caplog):
    from GarimpoInvestimentos.config import settings
    from GarimpoInvestimentos.core import logger

    secret = "synthetic-unlabelled-provider-key"
    monkeypatch.setattr(settings, "COINGECKO_API_KEY", secret)
    events = []
    monkeypatch.setattr(logger, "emit_event", lambda *a, **kw: events.append(kw))
    logger.log_error("bitcoin", RuntimeError(f"request rejected: {secret}"))
    assert events and secret not in str(events)
    assert secret not in caplog.text
    assert events[0]["metadata"]["error_type"] == "RuntimeError"


def test_future_logging_handlers_receive_sanitized_records():
    import io

    from GarimpoInvestimentos.security.redaction import install_log_redaction

    secret = "synthetic-future-handler-secret"
    previous = logging.getLogRecordFactory()
    logger = logging.getLogger("test.runtime.private")
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    try:
        install_log_redaction([secret])
        logger.addHandler(handler)
        logger.error("provider rejected %s", secret)
        assert secret not in buffer.getvalue()
        assert REDACTED in buffer.getvalue()
    finally:
        logger.removeHandler(handler)
        logging.setLogRecordFactory(previous)
