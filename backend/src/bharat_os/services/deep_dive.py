"""Assembling the deep-dive view.

Pulls together the hard-rule assessment, the soft judgements and the aggregate
report into the shape the deep-dive screen renders. This is where "why did I get
this score" gets an actual answer: every number on the page traces back to a
criterion, a source, and — for soft criteria — a specific prompt and model.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.config import get_settings
from bharat_os.engine import assess_hard_criteria
from bharat_os.engine.profile import ApplicantProfile
from bharat_os.engine.results import CriterionResult
from bharat_os.llm import get_provider
from bharat_os.models.audit import AIJudgement
from bharat_os.models.enums import CriterionType
from bharat_os.models.scheme import EligibilityCriterion, Scheme, SchemeVersion
from bharat_os.schemas.deep_dive import (
    DeepDiveOut,
    DisqualificationOut,
    HardCriterionOut,
    SoftCriterionOut,
)
from bharat_os.services.aggregate import ReportOutcome, aggregate
from bharat_os.services.eligibility import hard_criteria, soft_criteria
from bharat_os.services.soft_criteria import cache_key, judge_all

DISCLAIMER = (
    "This is an advisory assessment, not a determination of eligibility and not a "
    "prediction of approval. Hard criteria are checked deterministically against "
    "the rules on file. Criteria marked as judgement are opinions from a language "
    "model, shown with their reasoning so you can weigh them yourself. Confirm "
    "every criterion against the linked official source before you apply."
)


def _staleness(verified_at: datetime, threshold_days: int) -> tuple[int, bool]:
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    days = (datetime.now(UTC) - verified_at).days
    return days, days > threshold_days


def _hard_out(
    criterion: EligibilityCriterion,
    result: CriterionResult,
    threshold_days: int,
) -> HardCriterionOut:
    days, stale = _staleness(criterion.last_verified_at, threshold_days)
    return HardCriterionOut(
        criterion_id=criterion.id,
        description=criterion.description,
        state=result.state,
        reason=result.reason,
        missing_fields=list(result.missing_fields),
        source_url=criterion.source_url,
        source_quote=criterion.source_quote,
        last_verified_at=criterion.last_verified_at,
        verified_by_human=criterion.verified_by_human,
        days_since_verified=days,
        is_stale=stale,
    )


def build_deep_dive(
    db: Session,
    scheme: Scheme,
    version: SchemeVersion,
    profile: ApplicantProfile,
    *,
    user_id: object | None = None,
) -> DeepDiveOut:
    """Assemble the full breakdown for one scheme against one profile.

    Soft criteria are judged even when the applicant is ruled out on a hard
    criterion. A disqualified applicant still benefits from the full picture — for
    instance, to know whether the rest of the profile would clear if the one
    blocking fact changed.
    """
    settings = get_settings()
    threshold = settings.staleness_threshold_days

    hard_rules = hard_criteria(version)
    hard_assessment = assess_hard_criteria(hard_rules, profile)

    hard_criteria_by_id = {
        str(c.id): c for c in version.criteria if c.criterion_type is CriterionType.HARD
    }

    met = [
        _hard_out(hard_criteria_by_id[key], hard_assessment.results[key], threshold)
        for key in hard_assessment.met
    ]
    unmet = [
        _hard_out(hard_criteria_by_id[key], hard_assessment.results[key], threshold)
        for key in hard_assessment.unmet
    ]
    unverifiable = [
        _hard_out(hard_criteria_by_id[key], hard_assessment.results[key], threshold)
        for key in hard_assessment.unverifiable
    ]
    disqualifications = [
        DisqualificationOut(
            criterion_id=hard_criteria_by_id[key].id,
            description=hard_criteria_by_id[key].description,
            reason=hard_assessment.results[key].reason,
        )
        for key in hard_assessment.unmet
    ]

    soft_judgements = judge_all(db, version, profile, user_id=user_id)

    # Fetch the audit rows for the prompt text shown in the expandable trail. The
    # judgements themselves already carry everything except the exact prompt, which
    # only the persisted record retains.
    audit_by_criterion: dict[str, AIJudgement] = {}
    if soft_judgements:
        provider = get_provider()
        keys = [cache_key(c, profile, provider) for c in soft_criteria(version)]
        rows = db.scalars(select(AIJudgement).where(AIJudgement.cache_key.in_(keys))).all()
        audit_by_criterion = {str(row.criterion_id): row for row in rows}

    soft_criteria_by_id = {str(c.id): c for c in soft_criteria(version)}
    soft_out = []
    for judgement in soft_judgements:
        criterion = soft_criteria_by_id[judgement.criterion_id]
        audit_row = audit_by_criterion.get(judgement.criterion_id)
        days, stale = _staleness(criterion.last_verified_at, threshold)
        soft_out.append(
            SoftCriterionOut(
                criterion_id=judgement.criterion_id,
                description=judgement.description,
                verdict=judgement.verdict,
                confidence=judgement.confidence,
                reasoning=judgement.reasoning,
                evidence_that_would_strengthen=list(judgement.evidence_that_would_strengthen),
                requires_human_review=judgement.requires_human_review,
                audit_prompt=audit_row.prompt if audit_row else None,
                audit_provider=judgement.provider,
                audit_model=judgement.model,
                audit_prompt_version=judgement.prompt_version,
                was_cached=judgement.cached,
                source_url=criterion.source_url,
                source_quote=criterion.source_quote,
                last_verified_at=criterion.last_verified_at,
                verified_by_human=criterion.verified_by_human,
                days_since_verified=days,
                is_stale=stale,
            )
        )

    report = aggregate(hard_assessment, soft_judgements)
    has_stale_data = any(c.is_stale for c in (*met, *unmet, *unverifiable, *soft_out))

    return DeepDiveOut(
        scheme_id=scheme.id,
        scheme_version_id=version.id,
        slug=scheme.slug,
        name=version.name,
        scheme_type=version.scheme_type.value,
        outcome=report.outcome,
        confidence=report.confidence,
        disqualifications=disqualifications if report.outcome is ReportOutcome.RULED_OUT else [],
        met=met,
        unmet=unmet,
        unverifiable=unverifiable,
        soft=soft_out,
        missing_fields=list(report.missing_fields),
        evidence_requested=list(report.evidence_requested),
        requires_human_review=report.requires_human_review,
        has_stale_data=has_stale_data,
        disclaimer=DISCLAIMER,
    )
