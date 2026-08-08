"""Small, bounded rate limits for a single API process.

Authenticated requests are keyed by a digest of the session cookie; anonymous
requests use the direct socket address. This protects the hackathon deployment
without adding Redis. A multi-instance deployment must replace this process-local
store with a shared limiter.
"""

from __future__ import annotations

import hashlib
import time
from threading import Lock
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

#: Requests permitted per window, per client.
DEFAULT_LIMIT = 60
DEFAULT_WINDOW_SECONDS = 60.0
#: Hard cap prevents arbitrary cookies or source addresses growing memory forever.
MAX_TRACKED_KEYS = 10_000

_hits: dict[str, list[float]] = {}
_hits_lock = Lock()


def reset_rate_limits() -> None:
    """Clear all tracked hits for test isolation."""
    with _hits_lock:
        _hits.clear()


def _client_key(request: Request) -> str:
    # Signed-in users receive independent budgets even when they share a NAT or
    # reverse proxy. Hash the opaque cookie so process memory never contains a
    # second copy of a usable session credential.
    session_token = request.cookies.get("bharat_os_session")
    if session_token:
        digest = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
        return f"session:{digest}"

    # Do not trust X-Forwarded-For from arbitrary callers: unless a deployment
    # validates proxy hops, that header is user-controlled and would let an
    # attacker choose a fresh key for every request.
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def _evict_oldest_key() -> None:
    """Keep memory bounded when presented with many one-off client identities."""
    if len(_hits) < MAX_TRACKED_KEYS:
        return
    oldest_key = min(_hits, key=lambda candidate: _hits[candidate][-1])
    del _hits[oldest_key]


def rate_limit(
    limit: int = DEFAULT_LIMIT,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
    *,
    scope: str = "general",
):
    """Build a dependency enforcing one scoped sliding-window budget."""

    def dependency(request: Request) -> None:
        key = f"{scope}:{_client_key(request)}"
        now = time.monotonic()
        window_start = now - window_seconds

        with _hits_lock:
            hits = _hits.get(key)
            if hits is None:
                _evict_oldest_key()
                hits = []
                _hits[key] = hits

            while hits and hits[0] < window_start:
                hits.pop(0)

            if len(hits) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait before trying again.",
                )

            hits.append(now)

    return dependency


#: A stricter limit for authentication endpoints, where the cost of abuse
#: (credential stuffing) is higher than for read-only browsing.
AuthRateLimit = Annotated[
    None,
    Depends(rate_limit(limit=10, window_seconds=60.0, scope="authentication")),
]

#: LLM-backed endpoints have direct latency and cost, so they get a smaller,
#: per-session budget than ordinary authenticated reads.
ExpensiveRateLimit = Annotated[
    None,
    Depends(rate_limit(limit=10, window_seconds=60.0, scope="llm")),
]
