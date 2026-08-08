"""Shared FastAPI dependencies.

:data:`CurrentUser` is the single gate for user data. Every endpoint that reads
or writes anything belonging to a user must depend on it — there is no
"optionally authenticated" variant, deliberately, because that is how an
unauthenticated path to user data gets introduced by accident.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from bharat_os.db import get_db
from bharat_os.models.auth import UserSession
from bharat_os.models.enums import ConsentPurpose
from bharat_os.models.user import UserAccount
from bharat_os.security import hash_session_token

DbSession = Annotated[Session, Depends(get_db)]

#: Name of the session cookie.
SESSION_COOKIE = "bharat_os_session"

UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required.",
)


def get_current_user(
    db: DbSession,
    bharat_os_session: Annotated[str | None, Cookie()] = None,
) -> UserAccount:
    """Resolve the session cookie to an active user, or reject the request."""
    if not bharat_os_session:
        raise UNAUTHENTICATED

    session_row = db.scalar(
        select(UserSession)
        .where(UserSession.token_hash == hash_session_token(bharat_os_session))
        .options(
            selectinload(UserSession.user).selectinload(UserAccount.consents),
            selectinload(UserSession.user).selectinload(UserAccount.profile),
        )
    )
    if session_row is None or session_row.revoked_at is not None:
        raise UNAUTHENTICATED

    expires_at = session_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise UNAUTHENTICATED

    if not session_row.user.is_active:
        raise UNAUTHENTICATED

    return session_row.user


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


def require_consent(purpose: ConsentPurpose):
    """Build a dependency requiring active consent for ``purpose``.

    Processing personal data for a purpose the user has not agreed to is the
    failure this guards against, so it is enforced in the request path rather
    than left to each handler to remember.
    """

    def dependency(user: CurrentUser) -> UserAccount:
        if not user.has_consent(purpose):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires consent for '{purpose.value}'. "
                    "Grant it via POST /me/consents."
                ),
            )
        return user

    return dependency


#: A user who has consented to their profile being processed for scheme matching.
MatchingUser = Annotated[UserAccount, Depends(require_consent(ConsentPurpose.SCHEME_MATCHING))]


#: Purpose-specific gates for optional data processing. Keeping these aliases
#: named makes a route's privacy requirements visible in its signature.
DocumentStorageUser = Annotated[
    UserAccount,
    Depends(require_consent(ConsentPurpose.DOCUMENT_STORAGE)),
]
OutcomeAnalyticsUser = Annotated[
    UserAccount,
    Depends(require_consent(ConsentPurpose.OUTCOME_ANALYTICS)),
]


def require_reviewer(user: CurrentUser) -> UserAccount:
    """A user permitted to act on the verification queue.

    Not consent-gated — this is not processing of the reviewer's own data, it is a
    role check. Reviewer status is granted directly in the database, not through
    self-service, because this is the gate between machine-extracted content and
    the live scheme corpus.
    """
    if not user.is_reviewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires reviewer access.",
        )
    return user


ReviewerUser = Annotated[UserAccount, Depends(require_reviewer)]
