"""Contracts for the document vault and gap analysis."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bharat_os.models.enums import DocumentType
from bharat_os.services.documents import DocumentStatus


class UserDocumentIn(BaseModel):
    document_type: DocumentType
    label: str | None = Field(default=None, max_length=300)
    issuing_authority_name: str | None = Field(default=None, max_length=300)
    issue_date: date | None = None
    expiry_date: date | None = None

    @field_validator("expiry_date")
    @classmethod
    def _expiry_after_issue(cls, value: date | None, info) -> date | None:
        issue = info.data.get("issue_date")
        if value and issue and value < issue:
            raise ValueError("expiry_date cannot be before issue_date")
        return value


class UserDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: DocumentType
    label: str | None
    issuing_authority_name: str | None
    issue_date: date | None
    expiry_date: date | None
    is_expired: bool
    created_at: datetime


class DocumentGapOut(BaseModel):
    requirement_id: uuid.UUID
    document_name: str
    document_type: str
    mandatory: bool
    status: DocumentStatus
    issuing_authority: str | None
    typical_processing_days: int | None
    how_to_obtain: str | None
    expired_on: date | None


class DocumentChecklistOut(BaseModel):
    """The full document picture for one scheme."""

    slug: str
    documents: list[DocumentGapOut]
    have_count: int
    need_count: int
    optional_missing_count: int
    expired_count: int
    #: Vault documents that this scheme does not require. Not a problem — shown
    #: so the vault view can say "not needed here" instead of going quiet.
    unused_vault_documents: list[UserDocumentOut]
