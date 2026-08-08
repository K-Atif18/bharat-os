"""Draft application generation and retrieval."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from bharat_os.dependencies import DbSession, MatchingUser
from bharat_os.models.draft import ApplicationDraft
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.rate_limit import ExpensiveRateLimit
from bharat_os.schemas.drafts import DraftDiffOut, DraftFieldDiffOut, DraftOut, SupportedSchemesOut
from bharat_os.services.drafting import NoFieldMapError, generate_draft, supported_schemes
from bharat_os.services.eligibility import to_domain_profile

router = APIRouter(prefix="/matches", tags=["drafts"])


@router.get("/draftable", response_model=SupportedSchemesOut)
def list_draftable_schemes() -> SupportedSchemesOut:
    return SupportedSchemesOut(slugs=supported_schemes())


@router.post("/{slug}/draft", response_model=DraftOut, status_code=status.HTTP_201_CREATED)
def create_draft(
    slug: str,
    user: MatchingUser,
    db: DbSession,
    _rate_limit: ExpensiveRateLimit = None,
) -> DraftOut:
    """Generate a new draft version for one scheme.

    Every call creates a new version rather than overwriting, so an applicant can
    see what changed between attempts. Nothing here submits anything — see the
    module docstring on :mod:`bharat_os.services.drafting`.
    """
    row = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == slug, SchemeVersion.is_current.is_(True))
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No scheme found for slug {slug!r}"
        )
    _, version = row

    profile = to_domain_profile(user.profile)
    entity_name = user.profile.entity_name if user.profile else None
    try:
        fields = generate_draft(db, version, profile, scheme_slug=slug, entity_name=entity_name)
    except NoFieldMapError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    highest = db.scalar(
        select(ApplicationDraft.version)
        .where(
            ApplicationDraft.user_id == user.id,
            ApplicationDraft.scheme_version_id == version.id,
        )
        .order_by(ApplicationDraft.version.desc())
        .limit(1)
    )
    db.execute(
        ApplicationDraft.__table__.update()
        .where(
            ApplicationDraft.user_id == user.id,
            ApplicationDraft.scheme_version_id == version.id,
        )
        .values(is_current=False)
    )

    draft = ApplicationDraft(
        user_id=user.id,
        scheme_version_id=version.id,
        version=(highest or 0) + 1,
        is_current=True,
        fields=[f.to_dict() for f in fields],
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return DraftOut(
        id=draft.id,
        scheme_version_id=draft.scheme_version_id,
        version=draft.version,
        fields=draft.fields,
        human_required_count=draft.human_required_count,
        created_at=draft.created_at,
    )


@router.get("/{slug}/draft", response_model=DraftOut)
def get_current_draft(slug: str, user: MatchingUser, db: DbSession) -> DraftOut:
    row = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == slug, SchemeVersion.is_current.is_(True))
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No scheme found for slug {slug!r}"
        )
    _, version = row

    draft = db.scalar(
        select(ApplicationDraft).where(
            ApplicationDraft.user_id == user.id,
            ApplicationDraft.scheme_version_id == version.id,
            ApplicationDraft.is_current.is_(True),
        )
    )
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No draft yet. Create one with POST /matches/{slug}/draft.",
        )

    return DraftOut(
        id=draft.id,
        scheme_version_id=draft.scheme_version_id,
        version=draft.version,
        fields=draft.fields,
        human_required_count=draft.human_required_count,
        created_at=draft.created_at,
    )


def _load_owned_draft(draft_id: str, user: MatchingUser, db: DbSession) -> ApplicationDraft:
    draft = db.scalar(
        select(ApplicationDraft).where(
            ApplicationDraft.id == draft_id, ApplicationDraft.user_id == user.id
        )
    )
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such draft.")
    return draft


@router.get("/drafts/{draft_id}/diff/{other_draft_id}", response_model=DraftDiffOut)
def diff_drafts(
    draft_id: str, other_draft_id: str, user: MatchingUser, db: DbSession
) -> DraftDiffOut:
    """Compare two versions of the same applicant's draft, field by field.

    Pure string comparison — no LLM involved. Both drafts must belong to the
    calling user; this never compares across applicants.
    """
    draft_a = _load_owned_draft(draft_id, user, db)
    draft_b = _load_owned_draft(other_draft_id, user, db)

    fields_a = {f["key"]: f for f in draft_a.fields}
    fields_b = {f["key"]: f for f in draft_b.fields}
    all_keys = list(dict.fromkeys([*fields_a.keys(), *fields_b.keys()]))

    fields = []
    for key in all_keys:
        a = fields_a.get(key)
        b = fields_b.get(key)
        value_a = a.get("value") if a else None
        value_b = b.get("value") if b else None
        fields.append(
            DraftFieldDiffOut(
                key=key,
                label=(b or a or {}).get("label", key),
                value_a=value_a,
                value_b=value_b,
                changed=value_a != value_b,
            )
        )

    return DraftDiffOut(
        draft_id_a=draft_a.id,
        draft_id_b=draft_b.id,
        version_a=draft_a.version,
        version_b=draft_b.version,
        fields=fields,
    )
