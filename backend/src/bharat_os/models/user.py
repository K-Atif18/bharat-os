"""User accounts and applicant profiles.

Two fields here are sensitive personal data under the DPDP Act 2023: exact
annual turnover and social category. Both are stored encrypted via
:mod:`bharat_os.crypto` and must never be written to logs, error messages or
analytics.

Because those columns hold ciphertext they cannot be filtered or compared in
SQL. That is intentional — eligibility comparisons happen in the engine, in
memory, on a decrypted domain object.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bharat_os.crypto import EncryptedInt, EncryptedText
from bharat_os.models.base import (
    Base,
    created_at_column,
    enum_column,
    updated_at_column,
    uuid_pk,
)
from bharat_os.models.enums import EntityStage


class UserAccount(Base):
    """An authenticated account.

    An authenticated account. This table exists so that profiles have a
    real owner and erasure has a single root to delete from.
    """

    __tablename__ = "user_account"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Grants access to the verification queue. Not exposed via self-registration
    #: — set directly in the database for trusted reviewers, since the queue is
    #: where crawler and PDF output becomes a fact about a scheme.
    is_reviewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = created_at_column()

    profile: Mapped[Profile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    sessions: Mapped[list[UserSession]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    consents: Mapped[list[ConsentGrant]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )

    def has_consent(self, purpose: object) -> bool:
        """Whether an active consent exists for ``purpose``."""
        return any(grant.purpose == purpose and grant.is_active for grant in self.consents)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<UserAccount {self.id}>"


class Profile(Base):
    """An applicant entity: a startup or an MSME in v1.

    Only what scheme matching actually needs is collected. Anything not used by
    a criterion in the knowledge base does not belong here.
    """

    __tablename__ = "profile"
    __table_args__ = (
        CheckConstraint("employee_count IS NULL OR employee_count >= 0", name="employees_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    entity_name: Mapped[str] = mapped_column(String(300), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    stage: Mapped[EntityStage] = mapped_column(
        enum_column(EntityStage, "entity_stage"), nullable=False
    )

    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    incorporation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_woman_led: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Registrations held, as a list of RegistrationType values. Many schemes
    # gate eligibility on these, so absence is meaningful.
    registrations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # --- Sensitive personal data. Encrypted at rest. Never log these. ---
    annual_turnover_inr: Mapped[int | None] = mapped_column(EncryptedInt, nullable=True)
    social_category: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    user: Mapped[UserAccount] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        # Deliberately omits every sensitive field.
        return f"<Profile {self.id} state={self.state} sector={self.sector}>"
