"""Respecting robots.txt.

Checked and cached per source rather than trusted to the crawler's own judgement
call at fetch time — a source found to disallow crawling is marked and stays
excluded until someone re-checks it, rather than being silently retried forever.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

#: Identifies this crawler in the User-Agent header and to robots.txt rules.
USER_AGENT = "BharatOS-SchemeMonitor/1.0 (+https://github.com/bharat-os; scheme data verification)"

REQUEST_TIMEOUT_SECONDS = 15.0


def is_allowed(url: str) -> bool:
    """Whether robots.txt at ``url``'s host permits fetching ``url``.

    Fails closed: if robots.txt cannot be retrieved or parsed, the URL is treated
    as disallowed. A site that cannot be checked is not a site that has granted
    permission.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = httpx.get(
            robots_url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        logger.warning("robots.txt unreachable for %s (%s); treating as disallowed", url, exc)
        return False

    if response.status_code == 404:
        # No robots.txt published is conventionally treated as "allow", per the
        # standard most crawlers follow.
        return True
    if response.status_code != 200:
        logger.warning(
            "robots.txt at %s returned HTTP %s; treating as disallowed",
            robots_url,
            response.status_code,
        )
        return False

    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)
