"""The deadline calendar: not just dates, but whether they are reachable."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bharat_os.dependencies import DbSession, DocumentStorageUser, MatchingUser
from bharat_os.models.document import UserDocument
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.schemas.deadlines import DeadlineCalendarOut, DeadlineOut
from bharat_os.services.deadlines import (
    NOTIFICATION_OFFSETS_DAYS,
    ReachabilityStatus,
    assess_reachability,
)
from bharat_os.services.documents import DocumentStatus, match_documents
from bharat_os.services.eligibility import assess_hard_rules, to_domain_profile

router = APIRouter(prefix="/deadlines", tags=["deadlines"])


def _next_close(version: SchemeVersion) -> datetime | None:
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


def _build_deadline_calendar(user: MatchingUser, db: DbSession) -> DeadlineCalendarOut:
    rows = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(SchemeVersion.is_current.is_(True), SchemeVersion.status == "active")
        .options(
            selectinload(SchemeVersion.criteria),
            selectinload(SchemeVersion.windows),
            selectinload(SchemeVersion.document_requirements),
        )
    ).all()

    vault = list(db.scalars(select(UserDocument).where(UserDocument.user_id == user.id)).all())
    domain_profile = to_domain_profile(user.profile)

    deadlines: list[DeadlineOut] = []
    for scheme, version in rows:
        assessment = assess_hard_rules(version, user.profile)
        if assessment.has_disqualifier:
            continue

        close = _next_close(version)
        gaps = match_documents(version.document_requirements, vault, profile_resolve=domain_profile)
        outstanding = [
            (gap.document_name, gap.typical_processing_days)
            for gap in gaps
            if gap.status in {DocumentStatus.NEED, DocumentStatus.EXPIRED} and gap.mandatory
        ]
        reachability = assess_reachability(
            close_date=close,
            drafting_lead_days=version.drafting_lead_days,
            outstanding_documents=outstanding,
        )

        deadlines.append(
            DeadlineOut(
                scheme_id=scheme.id,
                scheme_version_id=version.id,
                slug=scheme.slug,
                name=version.name,
                status=reachability.status,
                close_date=reachability.close_date,
                days_remaining=reachability.days_remaining,
                days_required=reachability.days_required,
                margin_days=reachability.margin_days,
                bottleneck_document=reachability.bottleneck_document,
                bottleneck_days=reachability.bottleneck_days,
            )
        )

    deadlines.sort(
        key=lambda item: item.days_remaining if item.days_remaining is not None else 10**9
    )
    return DeadlineCalendarOut(
        deadlines=deadlines,
        unreachable_count=sum(
            1 for item in deadlines if item.status is ReachabilityStatus.UNREACHABLE
        ),
    )


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _render_ics(calendar: DeadlineCalendarOut, generated_at: datetime | None = None) -> str:
    """Render dated opportunities as an RFC 5545-compatible calendar."""
    stamp = (generated_at or datetime.now(UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bharat OS//Reachable Scheme Deadlines//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Bharat OS scheme deadlines",
    ]

    for item in calendar.deadlines:
        if item.close_date is None:
            continue
        description_parts = [f"Reachability: {item.status.value.replace('_', ' ')}"]
        if item.margin_days is not None:
            description_parts.append(f"Planning margin: {item.margin_days} days")
        if item.bottleneck_document:
            description_parts.append(f"Bottleneck: {item.bottleneck_document}")

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:scheme-{item.scheme_version_id}@bharat-os",
                f"DTSTAMP:{stamp}",
                f"DTSTART;VALUE=DATE:{item.close_date.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{(item.close_date + timedelta(days=1)).strftime('%Y%m%d')}",
                f"SUMMARY:{_ics_escape(item.name)} application deadline",
                f"DESCRIPTION:{_ics_escape('; '.join(description_parts))}",
                f"CATEGORIES:{item.status.value.upper()}",
            ]
        )
        for offset in NOTIFICATION_OFFSETS_DAYS:
            lines.extend(
                [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"TRIGGER:-P{offset}D",
                    f"DESCRIPTION:{_ics_escape(item.name)} deadline in {offset} days",
                    "END:VALARM",
                ]
            )
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


@router.get("", response_model=DeadlineCalendarOut)
def get_deadline_calendar(
    user: MatchingUser,
    db: DbSession,
    _storage_consent: DocumentStorageUser = None,
) -> DeadlineCalendarOut:
    """Return every non-ruled-out scheme with a deadline reachability verdict."""
    return _build_deadline_calendar(user, db)


@router.get("/calendar.ics", response_class=Response)
def export_deadline_calendar(
    user: MatchingUser,
    db: DbSession,
    _storage_consent: DocumentStorageUser = None,
) -> Response:
    """Download the caller's reachable deadline plan for any calendar application."""
    calendar = _build_deadline_calendar(user, db)
    return Response(
        content=_render_ics(calendar),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": 'attachment; filename="bharat-os-deadlines.ics"',
        },
    )
