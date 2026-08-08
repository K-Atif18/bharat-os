"""The scheme knowledge base.

Schemes are **versioned**. A :class:`Scheme` row is a stable identity (a slug
that never changes); each :class:`SchemeVersion` row is an immutable snapshot of
that scheme's content at a point in time. Criteria, documents, windows and
benefits hang off a *version*, never off the stable identity.

This matters because an application submitted last March was assessed against
the criteria as they stood last March. If revisions overwrote each other, that
assessment would become inexplicable the moment a ministry quietly amended a
circular.

Every row carrying a factual claim about a scheme also carries its provenance:
where the claim came from and when a human last confirmed it. This is enforced
by ``NOT NULL`` columns, not by convention.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bharat_os.models.base import Base, created_at_column, enum_column, uuid_pk
from bharat_os.models.enums import (
    ApplicationDifficulty,
    AuthorityType,
    BenefitType,
    CriterionType,
    NotificationSource,
    Recurrence,
    SchemeStatus,
    SchemeType,
)


class ProvenanceMixin:
    """Mandatory sourcing for any persisted claim about a scheme.

    ``source_url`` is where the claim was read. ``last_verified_at`` is when a
    human or verified pipeline run last confirmed it against that source.
    ``verified_by_human`` distinguishes hand-checked data from machine
    extraction that has not yet been reviewed.
    """

    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Authority(Base):
    """A body that administers schemes or issues documents."""

    __tablename__ = "authority"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    authority_type: Mapped[AuthorityType] = mapped_column(
        enum_column(AuthorityType, "authority_type"), nullable=False
    )
    portal_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(300), nullable=True)
    document_acceptance_method: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = created_at_column()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Authority {self.slug}>"


class Scheme(Base):
    """Stable identity of a scheme across all its revisions."""

    __tablename__ = "scheme"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    created_at: Mapped[datetime] = created_at_column()

    versions: Mapped[list[SchemeVersion]] = relationship(
        back_populates="scheme",
        cascade="all, delete-orphan",
        order_by="SchemeVersion.version",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Scheme {self.slug}>"


class SchemeVersion(Base):
    """An immutable snapshot of a scheme's published terms.

    Exactly one version per scheme should have ``is_current`` set. That
    invariant is maintained by the loader and asserted by tests rather than by a
    partial unique index, which behaves inconsistently across backends.
    """

    __tablename__ = "scheme_version"
    __table_args__ = (
        UniqueConstraint("scheme_id", "version", name="uq_scheme_version_scheme_id_version"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "benefit_value_max IS NULL OR benefit_value_min IS NULL "
            "OR benefit_value_max >= benefit_value_min",
            name="benefit_range_ordered",
        ),
        Index("ix_scheme_version_current", "scheme_id", "is_current"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    scheme_type: Mapped[SchemeType] = mapped_column(
        enum_column(SchemeType, "scheme_type"), nullable=False
    )
    status: Mapped[SchemeStatus] = mapped_column(
        enum_column(SchemeStatus, "scheme_status"), nullable=False, default=SchemeStatus.ACTIVE
    )

    administering_ministry: Mapped[str] = mapped_column(String(300), nullable=False)
    implementing_agency: Mapped[str | None] = mapped_column(String(300), nullable=True)
    authority_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("authority.id", ondelete="SET NULL"), nullable=True
    )

    # Targeting. An empty ``states`` list means the scheme is all-India; an
    # empty ``sectors`` list means sector-agnostic.
    target_segments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    sectors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    states: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    benefit_value_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    benefit_value_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    benefit_description: Mapped[str] = mapped_column(Text, nullable=False)

    application_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    offline_process: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    application_difficulty: Mapped[ApplicationDifficulty] = mapped_column(
        enum_column(ApplicationDifficulty, "application_difficulty"), nullable=False
    )
    # Realistic effort for a first-time applicant, used for lead-time planning.
    estimated_effort_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Days needed to prepare a submission once documents are in hand.
    drafting_lead_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    # Hash of the upstream source content, used by change detection to tell a
    # substantive amendment from incidental page churn.
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at_column()

    scheme: Mapped[Scheme] = relationship(back_populates="versions")
    authority: Mapped[Authority | None] = relationship()
    criteria: Mapped[list[EligibilityCriterion]] = relationship(
        back_populates="scheme_version", cascade="all, delete-orphan"
    )
    document_requirements: Mapped[list[DocumentRequirement]] = relationship(
        back_populates="scheme_version", cascade="all, delete-orphan"
    )
    windows: Mapped[list[ApplicationWindow]] = relationship(
        back_populates="scheme_version", cascade="all, delete-orphan"
    )
    benefits: Mapped[list[Benefit]] = relationship(
        back_populates="scheme_version", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SchemeVersion {self.name} v{self.version}>"


class EligibilityCriterion(Base, ProvenanceMixin):
    """A single eligibility condition attached to a scheme version.

    ``HARD`` criteria carry a ``machine_readable_rule`` and are decided in code.
    ``SOFT`` criteria carry none and require language judgement; they are
    evaluated by an LLM with an explicit confidence score.

    The pairing is enforced: a hard criterion without a rule is not decidable in
    code and would silently degrade to guesswork.
    """

    __tablename__ = "eligibility_criterion"
    __table_args__ = (
        CheckConstraint(
            "(criterion_type = 'hard' AND machine_readable_rule IS NOT NULL) "
            "OR (criterion_type = 'soft' AND machine_readable_rule IS NULL)",
            name="hard_criteria_require_rule",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_version.id", ondelete="CASCADE"), nullable=False
    )
    criterion_type: Mapped[CriterionType] = mapped_column(
        enum_column(CriterionType, "criterion_type"), nullable=False
    )
    # Plain-language statement of the condition, shown to the user verbatim.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # ``none_as_null`` is required: without it SQLAlchemy stores Python ``None``
    # as the JSON literal ``null``, which is not SQL NULL, and the check
    # constraint above would silently never fire.
    machine_readable_rule: Mapped[dict | None] = mapped_column(
        JSON(none_as_null=True), nullable=True
    )
    # Ordering for display, so the breakdown reads in the order the scheme
    # document states its conditions.
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    scheme_version: Mapped[SchemeVersion] = relationship(back_populates="criteria")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<EligibilityCriterion {self.criterion_type} {self.description[:40]!r}>"


class DocumentRequirement(Base, ProvenanceMixin):
    """A document a scheme version requires, and how long it takes to obtain."""

    __tablename__ = "document_requirement"

    id: Mapped[uuid.UUID] = uuid_pk()
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_version.id", ondelete="CASCADE"), nullable=False
    )
    document_name: Mapped[str] = mapped_column(String(300), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    issuing_authority_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("authority.id", ondelete="SET NULL"), nullable=True
    )
    # Free-text fallback when the issuer is not a modelled authority.
    issuing_authority_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Realistic elapsed days to obtain, which drives lead-time warnings.
    typical_processing_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    how_to_obtain: Mapped[str | None] = mapped_column(Text, nullable=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Rule describing when a conditionally-required document applies.
    conditional_logic: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    scheme_version: Mapped[SchemeVersion] = relationship(back_populates="document_requirements")
    issuing_authority: Mapped[Authority | None] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<DocumentRequirement {self.document_name}>"


class ApplicationWindow(Base, ProvenanceMixin):
    """A period during which a scheme version accepts applications.

    ``open_date`` and ``close_date`` are both nullable because rolling schemes
    have neither, and some windows are announced with a start but no published
    end.
    """

    __tablename__ = "application_window"
    __table_args__ = (
        CheckConstraint(
            "open_date IS NULL OR close_date IS NULL OR close_date >= open_date",
            name="window_dates_ordered",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_version.id", ondelete="CASCADE"), nullable=False
    )
    open_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recurrence: Mapped[Recurrence] = mapped_column(
        enum_column(Recurrence, "recurrence"), nullable=False
    )
    notification_source: Mapped[NotificationSource] = mapped_column(
        enum_column(NotificationSource, "notification_source"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    scheme_version: Mapped[SchemeVersion] = relationship(back_populates="windows")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ApplicationWindow {self.open_date}..{self.close_date}>"


class Benefit(Base, ProvenanceMixin):
    """What a scheme version actually provides on approval."""

    __tablename__ = "benefit"

    id: Mapped[uuid.UUID] = uuid_pk()
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_version.id", ondelete="CASCADE"), nullable=False
    )
    benefit_type: Mapped[BenefitType] = mapped_column(
        enum_column(BenefitType, "benefit_type"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantum_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantum_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conditions_for_disbursement: Mapped[str | None] = mapped_column(Text, nullable=True)

    scheme_version: Mapped[SchemeVersion] = relationship(back_populates="benefits")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Benefit {self.benefit_type}>"
