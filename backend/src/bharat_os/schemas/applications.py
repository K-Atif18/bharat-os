"""Contracts for applications and outcomes."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from bharat_os.models.enums import ApplicationStatus, OutcomeType


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheme_version_id: uuid.UUID
    status: ApplicationStatus
    external_reference: str | None
    submitted_at: datetime | None
    last_status_update: datetime | None
    created_at: datetime


class ApplicationStatusUpdateIn(BaseModel):
    """A status change the user is making themselves.

    ``external_reference`` is the reference number the government portal gave the
    user after *they* submitted — evidence that a human acted, not something the
    system fabricates.
    """

    status: ApplicationStatus
    external_reference: str | None = Field(default=None, max_length=200)


class OutcomeIn(BaseModel):
    outcome_type: OutcomeType
    decided_at: datetime | None = None
    amount_sanctioned_inr: int | None = Field(default=None, ge=0)
    rejection_reason: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class OutcomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    outcome_type: OutcomeType
    decided_at: datetime | None
    amount_sanctioned_inr: int | None
    rejection_reason: str | None
    notes: str | None
    days_to_decision: int | None
    created_at: datetime


class SchemeOutcomeStatsOut(BaseModel):
    """Aggregate statistics only. Never a per-applicant row."""

    scheme_version_id: str
    total: int
    approved: int
    rejected: int
    approval_rate: float | None
    common_rejection_reasons: list[tuple[str, int]]
