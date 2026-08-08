"""API and ingest contracts for the scheme knowledge base.

``*In`` models validate data entering the system, whether hand-curated or
machine-extracted. ``*Out`` models are what the API returns.

Two invariants are enforced here rather than left to reviewer discipline:

* every factual claim carries a source URL and a last-verified date;
* a hard criterion carries a machine-readable rule, and a soft criterion does
  not — a hard criterion without a rule cannot be decided in code, and would
  quietly become guesswork.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field, model_validator

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
from bharat_os.rules import validate_rule

# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


class ProvenanceIn(BaseModel):
    """Sourcing required on every claim about a scheme."""

    source_url: HttpUrl
    source_quote: str | None = None
    last_verified_at: datetime
    verified_by_human: bool = False

    @model_validator(mode="after")
    def _reject_future_verification(self) -> ProvenanceIn:
        if self.last_verified_at > datetime.now(UTC):
            raise ValueError("last_verified_at cannot be in the future")
        return self


class ProvenanceOut(BaseModel):
    """Provenance as returned to clients, with staleness computed."""

    model_config = ConfigDict(from_attributes=True)

    source_url: str
    source_quote: str | None
    last_verified_at: datetime
    verified_by_human: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_since_verified(self) -> int:
        reference = self.last_verified_at
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        return (datetime.now(UTC) - reference).days


# --------------------------------------------------------------------------
# Authority
# --------------------------------------------------------------------------


class AuthorityIn(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=300)
    authority_type: AuthorityType
    portal_url: HttpUrl | None = None
    contact: str | None = None
    document_acceptance_method: str | None = None


class AuthorityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    authority_type: AuthorityType
    portal_url: str | None


# --------------------------------------------------------------------------
# Eligibility criteria
# --------------------------------------------------------------------------


class EligibilityCriterionIn(ProvenanceIn):
    criterion_type: CriterionType
    description: str = Field(min_length=1)
    machine_readable_rule: dict | None = None
    display_order: int = 0

    @model_validator(mode="after")
    def _rule_matches_criterion_type(self) -> EligibilityCriterionIn:
        if self.criterion_type is CriterionType.HARD and self.machine_readable_rule is None:
            raise ValueError(
                "a hard criterion requires a machine_readable_rule; without one it cannot "
                "be decided deterministically"
            )
        if self.criterion_type is CriterionType.SOFT and self.machine_readable_rule is not None:
            raise ValueError(
                "a soft criterion must not carry a machine_readable_rule; soft criteria are "
                "resolved by language judgement with an explicit confidence score"
            )
        if self.machine_readable_rule is not None:
            # Validated here so a typo in curated data fails at load time rather
            # than evaluating to "cannot verify" forever in production.
            validate_rule(self.machine_readable_rule)
        return self


class EligibilityCriterionOut(ProvenanceOut):
    id: uuid.UUID
    criterion_type: CriterionType
    description: str
    machine_readable_rule: dict | None
    display_order: int


# --------------------------------------------------------------------------
# Document requirements
# --------------------------------------------------------------------------


class DocumentRequirementIn(ProvenanceIn):
    document_name: str = Field(min_length=1, max_length=300)
    document_type: str = Field(min_length=1, max_length=80)
    issuing_authority_slug: str | None = None
    issuing_authority_name: str | None = None
    typical_processing_days: int | None = Field(default=None, ge=0)
    how_to_obtain: str | None = None
    mandatory: bool = True
    conditional_logic: dict | None = None
    display_order: int = 0


class DocumentRequirementOut(ProvenanceOut):
    id: uuid.UUID
    document_name: str
    document_type: str
    issuing_authority_name: str | None
    typical_processing_days: int | None
    how_to_obtain: str | None
    mandatory: bool
    conditional_logic: dict | None
    display_order: int


# --------------------------------------------------------------------------
# Application windows
# --------------------------------------------------------------------------


class ApplicationWindowIn(ProvenanceIn):
    open_date: datetime | None = None
    close_date: datetime | None = None
    recurrence: Recurrence
    notification_source: NotificationSource
    notes: str | None = None

    @model_validator(mode="after")
    def _dates_ordered(self) -> ApplicationWindowIn:
        if self.open_date and self.close_date and self.close_date < self.open_date:
            raise ValueError("close_date must not precede open_date")
        return self


class ApplicationWindowOut(ProvenanceOut):
    id: uuid.UUID
    open_date: datetime | None
    close_date: datetime | None
    recurrence: Recurrence
    notification_source: NotificationSource
    notes: str | None


# --------------------------------------------------------------------------
# Benefits
# --------------------------------------------------------------------------


class BenefitIn(ProvenanceIn):
    benefit_type: BenefitType
    description: str = Field(min_length=1)
    quantum_min: int | None = Field(default=None, ge=0)
    quantum_max: int | None = Field(default=None, ge=0)
    conditions_for_disbursement: str | None = None

    @model_validator(mode="after")
    def _quantum_ordered(self) -> BenefitIn:
        if (
            self.quantum_min is not None
            and self.quantum_max is not None
            and self.quantum_max < self.quantum_min
        ):
            raise ValueError("quantum_max must not be less than quantum_min")
        return self


class BenefitOut(ProvenanceOut):
    id: uuid.UUID
    benefit_type: BenefitType
    description: str
    quantum_min: int | None
    quantum_max: int | None
    conditions_for_disbursement: str | None


# --------------------------------------------------------------------------
# Schemes
# --------------------------------------------------------------------------


class SchemeVersionIn(BaseModel):
    """A curated or extracted scheme revision, ready to load."""

    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1)
    scheme_type: SchemeType
    status: SchemeStatus = SchemeStatus.ACTIVE
    administering_ministry: str = Field(min_length=1, max_length=300)
    implementing_agency: str | None = None
    authority_slug: str | None = None
    target_segments: list[str] = Field(min_length=1)
    sectors: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    benefit_value_min: int | None = Field(default=None, ge=0)
    benefit_value_max: int | None = Field(default=None, ge=0)
    benefit_description: str = Field(min_length=1)
    application_url: HttpUrl | None = None
    offline_process: bool = False
    application_difficulty: ApplicationDifficulty
    estimated_effort_hours: int | None = Field(default=None, ge=0)
    drafting_lead_days: int = Field(default=7, ge=0)
    effective_from: datetime

    criteria: list[EligibilityCriterionIn] = Field(min_length=1)
    document_requirements: list[DocumentRequirementIn] = Field(default_factory=list)
    windows: list[ApplicationWindowIn] = Field(default_factory=list)
    benefits: list[BenefitIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _benefit_range_ordered(self) -> SchemeVersionIn:
        if (
            self.benefit_value_min is not None
            and self.benefit_value_max is not None
            and self.benefit_value_max < self.benefit_value_min
        ):
            raise ValueError("benefit_value_max must not be less than benefit_value_min")
        return self


class SchemeSummaryOut(BaseModel):
    """Compact scheme representation for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    scheme_id: uuid.UUID
    scheme_version_id: uuid.UUID
    slug: str
    version: int
    name: str
    summary: str
    scheme_type: SchemeType
    status: SchemeStatus
    administering_ministry: str
    target_segments: list[str]
    sectors: list[str]
    states: list[str]
    benefit_value_min: int | None
    benefit_value_max: int | None
    benefit_description: str
    application_difficulty: ApplicationDifficulty
    offline_process: bool


class SchemeDetailOut(SchemeSummaryOut):
    """Full scheme version, including every sourced claim."""

    implementing_agency: str | None
    application_url: str | None
    estimated_effort_hours: int | None
    drafting_lead_days: int
    effective_from: datetime
    authority: AuthorityOut | None
    criteria: list[EligibilityCriterionOut]
    document_requirements: list[DocumentRequirementOut]
    windows: list[ApplicationWindowOut]
    benefits: list[BenefitOut]
