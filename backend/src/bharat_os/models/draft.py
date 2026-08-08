"""Application drafts.

A draft is text for the applicant to review, edit and submit themselves. Every
field is tagged with where its value came from, and any field the system could not
fill is explicit about why, so the applicant knows exactly what still needs their
attention before this is submission-ready.

Nothing in this model, or in any code that populates it, has a status the
applicant did not set. There is no ``submitted_by_system`` anywhere in this
codebase, and that is intentional at every layer, not just this one.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bharat_os.models.base import Base, created_at_column, uuid_pk


class ApplicationDraft(Base):
    """One version of a draft application for one scheme.

    Versioned like the scheme corpus: editing a draft creates a new version rather
    than overwriting, so an applicant can see what changed and revert.
    """

    __tablename__ = "application_draft"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "scheme_version_id",
            "version",
            name="uq_application_draft_user_scheme_version",
        ),
        Index("ix_application_draft_current", "user_id", "scheme_version_id", "is_current"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheme_version.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(nullable=False, default=True)

    #: List of field objects: key, label, source, value, and — for
    #: HUMAN_REQUIRED fields — the reason. Stored as JSON because the field set
    #: varies per scheme and is defined by the field map, not by this schema.
    fields: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = created_at_column()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ApplicationDraft scheme_version={self.scheme_version_id} v{self.version}>"

    @property
    def human_required_count(self) -> int:
        return sum(1 for f in self.fields if f.get("source") == "human_required")
