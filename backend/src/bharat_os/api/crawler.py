"""Triggering a crawl run on demand.

Everything here is reviewer-only, same gate as ``api/review_queue.py`` — this
endpoint makes real outbound network requests to government sites and real
LLM calls per changed source, so it is not something to leave open to every
authenticated user, let alone the public. Triggering a crawl never writes to
the live scheme corpus; see :mod:`bharat_os.crawler.runner` for the enforced
boundary this endpoint sits in front of.
"""

from __future__ import annotations

import pydantic
from fastapi import APIRouter
from sqlalchemy import select

from bharat_os.crawler.runner import crawl_all
from bharat_os.dependencies import DbSession, ReviewerUser
from bharat_os.models.crawl import CrawlSource

router = APIRouter(prefix="/crawler", tags=["crawler"])


class CrawlOutcomeOut(pydantic.BaseModel):
    source_id: str
    url: str
    changed: bool
    error: str | None
    skipped_by_robots: bool
    extraction_confidence: float | None


class CrawlRunOut(pydantic.BaseModel):
    sources_crawled: int
    changed_count: int
    skipped_by_robots_count: int
    failed_count: int
    outcomes: list[CrawlOutcomeOut]


class CrawlSourceOut(pydantic.BaseModel):
    id: str
    url: str
    source_type: str
    scheme_slug: str | None
    is_active: bool
    robots_allowed: bool
    consecutive_failures: int


@router.post("/run", response_model=CrawlRunOut)
def run_crawl(user: ReviewerUser, db: DbSession) -> CrawlRunOut:
    """Crawl every active source now, queuing any detected change for review.

    Synchronous and blocking on purpose: a hackathon-scale source list crawls
    in seconds, and a reviewer triggering this wants to see the outcome
    immediately, not poll a job status. Revisit if the source list grows large
    enough that this becomes a real request-timeout risk.
    """
    outcomes = crawl_all(db)
    return CrawlRunOut(
        sources_crawled=len(outcomes),
        changed_count=sum(1 for o in outcomes if o.changed),
        skipped_by_robots_count=sum(1 for o in outcomes if o.skipped_by_robots),
        failed_count=sum(1 for o in outcomes if o.error),
        outcomes=[
            CrawlOutcomeOut(
                source_id=o.source_id,
                url=o.url,
                changed=o.changed,
                error=o.error,
                skipped_by_robots=o.skipped_by_robots,
                extraction_confidence=o.extraction_confidence,
            )
            for o in outcomes
        ],
    )


@router.get("/sources", response_model=list[CrawlSourceOut])
def list_sources(user: ReviewerUser, db: DbSession) -> list[CrawlSourceOut]:
    """Every configured crawl source, for a reviewer deciding what to trigger."""
    sources = db.scalars(select(CrawlSource).order_by(CrawlSource.url)).all()
    return [
        CrawlSourceOut(
            id=str(source.id),
            url=source.url,
            source_type=source.source_type.value,
            scheme_slug=source.scheme_slug,
            is_active=source.is_active,
            robots_allowed=source.robots_allowed,
            consecutive_failures=source.consecutive_failures,
        )
        for source in sources
    ]
