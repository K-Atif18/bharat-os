"""Applications and their outcomes.

Outcome data is the asset that compounds: knowing which applications succeeded,
which failed, and why is knowledge that exists nowhere else and cannot be
scraped. These tables are empty at launch by definition, but the schema has to
exist from the start or the data is lost forever.

Two design points follow from that:

* ``Application.user_id`` is nullable with ``ON DELETE SET NULL``. When a user
  exercises their right to erasure, the link to them is severed while the
  anonymised outcome row survives.
* :class:`Outcome` carries its own de-identified dimensions (state, sector,
  turnover *band* rather than exact turnover) so aggregate analysis remains
  possible after erasure without retaining personal data.

Nothing in this module advances an application to ``SUBMITTED``. Status changes
past ``READY_FOR_REVIEW`` are user-initiated, always.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bharat_os.models.base import Base, created_at_column, enum_column, uuid_pk
from bharat_os.models.enums import ApplicationStatus, OutcomeType


class Application(Base):
    """A user's application against a specific scheme *version*.

    Pinning to a version rather than a scheme is what makes an assessment
    explicable months later, after the ministry has amended its criteria.
    """

    __tablename__ = "application"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Nullable so erasure can sever the link without destroying outcome history.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_version.id", ondelete="RESTRICT"), nullable=False
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        enum_column(ApplicationStatus, "application_status"),
        nullable=False,
        default=ApplicationStatus.DRAFT,
    )
    # Reference number issued by the government portal, entered by the user
    # after they submit themselves.
    external_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status_update: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = created_at_column()

    #: The exact scheme revision this application was assessed against.
    scheme_version: Mapped[SchemeVersion] = relationship()  # noqa: F821
    outcome: Mapped[Outcome | None] = relationship(
        back_populates="application", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Application {self.id} status={self.status}>"


class Outcome(Base):
    """The decision on an application, including why it failed.

    Rejection reasons are the most valuable field in the schema. Government
    portals rarely surface them, so they are captured from the user and treated
    as first-class data.
    """

    __tablename__ = "outcome"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    outcome_type: Mapped[OutcomeType] = mapped_column(
        enum_column(OutcomeType, "outcome_type"), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amount_sanctioned_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Elapsed days from submission to decision: the difference between the
    # timeline a scheme advertises and the one applicants actually experience.
    days_to_decision: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- De-identified dimensions, retained after user erasure. ---
    # Denormalised so aggregate analysis never needs to join back to a profile.
    applicant_state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    applicant_sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # A coarse band such as "1cr-5cr", never an exact figure.
    applicant_turnover_band: Mapped[str | None] = mapped_column(String(40), nullable=True)

    created_at: Mapped[datetime] = created_at_column()

    application: Mapped[Application] = relationship(back_populates="outcome")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Outcome {self.outcome_type}>"
