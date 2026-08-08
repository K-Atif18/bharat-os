"""Contracts for the verification queue."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from bharat_os.models.enums import CrawlSourceType, ReviewStatus


class PendingRevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    source_url: str
    source_type: CrawlSourceType
    scheme_slug: str | None
    status: ReviewStatus
    extracted_content: dict
    extraction_confidence: float | None
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ReviewDecisionIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class RejectDecisionIn(BaseModel):
    #: Required, not optional — see services.review_queue.reject.
    note: str = Field(min_length=1, max_length=2000)


class AnnotateIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)
