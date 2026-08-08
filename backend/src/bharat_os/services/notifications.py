"""Scheduling deadline reminders.

The "fires once and only once" guarantee comes from the database's unique
constraint on (user, scheme version, offset), not from careful scheduler logic —
a scheduler that runs twice, or runs late and catches up, must still be safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bharat_os.models.notification import DeadlineNotification
from bharat_os.services.deadlines import NOTIFICATION_OFFSETS_DAYS


@dataclass(frozen=True)
class DueNotification:
    user_id: object
    scheme_version_id: object
    offset_days: int
    close_date: date


def due_offsets(close_date: date, as_of: date | None = None) -> list[int]:
    """Which reminder offsets have been reached as of today.

    Returns every offset less than or equal to the number of days remaining, so a
    scheduler that missed a day still catches up on the reminders it owes rather
    than skipping them.
    """
    today = as_of or date.today()
    days_remaining = (close_date - today).days
    if days_remaining < 0:
        return []
    return sorted(
        (offset for offset in NOTIFICATION_OFFSETS_DAYS if offset >= days_remaining),
        reverse=True,
    )


def record_sent(
    db: Session,
    *,
    user_id: object,
    scheme_version_id: object,
    offset_days: int,
) -> bool:
    """Record that a reminder was sent, returning whether this call actually sent it.

    ``False`` means the unique constraint rejected a duplicate — the reminder was
    already sent, so the caller must not send it again. This makes the function
    safe to call from a scheduler that might overlap or retry.
    """
    db.add(
        DeadlineNotification(
            user_id=user_id,
            scheme_version_id=scheme_version_id,
            offset_days=offset_days,
        )
    )
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def already_sent(
    db: Session, *, user_id: object, scheme_version_id: object, offset_days: int
) -> bool:
    return (
        db.scalar(
            select(DeadlineNotification.id).where(
                DeadlineNotification.user_id == user_id,
                DeadlineNotification.scheme_version_id == scheme_version_id,
                DeadlineNotification.offset_days == offset_days,
            )
        )
        is not None
    )


def pending_for_user(
    db: Session,
    *,
    user_id: object,
    windows: list[tuple[object, datetime | date | None]],
    as_of: date | None = None,
) -> list[DueNotification]:
    """Reminders that are due for a user and not yet sent, across their windows."""
    today = as_of or date.today()
    due: list[DueNotification] = []

    for scheme_version_id, close in windows:
        if close is None:
            continue
        close_date = close.date() if isinstance(close, datetime) else close
        for offset in due_offsets(close_date, today):
            if not already_sent(
                db, user_id=user_id, scheme_version_id=scheme_version_id, offset_days=offset
            ):
                due.append(
                    DueNotification(
                        user_id=user_id,
                        scheme_version_id=scheme_version_id,
                        offset_days=offset,
                        close_date=close_date,
                    )
                )
    return due
