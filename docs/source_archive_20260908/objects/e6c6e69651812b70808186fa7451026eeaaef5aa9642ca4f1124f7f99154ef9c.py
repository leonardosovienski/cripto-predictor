import logging

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
