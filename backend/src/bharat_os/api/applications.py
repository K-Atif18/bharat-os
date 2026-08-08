"""Application tracking and outcome capture.

The pipeline is user-driven end to end. Every status change here is a record of
something the user told us happened, not an action this system took. The
transition table in :mod:`bharat_os.services.application_lifecycle` is what makes
that a checked property rather than a convention.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from bharat_os.dependencies import DbSession, MatchingUser, OutcomeAnalyticsUser
from bharat_os.models.application import Application, Outcome
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.schemas.applications import (
    ApplicationOut,
    ApplicationStatusUpdateIn,
    OutcomeIn,
    OutcomeOut,
    SchemeOutcomeStatsOut,
)
from bharat_os.services.application_lifecycle import InvalidTransitionError, transition
from bharat_os.services.outcomes import scheme_outcome_stats, turnover_band

router = APIRouter(tags=["applications"])


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(user: MatchingUser, db: DbSession) -> list[ApplicationOut]:
    rows = db.scalars(
        select(Application).where(Application.user_id == user.id).order_by(Application.created_at)
    ).all()
    return [ApplicationOut.model_validate(a) for a in rows]


@router.post(
    "/matches/{slug}/applications",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def start_application(slug: str, user: MatchingUser, db: DbSession) -> ApplicationOut:
    """Start tracking an application. Created in DRAFT; nothing is submitted."""
    row = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == slug, SchemeVersion.is_current.is_(True))
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No scheme found for slug {slug!r}"
        )
    _, version = row

    application = Application(user_id=user.id, scheme_version_id=version.id)
    db.add(application)
    db.commit()
    db.refresh(application)
    return ApplicationOut.model_validate(application)


def _load_application(db: DbSession, user, application_id: str) -> Application:
    application = db.scalar(
        select(Application).where(Application.id == application_id, Application.user_id == user.id)
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such application.")
    return application


@router.patch("/applications/{application_id}", response_model=ApplicationOut)
def update_application_status(
    application_id: str,
    payload: ApplicationStatusUpdateIn,
    user: MatchingUser,
    db: DbSession,
) -> ApplicationOut:
    """Record a status change the user is telling us about.

    Moving to SUBMITTED means the user has told us they filed it themselves
    through the official channel; the system does not and cannot cause this
    transition on its own initiative.
    """
    application = _load_application(db, user, application_id)

    try:
        new_status = transition(application.status, payload.status)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    application.status = new_status
    application.last_status_update = datetime.now(UTC)
    if new_status.value == "submitted":
        application.submitted_at = datetime.now(UTC)
    if payload.external_reference:
        application.external_reference = payload.external_reference

    db.commit()
    db.refresh(application)
    return ApplicationOut.model_validate(application)


@router.post(
    "/applications/{application_id}/outcome",
    response_model=OutcomeOut,
    status_code=status.HTTP_201_CREATED,
)
def record_outcome(
    application_id: str,
    payload: OutcomeIn,
    user: MatchingUser,
    db: DbSession,
    _analytics_consent: OutcomeAnalyticsUser = None,
) -> OutcomeOut:
    """Record what happened. This is the data asset the long-term thesis rests on.

    Exact turnover never reaches this row — it is banded at the point of capture,
    here, so de-identification is enforced rather than merely intended.
    """
    application = _load_application(db, user, application_id)
    if application.outcome is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An outcome is already recorded for this application.",
        )

    days_to_decision = None
    if application.submitted_at and payload.decided_at:
        submitted = application.submitted_at
        decided = payload.decided_at
        if submitted.tzinfo is None:
            submitted = submitted.replace(tzinfo=UTC)
        if decided.tzinfo is None:
            decided = decided.replace(tzinfo=UTC)
        days_to_decision = (decided - submitted).days

    outcome = Outcome(
        application_id=application.id,
        outcome_type=payload.outcome_type,
        decided_at=payload.decided_at,
        amount_sanctioned_inr=payload.amount_sanctioned_inr,
        rejection_reason=payload.rejection_reason,
        notes=payload.notes,
        days_to_decision=days_to_decision,
        applicant_state=user.profile.state if user.profile else None,
        applicant_sector=user.profile.sector if user.profile else None,
        applicant_turnover_band=(
            turnover_band(user.profile.annual_turnover_inr) if user.profile else None
        ),
    )
    db.add(outcome)

    from bharat_os.models.enums import ApplicationStatus

    if payload.outcome_type.value in {"approved", "partially_approved"}:
        application.status = transition(application.status, ApplicationStatus.APPROVED)
    elif payload.outcome_type.value == "rejected":
        application.status = transition(application.status, ApplicationStatus.REJECTED)

    db.commit()
    db.refresh(outcome)
    return OutcomeOut.model_validate(outcome)


@router.get("/schemes/{slug}/outcome-stats", response_model=SchemeOutcomeStatsOut)
def get_scheme_outcome_stats(slug: str, user: MatchingUser, db: DbSession) -> SchemeOutcomeStatsOut:
    """Aggregate outcome statistics. Never a per-applicant row.

    Available to any signed-in user, since the aggregate itself contains nothing
    that identifies a contributor — that is the entire point of banding and
    de-identifying at capture time.
    """
    row = db.execute(
        select(SchemeVersion.id)
        .join(Scheme, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == slug, SchemeVersion.is_current.is_(True))
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No scheme found for slug {slug!r}"
        )

    stats = scheme_outcome_stats(db, row[0])
    return SchemeOutcomeStatsOut(
        scheme_version_id=stats.scheme_version_id,
        total=stats.total,
        approved=stats.approved,
        rejected=stats.rejected,
        approval_rate=stats.approval_rate,
        common_rejection_reasons=stats.common_rejection_reasons,
    )
