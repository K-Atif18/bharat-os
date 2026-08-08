"""Fetching static pages, with rate limiting and no crawler ever hammering a
government site.

Playwright is imported lazily by :mod:`bharat_os.crawler.js_fetcher` and never by
this module, so installing the static-only crawler never requires a browser
download.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from bharat_os.crawler.robots import USER_AGENT

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30.0

#: Minimum seconds between requests to the same host. Government portals are
#: shared infrastructure serving citizens, not a resource to be maximised against.
MIN_DELAY_SECONDS = 3.0


@dataclass
class RateLimiter:
    """Per-host minimum delay, enforced by actually sleeping.

    Kept as an object rather than a bare sleep call so a single limiter can be
    shared across many fetches in one crawl run and enforce the delay across all
    of them, not just consecutive calls to the same function.
    """

    min_delay_seconds: float = MIN_DELAY_SECONDS
    _last_request_at: dict[str, float] | None = None

    def __post_init__(self) -> None:
        if self._last_request_at is None:
            self._last_request_at = {}

    def wait(self, host: str) -> None:
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            remaining = self.min_delay_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at[host] = time.monotonic()


class FetchError(RuntimeError):
    """A page could not be retrieved."""


def fetch_static(url: str, *, limiter: RateLimiter | None = None) -> str:
    """Fetch a static page's HTML.

    Raises :class:`FetchError` on any failure rather than returning empty content,
    so a caller iterating many sources can catch this per-source and continue,
    rather than a transient failure on one page being indistinguishable from that
    page's content becoming empty.
    """
    from urllib.parse import urlparse

    active_limiter = limiter or RateLimiter()
    active_limiter.wait(urlparse(url).netloc)

    try:
        response = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        raise FetchError(f"Could not fetch {url}: {exc}") from exc

    if response.status_code != 200:
        raise FetchError(f"{url} returned HTTP {response.status_code}")

    return response.text
