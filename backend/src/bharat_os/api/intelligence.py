"""Aggregate outcome intelligence per scheme.

This is the "Government Process Graph" in its earliest form: what approval
rates, rejection patterns and timelines actually look like for a scheme, as
opposed to what the official guidelines claim. The aggregation functions
already existed in ``services/outcomes.py``; this module is the API surface
that was missing, not new measurement logic.

All data here is aggregated over multiple applications. No single applicant's
row is ever returned — see ``services/outcomes.py``'s own docstrings for why
that boundary exists.

There is no ``stated_days_to_decision`` field in this response. The scheme
data model (``SchemeVersion``) has no field representing a scheme's
advertised decision timeline — ``drafting_lead_days`` is a different concept
entirely (how long an *applicant* needs to prepare documents, not how long
the *government* takes to decide). Inventing a plausible-looking "stated
timeline" number to diff against would be fabricating a claim this system has
no source for, which is the exact failure mode the product's sourcing
discipline exists to prevent. If a real advertised timeline is added to the
scheme data later (with a source_url, like everything else in this system),
the gap calculation becomes real and can be added then.
"""

from __future__ import annotations

from typing import Annotated

import pydantic
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.db import get_db
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.services.outcomes import (
    approval_rate_by_turnover_band,
    average_days_to_decision,
    scheme_outcome_stats,
)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

DbSession = Annotated[Session, Depends(get_db)]


class RejectionReasonOut(pydantic.BaseModel):
    reason: str
    count: int


class SchemeIntelligenceOut(pydantic.BaseModel):
    scheme_slug: str
    scheme_name: str
    total_outcomes_recorded: int
    approval_rate: float | None
    average_days_to_decision: float | None
    approval_rate_by_turnover_band: dict[str, float | None]
    common_rejection_reasons: list[RejectionReasonOut]
    has_real_outcomes: bool
    data_note: str


#: Marker prefix on Outcome.notes for rows inserted by the synthetic seed
#: script, not by a real user reporting a real result. Chosen over adding a
#: new is_synthetic column: a schema migration is real production risk to
#: take on for something a documented text convention expresses just as
#: reliably, and this stays trivially removable once real outcomes exist.
SYNTHETIC_MARKER = "[SYNTHETIC]"


@router.get("/{scheme_slug}", response_model=SchemeIntelligenceOut)
def get_scheme_intelligence(scheme_slug: str, db: DbSession) -> SchemeIntelligenceOut:
    row = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == scheme_slug, SchemeVersion.is_current.is_(True))
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No scheme found for slug {scheme_slug!r}",
        )
    scheme, version = row

    stats = scheme_outcome_stats(db, version.id)
    avg_days = average_days_to_decision(db, version.id)
    by_band = approval_rate_by_turnover_band(db, version.id)

    has_real_outcomes = _has_real_outcomes(db, version.id)

    if stats.total == 0:
        note = "No outcomes recorded yet for this scheme."
    elif has_real_outcomes:
        note = f"Based on {stats.total} recorded outcome(s)."
    else:
        note = (
            f"Based on {stats.total} synthetic outcome(s), not real application "
            "results. This demonstrates the aggregation working; it does not "
            "describe this scheme's actual approval rate. Replaced automatically "
            "by real data as real outcomes are reported."
        )

    return SchemeIntelligenceOut(
        scheme_slug=scheme.slug,
        scheme_name=version.name,
        total_outcomes_recorded=stats.total,
        approval_rate=round(stats.approval_rate, 4) if stats.approval_rate is not None else None,
        average_days_to_decision=round(avg_days, 1) if avg_days is not None else None,
        approval_rate_by_turnover_band={
            band: (round(rate, 4) if rate is not None else None)
            for band, rate in by_band.items()
        },
        common_rejection_reasons=[
            RejectionReasonOut(reason=reason, count=count)
            for reason, count in stats.common_rejection_reasons
        ],
        has_real_outcomes=has_real_outcomes,
        data_note=note,
    )


def _has_real_outcomes(db: Session, scheme_version_id: object) -> bool:
    """Whether at least one outcome for this scheme is real, not synthetic.

    An outcome counts as real unless its notes carry the synthetic seed
    marker — see :data:`SYNTHETIC_MARKER`.
    """
    from bharat_os.models.application import Outcome

    rows = db.execute(
        select(Outcome.notes)
        .join(Outcome.application)
        .where(Outcome.application.has(scheme_version_id=scheme_version_id))
    ).all()
    return any(notes is None or not notes.startswith(SYNTHETIC_MARKER) for (notes,) in rows)
