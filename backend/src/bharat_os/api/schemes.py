"""Public scheme catalogue.

These endpoints expose curated public information about government schemes and
touch no user data, so they are unauthenticated by design. Every endpoint that
reads or writes user data requires authentication (see api/auth.py).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from bharat_os.db import get_db
from bharat_os.models.enums import Segment
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.schemas.scheme import (
    AuthorityOut,
    SchemeDetailOut,
    SchemeSummaryOut,
)

router = APIRouter(prefix="/schemes", tags=["schemes"])

DbSession = Annotated[Session, Depends(get_db)]
SegmentFilter = Annotated[Segment | None, Query(description="Filter by targeted segment")]
StateFilter = Annotated[
    str | None,
    Query(description="Filter to schemes available in this state, including all-India schemes"),
]
VersionSelector = Annotated[
    int | None,
    Query(ge=1, description="Specific revision to retrieve. Defaults to the current one."),
]


def _summary_fields(scheme: Scheme, version: SchemeVersion) -> dict:
    """Flatten the scheme/version pair into the shape clients consume."""
    return {
        "scheme_id": scheme.id,
        "scheme_version_id": version.id,
        "slug": scheme.slug,
        "version": version.version,
        "name": version.name,
        "summary": version.summary,
        "scheme_type": version.scheme_type,
        "status": version.status,
        "administering_ministry": version.administering_ministry,
        "target_segments": version.target_segments,
        "sectors": version.sectors,
        "states": version.states,
        "benefit_value_min": version.benefit_value_min,
        "benefit_value_max": version.benefit_value_max,
        "benefit_description": version.benefit_description,
        "application_difficulty": version.application_difficulty,
        "offline_process": version.offline_process,
    }


def to_summary(scheme: Scheme, version: SchemeVersion) -> SchemeSummaryOut:
    return SchemeSummaryOut(**_summary_fields(scheme, version))


def to_detail(scheme: Scheme, version: SchemeVersion) -> SchemeDetailOut:
    return SchemeDetailOut(
        **_summary_fields(scheme, version),
        implementing_agency=version.implementing_agency,
        application_url=version.application_url,
        estimated_effort_hours=version.estimated_effort_hours,
        drafting_lead_days=version.drafting_lead_days,
        effective_from=version.effective_from,
        authority=(AuthorityOut.model_validate(version.authority) if version.authority else None),
        criteria=sorted(version.criteria, key=lambda c: c.display_order),  # type: ignore[arg-type]
        document_requirements=sorted(  # type: ignore[arg-type]
            version.document_requirements, key=lambda d: d.display_order
        ),
        windows=list(version.windows),  # type: ignore[arg-type]
        benefits=list(version.benefits),  # type: ignore[arg-type]
    )


@router.get("", response_model=list[SchemeSummaryOut])
def list_schemes(
    db: DbSession,
    segment: SegmentFilter = None,
    state: StateFilter = None,
) -> list[SchemeSummaryOut]:
    """List the current version of every scheme, newest curation first."""
    stmt = (
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(SchemeVersion.is_current.is_(True))
        .options(selectinload(SchemeVersion.authority))
        .order_by(Scheme.slug)
    )
    rows = db.execute(stmt).all()

    results: list[SchemeSummaryOut] = []
    for scheme, version in rows:
        # Filtering happens in Python because target_segments and states are JSON
        # arrays; a JSON containment query would not be portable across SQLite
        # and Postgres. The catalogue is small enough that this is not a concern,
        # and it will move into the ranking query when it stops being true.
        if segment is not None and segment.value not in version.target_segments:
            continue
        if state is not None and version.states and state not in version.states:
            continue
        results.append(to_summary(scheme, version))
    return results


@router.get("/{slug}", response_model=SchemeDetailOut)
def get_scheme(
    slug: str,
    db: DbSession,
    version: VersionSelector = None,
) -> SchemeDetailOut:
    """Retrieve one scheme revision with all of its sourced claims.

    Historical revisions remain retrievable so an assessment made months ago can
    still be explained against the criteria that were in force at the time.
    """
    stmt = (
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == slug)
        .options(
            selectinload(SchemeVersion.authority),
            selectinload(SchemeVersion.criteria),
            selectinload(SchemeVersion.document_requirements),
            selectinload(SchemeVersion.windows),
            selectinload(SchemeVersion.benefits),
        )
    )
    stmt = (
        stmt.where(SchemeVersion.version == version)
        if version is not None
        else stmt.where(SchemeVersion.is_current.is_(True))
    )

    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No scheme found for slug {slug!r}"
            + (f" at version {version}" if version is not None else ""),
        )
    scheme, scheme_version = row
    return to_detail(scheme, scheme_version)
