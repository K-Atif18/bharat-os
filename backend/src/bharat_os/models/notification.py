"""Tracking which deadline reminders have already fired.

One row is created the moment a reminder is *sent*, keyed so that the same
reminder for the same user, scheme version and offset cannot be recorded twice.
This is what makes "fires once and only once" a database constraint rather than a
hope about scheduler behaviour.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bharat_os.models.base import Base, created_at_column, uuid_pk


class DeadlineNotification(Base):
    """A record that one reminder was sent for one user and one deadline."""

    __tablename__ = "deadline_notification"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "scheme_version_id",
            "offset_days",
            name="uq_deadline_notification_user_scheme_offset",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_version.id", ondelete="CASCADE"), nullable=False
    )
    #: Which reminder this is: 30, 14, 7 or 1 days before close.
    offset_days: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_at: Mapped[datetime] = created_at_column()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<DeadlineNotification user={self.user_id} offset={self.offset_days}d>"
