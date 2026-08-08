"""Turning outcomes into the de-identified asset the long-term thesis rests on.

Two responsibilities:

**Banding.** Exact turnover is personal data and is never written into an
``Outcome`` row. It is converted to a coarse band first, here, so the
de-identification is enforced at the point of capture rather than trusted to
happen later.

**Aggregate queries.** Rejection reasons, grouped by scheme and band, are the
Government Process Graph in its earliest form: which strategies succeed at which
schemes. Every query in this module returns aggregates over multiple applications,
never a single applicant's row, which is what keeps this analysis compatible with
having erased the applicants who contributed to it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bharat_os.models.application import Outcome
from bharat_os.models.enums import OutcomeType

#: Bands wide enough that no individual band identifies a specific applicant from
#: turnover alone, narrow enough to be analytically useful.
TURNOVER_BANDS: list[tuple[int | None, int | None, str]] = [
    (None, 1_000_000, "under-10L"),
    (1_000_000, 10_000_000, "10L-1Cr"),
    (10_000_000, 50_000_000, "1Cr-5Cr"),
    (50_000_000, 1_000_000_000, "5Cr-100Cr"),
    (1_000_000_000, None, "100Cr+"),
]


def turnover_band(annual_turnover_inr: int | None) -> str | None:
    """Map an exact turnover to its band, or ``None`` if not supplied.

    Called once, at the point an :class:`Outcome` is created. The exact figure
    must never reach that row — this function is the boundary.
    """
    if annual_turnover_inr is None:
        return None
    for lower, upper, label in TURNOVER_BANDS:
        if (lower is None or annual_turnover_inr >= lower) and (
            upper is None or annual_turnover_inr < upper
        ):
            return label
    return TURNOVER_BANDS[-1][2]


@dataclass(frozen=True)
class SchemeOutcomeStats:
    """Aggregate success statistics for one scheme."""

    scheme_version_id: str
    total: int
    approved: int
    rejected: int
    #: Most common rejection reasons, most frequent first. This is the data that
    #: cannot be scraped from anywhere: what actually gets applications rejected,
    #: as opposed to what the guidelines say is required.
    common_rejection_reasons: list[tuple[str, int]]

    @property
    def approval_rate(self) -> float | None:
        decided = self.approved + self.rejected
        return (self.approved / decided) if decided else None


def scheme_outcome_stats(db: Session, scheme_version_id: object) -> SchemeOutcomeStats:
    """Aggregate outcomes for one scheme version. Never returns a per-user row."""
    rows = db.execute(
        select(Outcome.outcome_type, Outcome.rejection_reason)
        .join(Outcome.application)
        .where(Outcome.application.has(scheme_version_id=scheme_version_id))
    ).all()

    approved = sum(
        1 for t, _ in rows if t in {OutcomeType.APPROVED, OutcomeType.PARTIALLY_APPROVED}
    )
    rejected = sum(1 for t, _ in rows if t is OutcomeType.REJECTED)

    reasons = Counter(reason for _, reason in rows if reason)

    return SchemeOutcomeStats(
        scheme_version_id=str(scheme_version_id),
        total=len(rows),
        approved=approved,
        rejected=rejected,
        common_rejection_reasons=reasons.most_common(5),
    )


def approval_rate_by_turnover_band(
    db: Session, scheme_version_id: object
) -> dict[str, float | None]:
    """Approval rate segmented by turnover band, for one scheme.

    Answers a question a government portal never answers: does this scheme
    actually favour a particular size of business in practice, regardless of what
    the eligibility criteria state.
    """
    rows = db.execute(
        select(Outcome.applicant_turnover_band, Outcome.outcome_type)
        .join(Outcome.application)
        .where(Outcome.application.has(scheme_version_id=scheme_version_id))
    ).all()

    by_band: dict[str, list[OutcomeType]] = {}
    for band, outcome_type in rows:
        by_band.setdefault(band or "unknown", []).append(outcome_type)

    result: dict[str, float | None] = {}
    for band, outcomes in by_band.items():
        decided = [o for o in outcomes if o in {OutcomeType.APPROVED, OutcomeType.REJECTED}]
        approved = sum(1 for o in decided if o is OutcomeType.APPROVED)
        result[band] = (approved / len(decided)) if decided else None
    return result


def average_days_to_decision(db: Session, scheme_version_id: object) -> float | None:
    """Mean elapsed days from submission to decision.

    The gap between this number and a scheme's advertised timeline is itself
    valuable information that exists nowhere else.
    """
    value = db.scalar(
        select(func.avg(Outcome.days_to_decision))
        .join(Outcome.application)
        .where(
            Outcome.application.has(scheme_version_id=scheme_version_id),
            Outcome.days_to_decision.is_not(None),
        )
    )
    return float(value) if value is not None else None
