"""Contracts for the deep-dive eligibility view.

This is the screen that has to survive the question "how do I know this isn't
hallucinating?" Every criterion carries its source, its verification date, and —
for soft criteria — the exact prompt and model that produced the judgement.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from bharat_os.models.enums import EvaluationState, SoftVerdict
from bharat_os.services.aggregate import ReportOutcome


class HardCriterionOut(BaseModel):
    """One deterministic criterion, with its verdict and provenance."""

    model_config = ConfigDict(from_attributes=True)

    criterion_id: uuid.UUID
    description: str
    state: EvaluationState
    reason: str
    missing_fields: list[str]

    source_url: str
    source_quote: str | None
    last_verified_at: datetime
    verified_by_human: bool
    days_since_verified: int
    is_stale: bool


class SoftCriterionOut(BaseModel):
    """One judgement-based criterion, with the audit trail visible."""

    criterion_id: str
    description: str
    verdict: SoftVerdict
    confidence: float
    reasoning: str
    evidence_that_would_strengthen: list[str]
    requires_human_review: bool

    #: The actual prompt sent and the model that answered — expandable in the UI,
    #: not hidden behind the verdict.
    audit_prompt: str | None
    audit_provider: str
    audit_model: str
    audit_prompt_version: str
    was_cached: bool

    source_url: str
    source_quote: str | None
    last_verified_at: datetime
    verified_by_human: bool
    days_since_verified: int
    is_stale: bool


class DisqualificationOut(BaseModel):
    """Why an applicant cannot have this scheme, shown plainly rather than scored."""

    criterion_id: uuid.UUID
    description: str
    reason: str


class DeepDiveOut(BaseModel):
    """The full eligibility breakdown for one scheme against one profile."""

    scheme_id: uuid.UUID
    scheme_version_id: uuid.UUID
    slug: str
    name: str
    scheme_type: str

    outcome: ReportOutcome
    #: ``None`` only when ruled out — see :class:`EligibilityReport`.
    confidence: float | None = Field(default=None, ge=0, le=1)

    #: Populated only when ruled out.
    disqualifications: list[DisqualificationOut]

    met: list[HardCriterionOut]
    unmet: list[HardCriterionOut]
    unverifiable: list[HardCriterionOut]
    soft: list[SoftCriterionOut]

    missing_fields: list[str]
    evidence_requested: list[str]
    requires_human_review: bool

    #: True if any criterion on this scheme was last verified beyond the
    #: staleness threshold. Surfaced at the top so it cannot be missed by only
    #: reading individual criteria.
    has_stale_data: bool
    disclaimer: str
