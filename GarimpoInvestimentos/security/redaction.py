"""Logging adapter over the installed predictor_ops redaction API."""

from __future__ import annotations

import logging
import traceback
from collections.abc import Iterable

from predictor_ops.redaction import REDACTED  # noqa: F401 - public compatibility export
from predictor_ops.redaction import redact_text as _ops_redact_text

REDACTION_FAILED = "[REDACTION_FAILED]"


def redact_text(text: str, known_values: Iterable[str] = ()) -> str:
    return _ops_redact_text(text, tuple(known_values))


def safe_redact_text(text: str, known_values: Iterable[str] = ()) -> str:
    try:
        return redact_text(text, known_values)
    except Exception:
        return REDACTION_FAILED


class RedactingFilter(logging.Filter):
    def __init__(self, known_values: Iterable[str] = ()) -> None:
        super().__init__()
        self._known_values = tuple(known_values)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        cleaned = safe_redact_text(message, self._known_values)
        if cleaned != message:
            record.msg, record.args = cleaned, None
        if record.exc_info:
            record.exc_text = safe_redact_text(
                "".join(traceback.format_exception(*record.exc_info)), self._known_values
            )
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = safe_redact_text(record.exc_text, self._known_values)
        if record.stack_info:
            record.stack_info = safe_redact_text(record.stack_info, self._known_values)
        return True


def configured_secret_values() -> tuple[str, ...]:
    """Resolved private values, including dotenv-only news tokens."""
    from GarimpoInvestimentos.config import settings

    return tuple(
        value
        for name in type(settings).model_fields
        if name.endswith(("_API_KEY", "_AUTH_TOKEN"))
        and isinstance(value := getattr(settings, name), str)
        and value
    )


def safe_error_message(error: Exception) -> str:
    return safe_redact_text(str(error), configured_secret_values())


def install_log_redaction(known_values: Iterable[str]) -> None:
    """Sanitize CLI records before any current or future logging handler sees them."""
    previous = logging.getLogRecordFactory()
    redactor = RedactingFilter(known_values)

    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        redactor.filter(record)
        return record

    logging.setLogRecordFactory(factory)
