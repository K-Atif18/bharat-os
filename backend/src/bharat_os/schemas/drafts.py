"""Contracts for application drafts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from bharat_os.models.enums import DraftFieldSource


class DraftFieldOut(BaseModel):
    key: str
    label: str
    source: DraftFieldSource
    value: str | None
    instruction: str | None = None
    reason: str | None = None


class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheme_version_id: uuid.UUID
    version: int
    fields: list[DraftFieldOut]
    human_required_count: int
    created_at: datetime

    #: Restated at the point of use, not only in the disclaimer footer — this is
    #: the screen where a user might be tempted to think a draft is final.
    review_notice: str = (
        "This is a draft, not a submission. Review every field, complete the "
        "ones marked for you, and submit it yourself through the official "
        "channel. Nothing here files anything on your behalf."
    )


class SupportedSchemesOut(BaseModel):
    slugs: list[str]
