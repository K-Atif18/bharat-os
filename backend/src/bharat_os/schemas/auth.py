"""Contracts for authentication, consent and profiles."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from bharat_os.models.enums import (
    ConsentPurpose,
    EntityStage,
    RegistrationType,
    SocialCategory,
)

#: Version of the privacy notice users are currently agreeing to. Bump this when
#: the notice materially changes, so old consents are distinguishable from new.
CURRENT_POLICY_VERSION = "2026-07-1"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    #: Purposes being consented to at sign-up. SCHEME_MATCHING is required for
    #: the product to function; the rest are genuinely optional.
    consents: list[ConsentPurpose] = Field(default_factory=list)

    @field_validator("consents")
    @classmethod
    def _matching_consent_required(cls, value: list[ConsentPurpose]) -> list[ConsentPurpose]:
        if ConsentPurpose.SCHEME_MATCHING not in value:
            raise ValueError(
                "Consent to 'scheme_matching' is required, because matching your "
                "profile against schemes is the service itself."
            )
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=256)


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purpose: ConsentPurpose
    granted_at: datetime | None
    withdrawn_at: datetime | None
    policy_version: str
    is_active: bool


class ConsentUpdateIn(BaseModel):
    purpose: ConsentPurpose
    granted: bool


class AccountOut(BaseModel):
    """The authenticated user's own account. Never exposes another user's data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime
    consents: list[ConsentOut]
    has_profile: bool


class ProfileIn(BaseModel):
    """Applicant profile.

    Only fields that some criterion in the knowledge base actually reads are
    collected. Data minimisation is a legal obligation under the DPDP Act and
    also a design constraint: an unused field is pure liability.
    """

    entity_name: str = Field(min_length=1, max_length=300)
    state: str = Field(min_length=1, max_length=80)
    district: str | None = Field(default=None, max_length=120)
    sector: str = Field(min_length=1, max_length=120)
    stage: EntityStage
    employee_count: int | None = Field(default=None, ge=0, le=1000000)
    incorporation_date: date | None = None
    is_woman_led: bool | None = None
    registrations: list[RegistrationType] = Field(default_factory=list)

    # --- Sensitive personal data. Optional, and the reason is shown in the UI. ---
    #: Exact annual turnover in rupees. Encrypted at rest.
    annual_turnover_inr: int | None = Field(default=None, ge=0)
    #: Social category, needed only for schemes reserving benefits by category.
    social_category: SocialCategory | None = None

    @field_validator("incorporation_date")
    @classmethod
    def _not_in_the_future(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("incorporation_date cannot be in the future")
        return value


class ProfileOut(BaseModel):
    """A profile as returned to its owner.

    Sensitive fields are included because the owner is entitled to see their own
    data, but they are never logged and never returned to anyone else.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_name: str
    state: str
    district: str | None
    sector: str
    stage: EntityStage
    employee_count: int | None
    incorporation_date: date | None
    is_woman_led: bool | None
    registrations: list[str]
    annual_turnover_inr: int | None
    social_category: str | None
    created_at: datetime
    updated_at: datetime


class ErasureOut(BaseModel):
    """Confirmation of what a deletion actually removed.

    Reporting the counts matters: "your data is deleted" is a claim the user has
    no way to check, and a vague confirmation is how erasure quietly fails.
    """

    account_deleted: bool
    profile_deleted: bool
    sessions_revoked: int
    consents_deleted: int
    ai_judgements_deleted: int
    applications_unlinked: int
    outcomes_retained_anonymised: int
    note: str
