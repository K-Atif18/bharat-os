"""Password hashing and session tokens.

Passwords use Argon2id, which is memory-hard and the current recommendation for
password storage. Session tokens are random and stored only as a SHA-256 digest,
so the database never holds a value that can be replayed as a credential.

Note the asymmetry: passwords need a slow, salted hash because they are
low-entropy and human-chosen. Session tokens are 256 bits of randomness, so a
fast unsalted digest is sufficient and appropriate — they cannot be brute-forced
or rainbow-tabled.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

#: Minimum password length. Long passphrases beat complexity rules, so length is
#: the only constraint imposed.
MIN_PASSWORD_LENGTH = 12

#: Session lifetime in days.
SESSION_TTL_DAYS = 14

_hasher = PasswordHasher()


class WeakPasswordError(ValueError):
    """Raised when a password does not meet the minimum policy."""


def validate_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters. "
            "A memorable passphrase is stronger than a short complex string."
        )


def hash_password(password: str) -> str:
    """Hash a password with Argon2id after checking the length policy."""
    validate_password_strength(password)
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verify a password against its hash.

    Returns ``False`` rather than raising for any failure, including a missing
    hash, so callers cannot accidentally distinguish "no such user" from "wrong
    password" and leak account existence.
    """
    if not password_hash:
        # Still do work, so a request for a nonexistent account does not return
        # measurably faster than one for a real account.
        _hasher.hash("timing-equalisation-placeholder")
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Whether a stored hash was made with outdated parameters."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


def generate_session_token() -> str:
    """A fresh, unguessable session token."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """The stored form of a session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(candidate_hash: str, stored_hash: str) -> bool:
    """Constant-time comparison of token digests."""
    return hmac.compare_digest(candidate_hash, stored_hash)
