"""Logging adapter over the installed predictor_ops redaction API."""

from __future__ import annotations

import logging
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
        return True
