"""Crawl sources and the human verification queue.

A :class:`CrawlSource` is a portal page or PDF the system monitors, with the hash
of what it saw last time. A :class:`PendingRevision` is a *candidate* change —
extracted, but not yet a fact — sitting in the verification queue until a human
approves, rejects or annotates it.

The critical property enforced across this module: nothing here writes to the
live scheme corpus. :mod:`bharat_os.seed.loader` is the only path that creates a
:class:`SchemeVersion`, and it is only ever invoked on curated or *approved*
data. A crawler finding a change, or an extractor parsing a PDF, produces a row
in this table and stops there.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bharat_os.models.base import Base, created_at_column, enum_column, uuid_pk
from bharat_os.models.enums import CrawlSourceType, ReviewStatus


class CrawlSource(Base):
    """One monitored URL."""

    __tablename__ = "crawl_source"

    id: Mapped[uuid.UUID] = uuid_pk()
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    source_type: Mapped[CrawlSourceType] = mapped_column(
        enum_column(CrawlSourceType, "crawl_source_type"), nullable=False
    )
    #: Scheme this source is believed to describe, for routing extracted content.
    scheme_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)

    #: Hash of the content as of the last successful crawl. ``None`` before the
    #: first crawl.
    last_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_crawled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    #: Whether this source's robots.txt permits crawling. Checked and cached so
    #: it is not re-fetched on every run, and so a source found to disallow
    #: crawling stays excluded until manually re-checked.
    robots_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = created_at_column()

    revisions: Mapped[list[PendingRevision]] = relationship(back_populates="source")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CrawlSource {self.url}>"


class PendingRevision(Base):
    """A candidate change awaiting human review.

    ``extracted_content`` holds whatever the pipeline produced — raw text for a
    plain change-detection hit, or a structured candidate scheme payload for an
    LLM extraction. Its shape is not fixed at the database level because the
    reviewer, not the schema, is the check on its correctness.
    """

    __tablename__ = "pending_revision"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crawl_source.id", ondelete="CASCADE"), nullable=False
    )

    previous_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Raw or structured content, exactly as produced by the pipeline stage that
    #: created this row. Never written anywhere else until approved.
    extracted_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    #: Confidence the extraction stage attached, when the content came from an
    #: LLM extraction rather than plain text. ``None`` for a bare change-detection
    #: hit with no extraction involved.
    extraction_confidence: Mapped[float | None] = mapped_column(nullable=True)

    status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus, "review_status"), nullable=False, default=ReviewStatus.PENDING
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    #: The reviewer's note — required on rejection, so "no" is never unexplained.
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = created_at_column()

    source: Mapped[CrawlSource] = relationship(back_populates="revisions")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<PendingRevision {self.status} source={self.source_id}>"
