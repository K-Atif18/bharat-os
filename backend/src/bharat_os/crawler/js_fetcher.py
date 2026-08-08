"""Fetching JavaScript-rendered pages via a real browser.

Playwright is imported inside the function, not at module level, so a deployment
that only crawls static pages never needs the browser binaries installed. This
module is the one place in the codebase that touches a browser.
"""

from __future__ import annotations

from bharat_os.crawler.robots import USER_AGENT
from bharat_os.crawler.static_fetcher import FetchError, RateLimiter

REQUEST_TIMEOUT_MS = 30_000


def fetch_rendered(
    url: str,
    *,
    limiter: RateLimiter | None = None,
    wait_selector: str | None = None,
) -> str:
    """Render ``url`` in a headless browser and return the resulting HTML.

    ``wait_selector``, when given, waits for that CSS selector to appear before
    capturing content — needed for pages whose eligibility criteria are injected
    by client-side JavaScript after the initial load.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise FetchError(
            "Playwright is not installed. Install it with "
            "`pip install playwright && playwright install chromium` to crawl "
            "JavaScript-rendered sources."
        ) from exc

    from urllib.parse import urlparse

    active_limiter = limiter or RateLimiter()
    active_limiter.wait(urlparse(url).netloc)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(url, timeout=REQUEST_TIMEOUT_MS, wait_until="networkidle")
                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=REQUEST_TIMEOUT_MS)
                return page.content()
            finally:
                browser.close()
    except Exception as exc:  # Playwright raises its own exception hierarchy.
        raise FetchError(f"Could not render {url}: {exc}") from exc
