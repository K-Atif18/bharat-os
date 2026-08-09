"""Authentication, consent and erasure.

The erasure endpoint here is the one that carries legal weight. Under the DPDP
Act a user can require their personal data to be deleted, and this implements
that literally: the account, profile, sessions, consent records and AI judgement
prompts are removed, and applications are unlinked from the user. What survives
is de-identified outcome data — which state, which sector, which turnover band,
approved or rejected and why — because none of that identifies a person and all
makes the system better at advising the next applicant.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from bharat_os.config import get_settings
from bharat_os.dependencies import SESSION_COOKIE, CurrentUser, DbSession
from bharat_os.models.application import Application, Outcome
from bharat_os.models.audit import AIJudgement
from bharat_os.models.auth import ConsentGrant, UserSession
from bharat_os.models.document import UserDocument
from bharat_os.models.enums import ConsentPurpose
from bharat_os.models.notification import DeadlineNotification
from bharat_os.models.user import Profile, UserAccount
from bharat_os.rate_limit import AuthRateLimit
from bharat_os.schemas.auth import (
    CURRENT_POLICY_VERSION,
    AccountOut,
    ConsentOut,
    ConsentUpdateIn,
    ErasureOut,
    LoginIn,
    RegisterIn,
)
from bharat_os.security import (
    SESSION_TTL_DAYS,
    WeakPasswordError,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)

router = APIRouter(tags=["auth"])

#: Deliberately identical for unknown email and wrong password, so the endpoint
#: cannot be used to discover which addresses have accounts.
INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Email or password is incorrect.",
)


def _issue_session(db: DbSession, user: UserAccount, response: Response) -> None:
    """Create a session and set its cookie."""
    token = generate_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_TTL_DAYS),
        )
    )
    db.commit()

    settings = get_settings()
    # In the hosted deployment the frontend (e.g. Vercel) and the API (e.g.
    # Railway) live on different domains, so every authenticated call is
    # cross-site. SameSite=Lax would stop the browser from sending the session
    # cookie on those calls, so production uses SameSite=None — which browsers
    # only accept together with Secure, hence the HTTPS pairing. Local
    # development stays SameSite=Lax over plain HTTP, where None is not allowed.
    is_production = settings.environment == "production"
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        samesite="none" if is_production else "lax",
        secure=is_production,
        path="/",
    )


def _account_out(user: UserAccount) -> AccountOut:
    return AccountOut(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        consents=[ConsentOut.model_validate(c) for c in user.consents],
        has_profile=user.profile is not None,
    )


@router.post("/auth/register", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterIn, response: Response, db: DbSession, _rate_limit: AuthRateLimit = None
) -> AccountOut:
    """Create an account, record consent, and start a session."""
    try:
        password_hash = hash_password(payload.password)
    except WeakPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    user = UserAccount(email=payload.email.lower(), password_hash=password_hash)
    now = datetime.now(UTC)
    for purpose in dict.fromkeys(payload.consents):
        user.consents.append(
            ConsentGrant(
                purpose=purpose,
                granted_at=now,
                policy_version=CURRENT_POLICY_VERSION,
            )
        )

    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        ) from exc

    db.refresh(user)
    _issue_session(db, user, response)
    return _account_out(user)


@router.post("/auth/login", response_model=AccountOut)
def login(
    payload: LoginIn, response: Response, db: DbSession, _rate_limit: AuthRateLimit = None
) -> AccountOut:
    user = db.scalar(select(UserAccount).where(UserAccount.email == payload.email.lower()))
    # verify_password is called even when no user exists, so the response time
    # does not reveal whether the address is registered.
    if not verify_password(payload.password, user.password_hash if user else None):
        raise INVALID_CREDENTIALS
    if user is None or not user.is_active:
        raise INVALID_CREDENTIALS

    _issue_session(db, user, response)
    return _account_out(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(user: CurrentUser, response: Response, db: DbSession) -> None:
    """Revoke every session for the user, not just the current one."""
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=AccountOut)
def read_me(user: CurrentUser) -> AccountOut:
    return _account_out(user)


@router.get("/me/consents", response_model=list[ConsentOut])
def list_consents(user: CurrentUser) -> list[ConsentOut]:
    return [ConsentOut.model_validate(c) for c in user.consents]


@router.post("/me/consents", response_model=list[ConsentOut])
def update_consent(payload: ConsentUpdateIn, user: CurrentUser, db: DbSession) -> list[ConsentOut]:
    """Grant or withdraw consent for one purpose.

    Withdrawing ``scheme_matching`` is allowed and deletes the profile, because
    the profile exists only to be matched. Silently keeping it after consent is
    withdrawn would make the consent meaningless.
    """
    now = datetime.now(UTC)
    existing = next((c for c in user.consents if c.purpose == payload.purpose), None)

    if existing is None:
        existing = ConsentGrant(
            user_id=user.id,
            purpose=payload.purpose,
            policy_version=CURRENT_POLICY_VERSION,
        )
        db.add(existing)
        user.consents.append(existing)

    if payload.granted:
        existing.granted_at = now
        existing.withdrawn_at = None
        existing.policy_version = CURRENT_POLICY_VERSION
    else:
        existing.withdrawn_at = now
        if payload.purpose is ConsentPurpose.SCHEME_MATCHING and user.profile is not None:
            db.delete(user.profile)
        elif payload.purpose is ConsentPurpose.DOCUMENT_STORAGE:
            db.execute(delete(UserDocument).where(UserDocument.user_id == user.id))
        elif payload.purpose is ConsentPurpose.OUTCOME_ANALYTICS:
            application_ids = select(Application.id).where(Application.user_id == user.id)
            db.execute(delete(Outcome).where(Outcome.application_id.in_(application_ids)))
        elif payload.purpose is ConsentPurpose.NOTIFICATIONS:
            db.execute(
                delete(DeadlineNotification).where(DeadlineNotification.user_id == user.id)
            )

    db.commit()
    db.refresh(user)
    return [ConsentOut.model_validate(c) for c in user.consents]


@router.delete("/me", response_model=ErasureOut)
def erase_account(user: CurrentUser, response: Response, db: DbSession) -> ErasureOut:
    """Delete the account and all personal data associated with it.

    Outcome rows survive in de-identified form. They carry state, sector and a
    coarse turnover band, never an exact figure and never a link to a person, so
    they remain useful for improving recommendations without being personal data.
    """
    user_id = user.id

    application_ids = list(
        db.scalars(select(Application.id).where(Application.user_id == user_id)).all()
    )
    outcomes_retained = 0
    if application_ids:
        outcomes_retained = (
            db.scalar(
                select(func.count())
                .select_from(Outcome)
                .where(Outcome.application_id.in_(application_ids))
            )
            or 0
        )

    profile_existed = user.profile is not None

    sessions_revoked = len(
        list(db.scalars(select(UserSession.id).where(UserSession.user_id == user_id)).all())
    )
    consents_deleted = len(
        list(db.scalars(select(ConsentGrant.id).where(ConsentGrant.user_id == user_id)).all())
    )
    ai_judgements_deleted = len(
        list(db.scalars(select(AIJudgement.id).where(AIJudgement.user_id == user_id)).all())
    )

    # Sever the link to the person before deleting them. The FK is ON DELETE SET
    # NULL, but doing it explicitly makes the intent legible and the count exact.
    applications_unlinked = (
        db.execute(
            update(Application).where(Application.user_id == user_id).values(user_id=None)
        ).rowcount
        or 0
    )

    if profile_existed:
        db.execute(delete(Profile).where(Profile.user_id == user_id))
    db.execute(delete(AIJudgement).where(AIJudgement.user_id == user_id))
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    db.execute(delete(ConsentGrant).where(ConsentGrant.user_id == user_id))
    db.execute(delete(UserAccount).where(UserAccount.id == user_id))
    db.commit()

    response.delete_cookie(SESSION_COOKIE, path="/")

    return ErasureOut(
        account_deleted=True,
        profile_deleted=profile_existed,
        sessions_revoked=sessions_revoked,
        consents_deleted=consents_deleted,
        ai_judgements_deleted=ai_judgements_deleted,
        applications_unlinked=applications_unlinked,
        outcomes_retained_anonymised=outcomes_retained,
        note=(
            "Your account, profile, sessions, consent records and AI judgement "
            "prompts have been deleted. Application outcome records are retained "
            "without any link to you and without your exact turnover, as "
            "de-identified data used to improve eligibility assessments."
        ),
    )
