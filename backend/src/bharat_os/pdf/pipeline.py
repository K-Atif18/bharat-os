"""End-to-end PDF ingestion: extract, structure, and queue for review.

Always ends in :class:`PendingRevision`, always ``PENDING``. This is the same
boundary the crawler observes, applied to the PDF path.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from bharat_os.models.crawl import CrawlSource, PendingRevision
from bharat_os.models.enums import CrawlSourceType, ReviewStatus
from bharat_os.pdf.extraction import PDFExtractionError, extract_text
from bharat_os.pdf.structured_extraction import extract_structured


def ingest_pdf(
    db: Session,
    path: Path | str,
    *,
    source_url: str,
    scheme_slug: str | None = None,
) -> PendingRevision:
    """Extract, structure, and queue one PDF as a candidate revision.

    Raises :class:`PDFExtractionError` only for a file that could not be opened at
    all — a file that opened but yielded low-confidence or empty extraction still
    produces a queued row, because "we could not confidently extract this" is
    itself useful information for the human reviewer, not a reason to discard it.
    """
    document = extract_text(path)

    source = _get_or_create_source(db, source_url, scheme_slug)
    result = extract_structured(document)

    revision = PendingRevision(
        source_id=source.id,
        previous_content_hash=None,
        new_content_hash=_hash_of(document.full_text),
        extracted_content={
            "scheme_name": result.scheme_name,
            "summary_of_change": result.summary_of_change,
            "extracted_fields": result.extracted_fields,
            "source_document": str(path),
        },
        extraction_confidence=result.confidence,
        status=ReviewStatus.PENDING,
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return revision


def _get_or_create_source(db: Session, source_url: str, scheme_slug: str | None) -> CrawlSource:
    from sqlalchemy import select

    source = db.scalar(select(CrawlSource).where(CrawlSource.url == source_url))
    if source is None:
        source = CrawlSource(
            url=source_url, source_type=CrawlSourceType.PDF, scheme_slug=scheme_slug
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    return source


def _hash_of(text: str) -> str:
    from bharat_os.crawler.change_detection import content_hash

    return content_hash(text)


__all__ = ["PDFExtractionError", "ingest_pdf"]
