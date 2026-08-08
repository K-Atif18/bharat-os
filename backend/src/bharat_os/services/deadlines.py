"""Computing whether there is enough time left, and when to be warned.

Pure with respect to its inputs. Takes a window's close date, a scheme's drafting
lead time, and the slowest document still outstanding, and answers the question
nobody's portal answers: not "when does this close" but "can I actually make it,
and if not, which single blocker is the reason".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

#: Days before close at which a reminder fires. Matches the plan's 30/14/7/1.
NOTIFICATION_OFFSETS_DAYS: tuple[int, ...] = (30, 14, 7, 1)


class ReachabilityStatus(StrEnum):
    #: Plenty of time for both documents and drafting.
    COMFORTABLE = "comfortable"
    #: Time exists but is tight; every day now matters.
    TIGHT = "tight"
    #: The slowest outstanding step will not finish before the window closes.
    UNREACHABLE = "unreachable"
    #: The window has already closed.
    CLOSED = "closed"
    #: No close date is published — a rolling or unannounced window.
    NO_DEADLINE = "no_deadline"


@dataclass(frozen=True)
class LeadTimeAssessment:
    """Whether an applicant can realistically make a deadline, and why."""

    status: ReachabilityStatus
    close_date: date | None
    days_remaining: int | None
    #: Days needed: the slower of (document acquisition, drafting lead time).
    days_required: int | None
    #: The single longest-lead document still outstanding, if any — the thing
    #: that is actually the bottleneck, not a generic "gather your documents".
    bottleneck_document: str | None = None
    bottleneck_days: int | None = None

    @property
    def margin_days(self) -> int | None:
        """Slack remaining. Negative means the deadline is not reachable."""
        if self.days_remaining is None or self.days_required is None:
            return None
        return self.days_remaining - self.days_required


#: Below this many days of slack, a reachable deadline is still flagged as tight.
TIGHT_MARGIN_DAYS = 5


def assess_reachability(
    *,
    close_date: datetime | date | None,
    drafting_lead_days: int,
    outstanding_documents: list[tuple[str, int | None]],
    as_of: date | None = None,
) -> LeadTimeAssessment:
    """Compute whether a deadline is reachable.

    ``outstanding_documents`` is a list of (document name, typical processing
    days) for documents the applicant does not yet have. Only the single slowest
    one matters for reachability, because documents can usually be pursued in
    parallel — the deadline is set by whichever one takes longest, not by their sum.
    """
    today = as_of or date.today()

    if close_date is None:
        return LeadTimeAssessment(
            status=ReachabilityStatus.NO_DEADLINE,
            close_date=None,
            days_remaining=None,
            days_required=None,
        )

    close = close_date.date() if isinstance(close_date, datetime) else close_date
    days_remaining = (close - today).days

    if days_remaining < 0:
        return LeadTimeAssessment(
            status=ReachabilityStatus.CLOSED,
            close_date=close,
            days_remaining=days_remaining,
            days_required=None,
        )

    bottleneck_name: str | None = None
    bottleneck_days = 0
    for name, processing_days in outstanding_documents:
        effective = processing_days or 0
        if effective > bottleneck_days:
            bottleneck_days = effective
            bottleneck_name = name

    # Document acquisition and drafting are not fully parallel — a realistic
    # bound is the document wait, then the drafting time, since the draft's
    # supporting-document fields cannot be finished before the document exists.
    days_required = bottleneck_days + drafting_lead_days

    if days_required > days_remaining:
        status = ReachabilityStatus.UNREACHABLE
    elif days_remaining - days_required <= TIGHT_MARGIN_DAYS:
        status = ReachabilityStatus.TIGHT
    else:
        status = ReachabilityStatus.COMFORTABLE

    return LeadTimeAssessment(
        status=status,
        close_date=close,
        days_remaining=days_remaining,
        days_required=days_required,
        bottleneck_document=bottleneck_name,
        bottleneck_days=bottleneck_days or None,
    )


def next_recurrence(
    close_date: date,
    recurrence: str,
) -> date | None:
    """The next occurrence of a closed recurring window.

    Returns ``None`` for one-time or rolling windows, which by definition do not
    recur on a schedule.
    """
    if recurrence == "annual":
        return close_date.replace(year=close_date.year + 1)
    if recurrence == "quarterly":
        return close_date + timedelta(days=91)
    return None


def notification_dates(close_date: date) -> dict[int, date]:
    """The calendar dates on which a reminder should fire for this deadline."""
    return {offset: close_date - timedelta(days=offset) for offset in NOTIFICATION_OFFSETS_DAYS}
