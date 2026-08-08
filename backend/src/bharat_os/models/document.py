"""The user's document vault.

A document row records that the user *has* a document, not the file bytes
themselves in v1 — storage of the actual scanned files is a production
concern (object storage, virus scanning) and is deliberately out of scope here.
What matters for gap analysis is: which document type, issued when, expiring
when, and by whom.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bharat_os.models.base import Base, created_at_column, enum_column, uuid_pk
from bharat_os.models.enums import DocumentType


class UserDocument(Base):
    """A document the user has declared they hold."""

    __tablename__ = "user_document"
    __table_args__ = (
        CheckConstraint(
            "expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date",
            name="expiry_after_issue",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )

    document_type: Mapped[DocumentType] = mapped_column(
        enum_column(DocumentType, "vault_document_type"), nullable=False
    )
    #: Free-text label, useful when document_type is UNKNOWN or ambiguous.
    label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    issuing_authority_name: Mapped[str | None] = mapped_column(String(300), nullable=True)

    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    #: Whether the user has confirmed this document is current. Distinguishes "I
    #: uploaded this once" from "I have re-confirmed I still hold this", the same
    #: distinction the scheme corpus draws with verified_by_human.
    confirmed_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = created_at_column()

    user: Mapped[UserAccount] = relationship()  # noqa: F821

    @property
    def is_expired(self) -> bool:
        return self.expiry_date is not None and self.expiry_date < date.today()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<UserDocument {self.document_type} expires={self.expiry_date}>"
