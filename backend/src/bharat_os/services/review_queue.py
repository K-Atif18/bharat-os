"""Acting on the verification queue.

Three actions, and only three: approve, reject, annotate. Approval is the only one
that has a downstream effect, and even that effect is narrow — it marks the
revision approved and records who approved it. It does not itself write a new
:class:`SchemeVersion`. Turning an approved revision's ``extracted_fields`` into
an actual curated scheme file remains a deliberate, separate, human-authored step
via the normal seed corpus workflow, because an approved *candidate* and a
verified *fact ready to publish* are not automatically the same thing — the
reviewer approved that the extraction looks right, which is necessary but not
sufficient for publication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from bharat_os.models.crawl import PendingRevision
from bharat_os.models.enums import ReviewStatus


class AlreadyReviewedError(ValueError):
    """Raised when acting on a revision that has already left PENDING."""


class ReviewNoteRequiredError(ValueError):
    """Raised when rejecting without a note — "no" must always be explained."""


@dataclass(frozen=True)
class ReviewAction:
    revision_id: str
    new_status: ReviewStatus
    reviewed_by_user_id: str
    note: str | None


def _require_pending(revision: PendingRevision) -> None:
    if revision.status is not ReviewStatus.PENDING:
        raise AlreadyReviewedError(
            f"Revision {revision.id} was already {revision.status.value} on "
            f"{revision.reviewed_at}; it cannot be reviewed again."
        )


def approve(
    db: Session, revision: PendingRevision, *, reviewer_id: object, note: str | None = None
) -> PendingRevision:
    _require_pending(revision)
    revision.status = ReviewStatus.APPROVED
    revision.reviewed_by_user_id = reviewer_id
    revision.reviewed_at = datetime.now(UTC)
    revision.review_note = note
    db.commit()
    db.refresh(revision)
    return revision


def reject(
    db: Session, revision: PendingRevision, *, reviewer_id: object, note: str
) -> PendingRevision:
    """Reject, with a mandatory note.

    A rejection with no reason is exactly the kind of unexplained "no" this
    product exists to eliminate from government processes; it should not
    reappear inside the tooling that builds the corpus.
    """
    _require_pending(revision)
    if not note or not note.strip():
        raise ReviewNoteRequiredError("A rejection must include a reason.")

    revision.status = ReviewStatus.REJECTED
    revision.reviewed_by_user_id = reviewer_id
    revision.reviewed_at = datetime.now(UTC)
    revision.review_note = note
    db.commit()
    db.refresh(revision)
    return revision


def annotate(db: Session, revision: PendingRevision, *, note: str) -> PendingRevision:
    """Attach a note without changing status — for a reviewer flagging something
    for a colleague before a decision is made."""
    revision.review_note = note
    db.commit()
    db.refresh(revision)
    return revision
