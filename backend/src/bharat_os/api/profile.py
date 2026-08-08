"""The applicant profile.

Every endpoint here requires both authentication and active consent for
``scheme_matching``. Nothing in this module logs a profile field: the request
path deals in whole objects and lets the response model decide what is exposed,
so there is no place a stray f-string can put turnover into a log line.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from bharat_os.dependencies import DbSession, MatchingUser
from bharat_os.models.user import Profile, UserAccount
from bharat_os.schemas.auth import ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])


def _apply(profile: Profile, payload: ProfileIn) -> None:
    profile.entity_name = payload.entity_name
    profile.state = payload.state
    profile.district = payload.district
    profile.sector = payload.sector
    profile.stage = payload.stage
    profile.employee_count = payload.employee_count
    profile.incorporation_date = payload.incorporation_date
    profile.is_woman_led = payload.is_woman_led
    profile.registrations = [r.value for r in payload.registrations]
    profile.annual_turnover_inr = payload.annual_turnover_inr
    profile.social_category = payload.social_category.value if payload.social_category else None


def _load(db: Session, user: UserAccount) -> Profile:
    if user.profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile yet. Create one with PUT /profile.",
        )
    return user.profile


@router.get("", response_model=ProfileOut)
def read_profile(user: MatchingUser, db: DbSession) -> ProfileOut:
    return ProfileOut.model_validate(_load(db, user))


@router.put("", response_model=ProfileOut)
def upsert_profile(payload: ProfileIn, user: MatchingUser, db: DbSession) -> ProfileOut:
    """Create or replace the profile.

    One profile per account in v1. Idempotent, so a client retrying after a
    dropped connection does not create a duplicate.
    """
    profile = user.profile
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)

    _apply(profile, payload)
    db.commit()
    db.refresh(profile)
    return ProfileOut.model_validate(profile)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_profile(user: MatchingUser, db: DbSession) -> None:
    """Delete the profile while keeping the account.

    Separate from account erasure on purpose: a user may want to remove their
    business details without giving up the account.
    """
    profile = _load(db, user)
    db.delete(profile)
    db.commit()
