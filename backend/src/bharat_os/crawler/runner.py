"""Running a crawl pass over configured sources.

Ties together robots compliance, fetching, change detection, LLM extraction and
queue insertion. The one invariant enforced at this layer, on top of everything
the modules below already enforce individually: **a detected change always
becomes a** :class:`PendingRevision` **and never a** :class:`SchemeVersion`.
Nothing here calls the seed loader.

LLM extraction runs on every detected change, using the same
:func:`bharat_os.pdf.structured_extraction.extract_structured` the PDF pipeline
uses — the model does not care whether the text it is given came from a PDF or
a web page, and duplicating that logic here would mean two places to keep the
extraction prompt and confidence handling consistent. A low-confidence or
failed extraction still produces a queued row: "we could not confidently
extract this" is itself useful information for the human reviewer, exactly as
in the PDF pipeline, not a reason to fall back to raw text only.

Failure isolation is deliberate: one source failing (network error, changed page
structure, robots.txt now disallowing) must not abort the run for every other
source. Each source's outcome is recorded independently.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from bharat_os.crawler.change_detection import has_changed
from bharat_os.crawler.html_text import html_to_text
from bharat_os.crawler.robots import is_allowed
from bharat_os.crawler.static_fetcher import FetchError, RateLimiter, fetch_static
from bharat_os.models.crawl import CrawlSource, PendingRevision
from bharat_os.models.enums import CrawlSourceType, ReviewStatus
from bharat_os.pdf.extraction import ExtractedDocument, ExtractedPage
from bharat_os.pdf.structured_extraction import extract_structured

logger = logging.getLogger(__name__)

#: Consecutive failures after which a source is deactivated rather than retried
#: forever against a page that may no longer exist.
MAX_CONSECUTIVE_FAILURES = 5


@dataclass(frozen=True)
class CrawlOutcome:
    source_id: str
    url: str
    #: True if this run produced a new PendingRevision.
    changed: bool
    #: None on success; the reason on failure.
    error: str | None = None
    skipped_by_robots: bool = False
    #: Confidence the extraction stage attached, when a change produced one.
    extraction_confidence: float | None = None


def _fetch(source: CrawlSource, limiter: RateLimiter) -> str:
    if source.source_type is CrawlSourceType.JS_RENDERED:
        from bharat_os.crawler.js_fetcher import fetch_rendered

        return fetch_rendered(source.url, limiter=limiter)
    return fetch_static(source.url, limiter=limiter)



def crawl_source(
    db: Session, source: CrawlSource, *, limiter: RateLimiter | None = None
) -> CrawlOutcome:
    """Crawl one source, queuing a revision if its content changed.

    Skips a source whose robots.txt disallows crawling, marking it so, rather than
    fetching it anyway and dealing with the consequence afterwards.
    """
    active_limiter = limiter or RateLimiter()

    if not is_allowed(source.url):
        source.robots_allowed = False
        db.commit()
        logger.info("robots.txt disallows crawling %s; skipping", source.url)
        return CrawlOutcome(str(source.id), source.url, changed=False, skipped_by_robots=True)

    source.robots_allowed = True

    try:
        content = _fetch(source, active_limiter)
    except FetchError as exc:
        source.consecutive_failures += 1
        if source.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            source.is_active = False
            logger.warning(
                "Deactivating %s after %d consecutive failures",
                source.url,
                source.consecutive_failures,
            )
        db.commit()
        return CrawlOutcome(str(source.id), source.url, changed=False, error=str(exc))

    source.consecutive_failures = 0
    source.last_crawled_at = datetime.now(UTC)

    changed, new_hash = has_changed(source.last_content_hash, content)

    if not changed:
        db.commit()
        return CrawlOutcome(str(source.id), source.url, changed=False)

    extraction_confidence = None
    extracted_content: dict = {"raw_html_excerpt": content[:20_000]}

    if source.source_type is not CrawlSourceType.PDF:
        text = html_to_text(content)
        document = ExtractedDocument(
            source_path=source.url,
            pages=(ExtractedPage(page_number=1, text=text),),
        )
        result = extract_structured(document)
        extraction_confidence = result.confidence
        extracted_content = {
            "raw_html_excerpt": content[:20_000],
            "scheme_name": result.scheme_name,
            "summary_of_change": result.summary_of_change,
            "extracted_fields": result.extracted_fields,
            "requires_review": result.requires_review,
            "extraction_provider": result.provider,
            "extraction_model": result.model,
        }

    revision = PendingRevision(
        source_id=source.id,
        previous_content_hash=source.last_content_hash,
        new_content_hash=new_hash,
        extracted_content=extracted_content,
        extraction_confidence=extraction_confidence,
        status=ReviewStatus.PENDING,
    )
    db.add(revision)
    source.last_content_hash = new_hash
    db.commit()

    return CrawlOutcome(
        str(source.id), source.url, changed=True, extraction_confidence=extraction_confidence
    )


def crawl_all(db: Session, *, only_active: bool = True) -> list[CrawlOutcome]:
    """Crawl every configured source, isolating failures per source."""
    from sqlalchemy import select

    query = select(CrawlSource)
    if only_active:
        query = query.where(CrawlSource.is_active.is_(True))

    sources = db.scalars(query).all()
    limiter = RateLimiter()
    outcomes = []

    for source in sources:
        try:
            outcomes.append(crawl_source(db, source, limiter=limiter))
        except Exception as exc:  # noqa: BLE001 - a single source's bug must not sink the run
            logger.exception("Unexpected error crawling %s", source.url)
            outcomes.append(CrawlOutcome(str(source.id), source.url, changed=False, error=str(exc)))

    return outcomes
