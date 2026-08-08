"""Scheme data freshness reporting.

Every eligibility criterion carries ``source_verified_at`` (see
``ProvenanceMixin``), but nothing before this endpoint ever surfaced that data
to a client. A user acting on a criterion nobody has re-checked against the
official source in a long time should be able to see that, rather than
implicitly trusting data that may already be wrong.

Staleness is computed per scheme version from its *oldest* verified
criterion: a scheme is only as fresh as its least-recently-checked claim, not
its most-recently-checked one. Showing the best case would hide exactly the
criterion a user most needs to double-check for themselves.

Unauthenticated by design, like ``api/schemes.py``: this reports a property
of the scheme catalogue, not of any user, so there is nothing here to
protect behind a session.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import pydantic
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from bharat_os.config import get_settings
from bharat_os.db import get_db
from bharat_os.models.scheme import Scheme, SchemeVersion

router = APIRouter(prefix="/freshness", tags=["freshness"])

DbSession = Annotated[Session, Depends(get_db)]


class SchemeFreshnessOut(pydantic.BaseModel):
    """Staleness of one scheme's sourced criteria, oldest claim first."""

    scheme_slug: str
    scheme_name: str
    oldest_criterion_verified_at: datetime | None
    is_stale: bool
    days_since_last_verification: int | None
    stale_criterion_count: int
    total_criterion_count: int
    staleness_threshold_days: int


def _build_report(scheme: Scheme, version: SchemeVersion) -> SchemeFreshnessOut:
    threshold_days = get_settings().staleness_threshold_days
    cutoff = datetime.now(UTC) - timedelta(days=threshold_days)

    # SQLite does not round-trip timezone info on DateTime columns, so a value
    # read back from the test database can be naive even though every write
    # path sets it with UTC attached. Normalising here keeps this endpoint
    # correct on both engines, matching the pattern used elsewhere in the
    # codebase (services/deep_dive.py, api/matches.py, api/deadlines.py).
    def _as_aware(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value

    criteria = version.criteria
    verified_dates = [_as_aware(c.last_verified_at) for c in criteria]
    # A scheme version with no criteria at all cannot be scored; treat it as
    # stale rather than silently reporting "fresh" on an empty sample.
    oldest = min(verified_dates) if verified_dates else None
    is_stale = oldest is None or oldest < cutoff
    stale_count = sum(1 for verified_at in verified_dates if verified_at < cutoff)
    days_since = (datetime.now(UTC) - oldest).days if oldest is not None else None

    return SchemeFreshnessOut(
        scheme_slug=scheme.slug,
        scheme_name=version.name,
        oldest_criterion_verified_at=oldest,
        is_stale=is_stale,
        days_since_last_verification=days_since,
        stale_criterion_count=stale_count,
        total_criterion_count=len(criteria),
        staleness_threshold_days=threshold_days,
    )


@router.get("/", response_model=list[SchemeFreshnessOut])
def list_freshness(db: DbSession) -> list[SchemeFreshnessOut]:
    """Staleness report for the current version of every scheme.

    Sorted oldest-verified-first, so the schemes most in need of a human
    recheck surface at the top rather than being buried in an alphabetical
    list.
    """
    stmt = (
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(SchemeVersion.is_current.is_(True))
        .options(selectinload(SchemeVersion.criteria))
        .order_by(Scheme.slug)
    )
    rows = db.execute(stmt).all()

    reports = [_build_report(scheme, version) for scheme, version in rows]
    reports.sort(
        key=lambda r: r.oldest_criterion_verified_at or datetime.min.replace(tzinfo=UTC)
    )
    return reports


@router.get("/{scheme_slug}", response_model=SchemeFreshnessOut)
def get_freshness(scheme_slug: str, db: DbSession) -> SchemeFreshnessOut:
    """Staleness report for one scheme's current version."""
    stmt = (
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == scheme_slug, SchemeVersion.is_current.is_(True))
        .options(selectinload(SchemeVersion.criteria))
    )
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No scheme found for slug {scheme_slug!r}",
        )
    scheme, version = row
    return _build_report(scheme, version)
