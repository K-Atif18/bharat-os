"""Sessions and consent records.

Sessions are server-side. A random token goes to the browser in an HttpOnly
cookie; only its hash is stored. That means a database disclosure does not hand
an attacker usable sessions, and it means a session can actually be revoked —
which a self-contained bearer token cannot be, and which the right to erasure
requires.

Consent is recorded per purpose, with the policy version in force at the time.
Withdrawal is a new state on the existing record rather than a deletion, because
proving what a user agreed to and when is the point of keeping the record.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bharat_os.models.base import Base, created_at_column, enum_column, uuid_pk
from bharat_os.models.enums import ConsentPurpose


class UserSession(Base):
    """A server-side session, revocable and expiring."""

    __tablename__ = "user_session"
    __table_args__ = (Index("ix_user_session_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    #: SHA-256 of the session token. The token itself is never persisted.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at_column()

    user: Mapped[UserAccount] = relationship(back_populates="sessions")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<UserSession {self.id} user={self.user_id}>"


class ConsentGrant(Base):
    """A user's decision about one processing purpose.

    One row per user and purpose. Granting again after withdrawal clears the
    withdrawal and updates the timestamp, so the current state is always a single
    row per purpose rather than an event log that has to be replayed.
    """

    __tablename__ = "consent_grant"
    __table_args__ = (
        UniqueConstraint("user_id", "purpose", name="uq_consent_grant_user_id_purpose"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[ConsentPurpose] = mapped_column(
        enum_column(ConsentPurpose, "consent_purpose"), nullable=False
    )
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Which version of the privacy notice the user agreed to.
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = created_at_column()

    user: Mapped[UserAccount] = relationship(back_populates="consents")  # noqa: F821

    @property
    def is_active(self) -> bool:
        return self.granted_at is not None and self.withdrawn_at is None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ConsentGrant {self.purpose} active={self.is_active}>"
