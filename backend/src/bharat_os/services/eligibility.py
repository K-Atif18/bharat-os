"""Adapting persisted data to the pure engine.

The engine deliberately knows nothing about the database. This module is the seam
between the two: it converts ORM rows into the engine's plain dataclasses and
converts results back. Keeping the conversion here rather than inside the engine
is what lets the engine stay independently testable.
"""

from __future__ import annotations

from datetime import date

from bharat_os.engine import (
    ApplicantProfile,
    HardCriterion,
    HardRuleAssessment,
    assess_hard_criteria,
)
from bharat_os.models.enums import CriterionType
from bharat_os.models.scheme import EligibilityCriterion, SchemeVersion
from bharat_os.models.user import Profile


def to_domain_profile(profile: Profile | None, *, as_of: date | None = None) -> ApplicantProfile:
    """Convert a stored profile into the engine's view of an applicant.

    Sensitive fields are decrypted by the ORM on read, so they arrive here as
    plain values. They stay in memory and are never logged.
    """
    if profile is None:
        # No profile at all: every criterion will come back unverifiable, which is
        # the honest answer rather than a default that implies knowledge.
        return ApplicantProfile(registrations_declared=False, as_of=as_of)

    return ApplicantProfile(
        state=profile.state,
        district=profile.district,
        sector=profile.sector,
        stage=profile.stage.value if profile.stage else None,
        employee_count=profile.employee_count,
        annual_turnover_inr=profile.annual_turnover_inr,
        social_category=profile.social_category,
        is_woman_led=profile.is_woman_led,
        incorporation_date=profile.incorporation_date,
        registrations=frozenset(profile.registrations or ()),
        # A saved profile means the user answered the registrations question, so
        # an empty list is a considered "none" rather than an unanswered field.
        registrations_declared=True,
        as_of=as_of,
    )


def hard_criteria(version: SchemeVersion) -> list[HardCriterion]:
    """Extract the machine-decidable criteria from a scheme version."""
    return [
        HardCriterion(
            key=str(criterion.id),
            description=criterion.description,
            rule=criterion.machine_readable_rule,
        )
        for criterion in sorted(version.criteria, key=lambda c: c.display_order)
        if criterion.criterion_type is CriterionType.HARD
        and criterion.machine_readable_rule is not None
    ]


def soft_criteria(version: SchemeVersion) -> list[EligibilityCriterion]:
    """The criteria requiring judgement, in display order."""
    return [
        criterion
        for criterion in sorted(version.criteria, key=lambda c: c.display_order)
        if criterion.criterion_type is CriterionType.SOFT
    ]


def assess_hard_rules(
    version: SchemeVersion,
    profile: Profile | None,
    *,
    as_of: date | None = None,
) -> HardRuleAssessment:
    """Run the deterministic assessment for one scheme version."""
    return assess_hard_criteria(hard_criteria(version), to_domain_profile(profile, as_of=as_of))
