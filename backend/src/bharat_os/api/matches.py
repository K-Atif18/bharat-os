"""The ranked feed.

Requires authentication and active consent for scheme matching, since matching is
processing of personal data.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bharat_os.dependencies import DbSession, MatchingUser
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.rate_limit import ExpensiveRateLimit
from bharat_os.schemas.deep_dive import DeepDiveOut
from bharat_os.schemas.matches import MatchFeedOut, MatchOut, ScoreBreakdown
from bharat_os.services.deep_dive import build_deep_dive
from bharat_os.services.eligibility import assess_hard_rules, soft_criteria, to_domain_profile
from bharat_os.services.ranking import RankedMatch, RankingInput, rank

router = APIRouter(prefix="/matches", tags=["matches"])

DISCLAIMER = (
    "These are advisory matches based on the profile you provided and the scheme "
    "terms as last verified. They are not a determination of eligibility and not a "
    "prediction of approval. Confirm each criterion against the official source "
    "before you apply."
)

MIN_CONFIDENCE = Annotated[
    float,
    Query(ge=0, le=1, description="Exclude matches below this confidence."),
]


def _next_deadline(version: SchemeVersion) -> datetime | None:
    """The soonest future close date, ignoring windows that have already closed."""
    now = datetime.now(UTC)
    upcoming = []
    for window in version.windows:
        close = window.close_date
        if close is None:
            continue
        if close.tzinfo is None:
            close = close.replace(tzinfo=UTC)
        if close > now:
            upcoming.append(close)
    return min(upcoming) if upcoming else None


def _max_days_since_verified(version: SchemeVersion) -> int:
    now = datetime.now(UTC)
    ages = []
    for criterion in version.criteria:
        verified = criterion.last_verified_at
        if verified.tzinfo is None:
            verified = verified.replace(tzinfo=UTC)
        ages.append((now - verified).days)
    return max(ages) if ages else 0


def _to_out(scheme: Scheme, version: SchemeVersion, match: RankedMatch) -> MatchOut:
    return MatchOut(
        scheme_id=scheme.id,
        scheme_version_id=version.id,
        slug=scheme.slug,
        name=version.name,
        summary=version.summary,
        scheme_type=version.scheme_type,
        administering_ministry=version.administering_ministry,
        outcome=match.outcome,
        confidence=match.confidence,
        score=match.score,
        score_breakdown=ScoreBreakdown(
            confidence_factor=match.confidence_factor,
            benefit_factor=match.benefit_factor,
            difficulty_factor=match.difficulty_factor,
        ),
        criteria_met=match.criteria_met,
        criteria_unmet=match.criteria_unmet,
        criteria_unverifiable=match.criteria_unverifiable,
        soft_criteria_count=match.soft_criteria_count,
        missing_fields=list(match.missing_fields),
        benefit_description=version.benefit_description,
        benefit_value_max=version.benefit_value_max,
        application_difficulty=version.application_difficulty,
        application_url=version.application_url,
        estimated_effort_hours=version.estimated_effort_hours,
        next_deadline=_next_deadline(version),
        max_days_since_verified=_max_days_since_verified(version),
    )


@router.get("", response_model=MatchFeedOut)
def list_matches(
    user: MatchingUser,
    db: DbSession,
    min_confidence: MIN_CONFIDENCE = 0.0,
) -> MatchFeedOut:
    """Rank every active scheme against the caller's profile.

    Assessment is deterministic: hard criteria only, evaluated in code. Criteria
    requiring judgement are counted and reported as outstanding rather than
    guessed at.
    """
    if user.profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a profile first with PUT /profile — matching needs one.",
        )

    rows = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(SchemeVersion.is_current.is_(True))
        .options(
            selectinload(SchemeVersion.criteria),
            selectinload(SchemeVersion.windows),
        )
        .order_by(Scheme.slug)
    ).all()

    by_slug: dict[str, tuple[Scheme, SchemeVersion]] = {}
    inputs: list[RankingInput] = []

    for scheme, version in rows:
        # Paused and closed schemes are omitted entirely. Suggesting an
        # application to something not currently accepting them wastes the
        # applicant's time, which is the resource this product exists to protect.
        if version.status.value != "active":
            continue

        by_slug[scheme.slug] = (scheme, version)
        assessment = assess_hard_rules(version, user.profile)
        inputs.append(
            RankingInput(
                slug=scheme.slug,
                assessment=assessment,
                difficulty=version.application_difficulty,
                benefit_value_max=version.benefit_value_max,
                soft_criteria_count=len(soft_criteria(version)),
            )
        )

    matches, ruled_out = rank(inputs)

    # Suggest the profile fields that would resolve the most unknowns, most
    # valuable first, so the user's next action has the largest effect.
    field_frequency: Counter[str] = Counter()
    for match in matches:
        field_frequency.update(match.missing_fields)

    return MatchFeedOut(
        matches=[_to_out(*by_slug[m.slug], m) for m in matches if m.confidence >= min_confidence],
        ruled_out=[_to_out(*by_slug[m.slug], m) for m in ruled_out],
        schemes_assessed=len(inputs),
        suggested_profile_additions=[name for name, _ in field_frequency.most_common()],
        disclaimer=DISCLAIMER,
    )


@router.get("/{slug}", response_model=MatchOut)
def get_match(slug: str, user: MatchingUser, db: DbSession) -> MatchOut:
    """The assessment for one scheme against the caller's profile."""
    if user.profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a profile first with PUT /profile — matching needs one.",
        )

    row = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == slug, SchemeVersion.is_current.is_(True))
        .options(
            selectinload(SchemeVersion.criteria),
            selectinload(SchemeVersion.windows),
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No scheme found for slug {slug!r}",
        )

    scheme, version = row
    assessment = assess_hard_rules(version, user.profile)
    scored, ruled_out = rank(
        [
            RankingInput(
                slug=scheme.slug,
                assessment=assessment,
                difficulty=version.application_difficulty,
                benefit_value_max=version.benefit_value_max,
                soft_criteria_count=len(soft_criteria(version)),
            )
        ]
    )
    match = (scored + ruled_out)[0]
    return _to_out(scheme, version, match)


@router.get("/{slug}/deep-dive", response_model=DeepDiveOut)
def get_deep_dive(
    slug: str,
    user: MatchingUser,
    db: DbSession,
    _rate_limit: ExpensiveRateLimit = None,
) -> DeepDiveOut:
    """The full, sourced, auditable breakdown for one scheme.

    Every criterion here traces back to a source URL and a verification date; every
    soft judgement traces back to the exact prompt and model that produced it. This
    is the answer to "how do I know this isn't hallucinating".
    """
    if user.profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a profile first with PUT /profile — matching needs one.",
        )

    row = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == slug, SchemeVersion.is_current.is_(True))
        .options(selectinload(SchemeVersion.criteria))
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No scheme found for slug {slug!r}",
        )

    scheme, version = row
    profile = to_domain_profile(user.profile)
    return build_deep_dive(db, scheme, version, profile, user_id=user.id)
