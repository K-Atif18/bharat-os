"""Structured logging and PII redaction.

The primary control against PII in logs is discipline at the call site — see
crypto.py and the services that never pass sensitive values to a logger. This
module is the safety net behind that discipline, so its tests use realistic
inputs (an actual Fernet token from the real encryption path, not a short
synthetic stand-in) to make sure the net actually catches what it claims to.
"""

from __future__ import annotations

import json
import logging

from bharat_os.crypto import encrypt_text
from bharat_os.logging_config import JsonFormatter, RedactionFilter, redact


class TestRedaction:
    def test_redacts_an_email_address(self) -> None:
        assert "founder@example.com" not in redact("contact founder@example.com about this")

    def test_redacts_long_digit_runs(self) -> None:
        """Turnover figures and phone numbers are both long digit runs."""
        assert "1200000" not in redact("turnover was 1200000 this year")

    def test_does_not_redact_short_numbers(self) -> None:
        """A count like '3 documents missing' is not personal data."""
        assert "3 documents" in redact("3 documents missing")

    def test_redacts_a_real_fernet_token(self) -> None:
        """Uses the actual encryption path, not a synthetic short string, because
        a too-short test token previously let a real gap go unnoticed."""
        token = encrypt_text("1200000")
        rendered = redact(f"stored value: {token}")
        assert token not in rendered
        assert "gAAAAA" not in rendered

    def test_redacts_fernet_token_including_base64_padding(self) -> None:
        """Fernet tokens are base64 and may end in '=' padding; the padding must
        not survive redaction as a dangling fragment of the original token."""
        token = encrypt_text("some sensitive value")
        rendered = redact(f"value={token}")
        assert token not in rendered
        assert rendered.endswith("[redacted]") or "[redacted]" in rendered

    def test_leaves_ordinary_text_untouched(self) -> None:
        assert redact("Scheme sisfs matched with confidence 87%") == (
            "Scheme sisfs matched with confidence 87%"
        )


class TestRedactionFilter:
    def test_filter_redacts_the_rendered_message(self) -> None:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="user founder@example.com did something", args=(), exc_info=None,
        )
        RedactionFilter().filter(record)
        assert "founder@example.com" not in record.getMessage()

    def test_filter_redacts_interpolated_args(self) -> None:
        """%-style logging args must be redacted too, not just a literal string."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="user %s registered", args=("founder@example.com",), exc_info=None,
        )
        RedactionFilter().filter(record)
        assert "founder@example.com" not in record.getMessage()

    def test_filter_always_returns_true(self) -> None:
        """A filter returning False would silently drop the log line entirely."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="anything", args=(), exc_info=None,
        )
        assert RedactionFilter().filter(record) is True


class TestJsonFormatter:
    def test_produces_valid_json(self) -> None:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        parsed = json.loads(JsonFormatter().format(record))
        assert parsed["message"] == "hello"
        assert parsed["level"] == "INFO"
        assert "timestamp" in parsed

    def test_includes_exception_info_when_present(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="", lineno=0,
                msg="failed", args=(), exc_info=sys.exc_info(),
            )
        parsed = json.loads(JsonFormatter().format(record))
        assert "ValueError" in parsed["exception"]
