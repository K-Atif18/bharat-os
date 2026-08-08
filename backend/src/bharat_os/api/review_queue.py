"""The human verification queue.

Everything here is reviewer-only. A crawler or PDF pipeline finding a change does
not make it true; a reviewer approving it is what the rest of the system is
allowed to treat as reviewed. Nothing in this router writes to the live scheme
corpus — see :mod:`bharat_os.services.review_queue` for why approval is
deliberately narrower than "publish".
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bharat_os.dependencies import DbSession, ReviewerUser
from bharat_os.models.crawl import PendingRevision
from bharat_os.models.enums import ReviewStatus
from bharat_os.schemas.review_queue import (
    AnnotateIn,
    PendingRevisionOut,
    RejectDecisionIn,
    ReviewDecisionIn,
)
from bharat_os.services.review_queue import (
    AlreadyReviewedError,
    ReviewNoteRequiredError,
    annotate,
    approve,
    reject,
)

router = APIRouter(prefix="/review-queue", tags=["verification-queue"])


def _out(revision: PendingRevision) -> PendingRevisionOut:
    return PendingRevisionOut(
        id=revision.id,
        source_id=revision.source_id,
        source_url=revision.source.url,
        source_type=revision.source.source_type,
        scheme_slug=revision.source.scheme_slug,
        status=revision.status,
        extracted_content=revision.extracted_content,
        extraction_confidence=revision.extraction_confidence,
        review_note=revision.review_note,
        reviewed_at=revision.reviewed_at,
        created_at=revision.created_at,
    )


def _load(db: DbSession, revision_id: str) -> PendingRevision:
    revision = db.scalar(
        select(PendingRevision)
        .where(PendingRevision.id == revision_id)
        .options(selectinload(PendingRevision.source))
    )
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such revision.")
    return revision


@router.get("", response_model=list[PendingRevisionOut])
def list_pending(user: ReviewerUser, db: DbSession) -> list[PendingRevisionOut]:
    """Everything awaiting a decision, oldest first — first in, first reviewed.

    A queue that becomes a bottleneck is a documented failure mode for this kind
    of product, so ordering favours clearing the backlog over any other sort.
    """
    rows = db.scalars(
        select(PendingRevision)
        .where(PendingRevision.status == ReviewStatus.PENDING)
        .options(selectinload(PendingRevision.source))
        .order_by(PendingRevision.created_at)
    ).all()
    return [_out(r) for r in rows]


@router.post("/{revision_id}/approve", response_model=PendingRevisionOut)
def approve_revision(
    revision_id: str, payload: ReviewDecisionIn, user: ReviewerUser, db: DbSession
) -> PendingRevisionOut:
    revision = _load(db, revision_id)
    try:
        approve(db, revision, reviewer_id=user.id, note=payload.note)
    except AlreadyReviewedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _out(revision)


@router.post("/{revision_id}/reject", response_model=PendingRevisionOut)
def reject_revision(
    revision_id: str, payload: RejectDecisionIn, user: ReviewerUser, db: DbSession
) -> PendingRevisionOut:
    revision = _load(db, revision_id)
    try:
        reject(db, revision, reviewer_id=user.id, note=payload.note)
    except AlreadyReviewedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ReviewNoteRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return _out(revision)


@router.post("/{revision_id}/annotate", response_model=PendingRevisionOut)
def annotate_revision(
    revision_id: str, payload: AnnotateIn, user: ReviewerUser, db: DbSession
) -> PendingRevisionOut:
    """Leave a note without deciding — for flagging something to a colleague."""
    revision = _load(db, revision_id)
    annotate(db, revision, note=payload.note)
    return _out(revision)
