"""The application lifecycle.

A small, explicit state machine rather than free-form status strings, so an
invalid transition is a rejected function call, not a row that silently makes no
sense. The transition table is the single place that encodes "what can happen
next", which matters here specifically because status changes past
``READY_FOR_REVIEW`` are always user-initiated — the table has no path that
reaches ``SUBMITTED`` from anywhere the system controls on its own.
"""

from __future__ import annotations

from bharat_os.models.enums import ApplicationStatus

#: Legal transitions. A status not present as a key has no legal transitions out
#: of it (a terminal state).
_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.DRAFT: frozenset(
        {ApplicationStatus.READY_FOR_REVIEW, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.READY_FOR_REVIEW: frozenset(
        {ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED, ApplicationStatus.WITHDRAWN}
    ),
    # SUBMITTED is only ever reached from READY_FOR_REVIEW, and only by an action
    # the user takes after they have submitted through the official channel
    # themselves — this transition records that fact, it does not cause it.
    ApplicationStatus.SUBMITTED: frozenset(
        {ApplicationStatus.UNDER_REVIEW, ApplicationStatus.APPROVED, ApplicationStatus.REJECTED}
    ),
    ApplicationStatus.UNDER_REVIEW: frozenset(
        {ApplicationStatus.APPROVED, ApplicationStatus.REJECTED}
    ),
    ApplicationStatus.APPROVED: frozenset(),
    ApplicationStatus.REJECTED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a status change is not permitted from the current state."""


def can_transition(current: ApplicationStatus, target: ApplicationStatus) -> bool:
    return target in _TRANSITIONS.get(current, frozenset())


def transition(current: ApplicationStatus, target: ApplicationStatus) -> ApplicationStatus:
    """Validate and return the new status, or raise.

    A pure check — callers apply the result to their own row. Kept this way so
    the rule "what transitions are legal" has exactly one implementation, used by
    both the API layer and anything (e.g. a future admin tool) that changes status.
    """
    if not can_transition(current, target):
        raise InvalidTransitionError(
            f"Cannot move an application from {current.value!r} to {target.value!r}."
        )
    return target


def is_terminal(status: ApplicationStatus) -> bool:
    return not _TRANSITIONS.get(status)
