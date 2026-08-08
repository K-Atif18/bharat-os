"""Contracts for the deadline calendar."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from bharat_os.services.deadlines import ReachabilityStatus


class DeadlineOut(BaseModel):
    """One scheme's deadline, with a reachability verdict rather than just a date."""

    scheme_id: uuid.UUID
    scheme_version_id: uuid.UUID
    slug: str
    name: str

    status: ReachabilityStatus
    close_date: date | None
    days_remaining: int | None
    days_required: int | None
    margin_days: int | None
    bottleneck_document: str | None
    bottleneck_days: int | None


class DeadlineCalendarOut(BaseModel):
    deadlines: list[DeadlineOut]
    #: Schemes whose deadline cannot realistically be met, surfaced separately so
    #: effort is not wasted chasing something already out of reach.
    unreachable_count: int
