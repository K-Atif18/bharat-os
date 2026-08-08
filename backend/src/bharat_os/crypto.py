"""Encryption at rest for sensitive personal data.

Under the DPDP Act 2023, fields such as annual turnover and social category are
sensitive personal data. They are encrypted before they reach the database and
decrypted only in memory, so a database dump never exposes them in plaintext.

Values are stored as Fernet tokens in ordinary ``TEXT`` columns, which keeps the
schema portable between SQLite and Postgres.
"""

from __future__ import annotations

import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Dialect, Text, TypeDecorator

from bharat_os.config import get_settings

logger = logging.getLogger(__name__)

_ephemeral_key: bytes | None = None


class DecryptionError(RuntimeError):
    """Raised when stored ciphertext cannot be decrypted with the active key."""


def _resolve_key() -> bytes:
    """Return the Fernet key, generating an ephemeral one in development.

    An ephemeral key means development data written in one process cannot be
    read by the next. That is deliberate: it makes a missing key obvious during
    development instead of silently persisting unreadable rows in production,
    where :meth:`Settings.validate_production_requirements` requires a real key.
    """
    global _ephemeral_key
    settings = get_settings()
    if settings.encryption_key:
        return settings.encryption_key.encode("utf-8")
    if settings.environment == "production":  # pragma: no cover - guarded at startup
        raise RuntimeError("BHARAT_OS_ENCRYPTION_KEY is required in production")
    if _ephemeral_key is None:
        _ephemeral_key = Fernet.generate_key()
        logger.warning(
            "BHARAT_OS_ENCRYPTION_KEY is unset; generated an ephemeral key. "
            "Encrypted values will not survive a restart."
        )
    return _ephemeral_key


def _cipher() -> Fernet:
    return Fernet(_resolve_key())


def encrypt_text(plaintext: str) -> str:
    """Encrypt ``plaintext`` into a Fernet token."""
    return _cipher().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str) -> str:
    """Decrypt a Fernet token produced by :func:`encrypt_text`."""
    try:
        return _cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise DecryptionError(
            "Stored value could not be decrypted with the active encryption key"
        ) from exc


class EncryptedText(TypeDecorator[str]):
    """A ``TEXT`` column whose Python value is transparently encrypted.

    The database only ever sees ciphertext. Never include a column of this type
    in log output or error messages.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return encrypt_text(str(value))

    def process_result_value(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return decrypt_text(value)


class EncryptedInt(TypeDecorator[int]):
    """An integer stored as an encrypted ``TEXT`` column.

    Used for monetary amounts such as annual turnover. Because the stored form
    is ciphertext, these fields cannot be filtered or compared in SQL —
    comparisons happen in the eligibility engine, in memory, by design.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return encrypt_text(str(int(value)))

    def process_result_value(self, value: Any, dialect: Dialect) -> int | None:
        if value is None:
            return None
        return int(decrypt_text(value))
