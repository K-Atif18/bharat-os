"""Contracts for the ranked feed."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from bharat_os.models.enums import ApplicationDifficulty, SchemeType
from bharat_os.services.ranking import MatchOutcome


class ScoreBreakdown(BaseModel):
    """The factors behind a score.

    Exposed rather than hidden. A ranking a user cannot interrogate is a ranking
    they have no reason to trust, and "why is this first?" is a fair question.
    """

    confidence_factor: float = Field(ge=0, le=1)
    benefit_factor: float = Field(ge=0, le=1)
    difficulty_factor: float = Field(ge=0, le=1)


class MatchOut(BaseModel):
    """One scheme as it appears in the ranked feed."""

    model_config = ConfigDict(from_attributes=True)

    scheme_id: uuid.UUID
    scheme_version_id: uuid.UUID
    slug: str
    name: str
    summary: str
    scheme_type: SchemeType
    administering_ministry: str

    outcome: MatchOutcome
    #: Share of hard criteria confirmed met. Never presented as a probability of
    #: approval, because it is not one.
    confidence: float = Field(ge=0, le=1)
    score: float
    score_breakdown: ScoreBreakdown

    criteria_met: int
    criteria_unmet: int
    criteria_unverifiable: int
    #: Criteria that need judgement rather than computation. Reported as
    #: outstanding rather than guessed at — soft-criteria reasoning happens in
    #: the deep-dive view, not in the ranked feed.
    soft_criteria_count: int
    #: Profile fields that would resolve unverifiable criteria if supplied.
    missing_fields: list[str]

    benefit_description: str
    benefit_value_max: int | None
    application_difficulty: ApplicationDifficulty
    application_url: str | None
    estimated_effort_hours: int | None
    next_deadline: datetime | None
    #: Days since the oldest criterion in this scheme was verified, so a stale
    #: entry can be flagged in the feed rather than only in the detail view.
    max_days_since_verified: int


class MatchFeedOut(BaseModel):
    """The ranked feed, with ruled-out schemes kept separate."""

    #: Schemes worth pursuing, best first.
    matches: list[MatchOut]
    #: Schemes with a definitively unmet hard requirement, and the reason.
    ruled_out: list[MatchOut]
    #: Total schemes assessed, so the feed can say what it looked at.
    schemes_assessed: int
    #: Fields that, if added to the profile, would resolve the most unknowns.
    suggested_profile_additions: list[str]
    #: Reminder that this is advisory, returned with the data rather than only
    #: rendered in the UI, so API consumers cannot drop it.
    disclaimer: str
