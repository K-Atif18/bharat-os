"""Detecting substantive change, distinct from incidental page noise.

Government portals inject timestamps, session tokens and rotating banners into
otherwise-static pages. Hashing the raw HTML would fire a "change" on every crawl
regardless of whether anything a scheme applicant cares about moved. This module
hashes a normalised form of the content instead, so the signal is content change,
not markup churn.
"""

from __future__ import annotations

import hashlib
import re

#: Patterns stripped before hashing: timestamps, common session/nonce params,
#: and whitespace runs. Deliberately conservative — under-normalising causes
#: false positives (noisy but safe); over-normalising could mask a real change,
#: which is the failure this module exists to avoid.
_TIMESTAMP_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\b")
_SESSION_PARAM_PATTERN = re.compile(r"(?:sessionid|token|nonce|csrf)=[\w-]+", re.IGNORECASE)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalise(content: str) -> str:
    """Strip volatile noise that is not a substantive content change."""
    text = _TIMESTAMP_PATTERN.sub("", content)
    text = _SESSION_PARAM_PATTERN.sub("", text)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def content_hash(content: str) -> str:
    """Stable hash of the normalised content."""
    return hashlib.sha256(normalise(content).encode("utf-8")).hexdigest()


def has_changed(previous_hash: str | None, current_content: str) -> tuple[bool, str]:
    """Whether ``current_content`` differs from what ``previous_hash`` represents.

    Returns ``(changed, new_hash)`` so the caller can store the new hash regardless
    of the outcome — a source is considered "up to date" after this check either
    way.
    """
    new_hash = content_hash(current_content)
    return (previous_hash != new_hash), new_hash
