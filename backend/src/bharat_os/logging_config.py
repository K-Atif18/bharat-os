"""Structured logging with PII redaction.

Two guarantees this module exists to provide:

**Structure.** Logs are JSON lines in production, so they are queryable by a log
aggregator rather than grep-only prose.

**Redaction.** A filter strips known-sensitive patterns — email addresses,
long digit runs that look like phone numbers or turnover figures, and anything
resembling a Fernet token — before a record is emitted. This is a safety net, not
the primary control: the primary control is that sensitive values are never
passed to a logger in the first place (see :mod:`bharat_os.crypto` and the
services that consume it). A filter here catches what discipline missed.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from bharat_os.http_middleware import current_request_id

_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_DIGIT_PATTERN = re.compile(r"\b\d{6,}\b")
_FERNET_TOKEN_PATTERN = re.compile(r"\bgAAAAA[A-Za-z0-9_=-]{20,}")

REDACTED = "[redacted]"


def redact(text: str) -> str:
    """Strip patterns that look like personal data from a log message."""
    text = _EMAIL_PATTERN.sub(REDACTED, text)
    text = _FERNET_TOKEN_PATTERN.sub(REDACTED, text)
    text = _LONG_DIGIT_PATTERN.sub(REDACTED, text)
    return text


class RedactionFilter(logging.Filter):
    """Applies :func:`redact` to every record's rendered message."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line, safe for a log aggregator to parse."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = current_request_id()
        if request_id is not None:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(*, environment: str, level: int = logging.INFO) -> None:
    """Set up root logging for the process.

    Production gets JSON output for aggregation; development gets plain text,
    which is faster to read at a terminal. Redaction applies in both, because a
    developer's terminal history is still a place PII should not land.
    """
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactionFilter())

    if environment == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)-5s %(name)s: %(message)s"))

    root.addHandler(handler)
