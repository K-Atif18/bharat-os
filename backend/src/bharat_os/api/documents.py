"""The document vault and per-scheme checklists."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bharat_os.dependencies import DbSession, DocumentStorageUser, MatchingUser
from bharat_os.models.document import UserDocument
from bharat_os.models.scheme import DocumentRequirement, Scheme, SchemeVersion
from bharat_os.schemas.documents import (
    DocumentChecklistOut,
    DocumentGapOut,
    UserDocumentIn,
    UserDocumentOut,
)
from bharat_os.services.documents import (
    DocumentStatus,
    match_documents,
    unrecognised_vault_documents,
)
from bharat_os.services.eligibility import to_domain_profile

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[UserDocumentOut])
def list_documents(
    user: MatchingUser,
    db: DbSession,
    _storage_consent: DocumentStorageUser = None,
) -> list[UserDocumentOut]:
    rows = db.scalars(
        select(UserDocument)
        .where(UserDocument.user_id == user.id)
        .order_by(UserDocument.created_at)
    ).all()
    return [UserDocumentOut.model_validate(d) for d in rows]


@router.post("/documents", response_model=UserDocumentOut, status_code=status.HTTP_201_CREATED)
def add_document(
    payload: UserDocumentIn,
    user: MatchingUser,
    db: DbSession,
    _storage_consent: DocumentStorageUser = None,
) -> UserDocumentOut:
    document = UserDocument(
        user_id=user.id,
        document_type=payload.document_type,
        label=payload.label,
        issuing_authority_name=payload.issuing_authority_name,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return UserDocumentOut.model_validate(document)


@router.delete(
    "/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_document(
    document_id: str,
    user: MatchingUser,
    db: DbSession,
    _storage_consent: DocumentStorageUser = None,
) -> None:
    document = db.scalar(
        select(UserDocument).where(UserDocument.id == document_id, UserDocument.user_id == user.id)
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such document.")
    db.delete(document)
    db.commit()


@router.get("/matches/{slug}/documents", response_model=DocumentChecklistOut)
def get_document_checklist(
    slug: str,
    user: MatchingUser,
    db: DbSession,
    _storage_consent: DocumentStorageUser = None,
) -> DocumentChecklistOut:
    """Have / need / expired / not-applicable for one scheme's requirements."""
    row = db.execute(
        select(Scheme, SchemeVersion)
        .join(SchemeVersion, SchemeVersion.scheme_id == Scheme.id)
        .where(Scheme.slug == slug, SchemeVersion.is_current.is_(True))
        .options(
            selectinload(SchemeVersion.document_requirements).selectinload(
                DocumentRequirement.issuing_authority
            )
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No scheme found for slug {slug!r}"
        )
    scheme, version = row

    vault = list(db.scalars(select(UserDocument).where(UserDocument.user_id == user.id)).all())
    profile = to_domain_profile(user.profile)

    gaps = match_documents(
        version.document_requirements,
        vault,
        profile_resolve=profile,
    )
    unused = unrecognised_vault_documents(version.document_requirements, vault)

    return DocumentChecklistOut(
        slug=scheme.slug,
        documents=[
            DocumentGapOut(
                requirement_id=g.requirement_id,
                document_name=g.document_name,
                document_type=g.document_type,
                mandatory=g.mandatory,
                status=g.status,
                issuing_authority=g.issuing_authority,
                typical_processing_days=g.typical_processing_days,
                how_to_obtain=g.how_to_obtain,
                expired_on=g.expired_on,
            )
            for g in gaps
        ],
        have_count=sum(1 for g in gaps if g.status is DocumentStatus.HAVE),
        need_count=sum(1 for g in gaps if g.status is DocumentStatus.NEED),
        optional_missing_count=sum(1 for g in gaps if g.status is DocumentStatus.OPTIONAL_MISSING),
        expired_count=sum(1 for g in gaps if g.status is DocumentStatus.EXPIRED),
        unused_vault_documents=[UserDocumentOut.model_validate(d) for d in unused],
    )
