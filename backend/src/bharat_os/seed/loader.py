"""Load the curated scheme corpus into the database.

Two properties matter more than speed here.

**Idempotent.** Running the loader twice must not create a second identical
version. Curation is an ongoing activity and the loader will be run repeatedly,
often against a database that already holds most of the corpus.

**Versioning-aware.** When a scheme's content *has* changed, the loader supersedes
the current version and creates a new one rather than mutating in place. Nothing
is ever overwritten, so an assessment made against version 1 remains explicable
after version 2 lands.

Change is detected by hashing the canonical payload. A reformatted comment
produces the same hash and is correctly treated as no change; an amended turnover
threshold produces a different hash and correctly creates a new version.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.models.scheme import (
    ApplicationWindow,
    Authority,
    Benefit,
    DocumentRequirement,
    EligibilityCriterion,
    Scheme,
    SchemeVersion,
)
from bharat_os.schemas.scheme import AuthorityIn, SchemeVersionIn

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
SCHEME_DIR = DATA_DIR / "schemes"
AUTHORITIES_FILE = DATA_DIR / "authorities.json"


class SeedDataError(RuntimeError):
    """Raised when curated data on disk is invalid."""


@dataclass
class LoadReport:
    """What a load run actually did, so runs are auditable rather than silent."""

    authorities_created: int = 0
    authorities_updated: int = 0
    schemes_created: int = 0
    versions_created: int = 0
    unchanged: int = 0
    slugs_created: list[str] = field(default_factory=list)
    slugs_versioned: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"authorities: {self.authorities_created} created, "
            f"{self.authorities_updated} updated; "
            f"schemes: {self.schemes_created} new, "
            f"{self.versions_created} new versions, "
            f"{self.unchanged} unchanged"
        )


def content_hash(payload: SchemeVersionIn) -> str:
    """Stable hash of a scheme's substantive content.

    Excludes provenance bookkeeping: re-verifying an unchanged criterion updates
    ``last_verified_at`` but must not manufacture a new scheme version, or the
    history would fill with revisions that changed nothing.
    """
    data = payload.model_dump(mode="json", exclude={"effective_from"})

    def strip_bookkeeping(node: object) -> object:
        if isinstance(node, dict):
            return {
                key: strip_bookkeeping(value)
                for key, value in node.items()
                if key not in {"last_verified_at", "verified_by_human"}
            }
        if isinstance(node, list):
            return [strip_bookkeeping(item) for item in node]
        return node

    canonical = json.dumps(strip_bookkeeping(data), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_authorities(path: Path = AUTHORITIES_FILE) -> list[AuthorityIn]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedDataError(f"{path.name}: invalid JSON — {exc}") from exc
    try:
        return [AuthorityIn.model_validate(item) for item in raw]
    except ValidationError as exc:
        raise SeedDataError(f"{path.name}: {exc}") from exc


def read_schemes(directory: Path = SCHEME_DIR) -> list[SchemeVersionIn]:
    """Read and validate every curated scheme file.

    Validation failures name the offending file, because "field required" with no
    filename is useless when the corpus has dozens of entries.
    """
    if not directory.exists():
        return []

    schemes: list[SchemeVersionIn] = []
    for path in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SeedDataError(f"{path.name}: invalid JSON — {exc}") from exc
        try:
            schemes.append(SchemeVersionIn.model_validate(raw))
        except ValidationError as exc:
            raise SeedDataError(f"{path.name}: {exc}") from exc

    slugs = [scheme.slug for scheme in schemes]
    duplicates = {slug for slug in slugs if slugs.count(slug) > 1}
    if duplicates:
        raise SeedDataError(f"duplicate scheme slugs across files: {sorted(duplicates)}")

    return schemes


def _upsert_authorities(session: Session, authorities: list[AuthorityIn]) -> LoadReport:
    report = LoadReport()
    for payload in authorities:
        existing = session.scalar(select(Authority).where(Authority.slug == payload.slug))
        if existing is None:
            session.add(
                Authority(
                    slug=payload.slug,
                    name=payload.name,
                    authority_type=payload.authority_type,
                    portal_url=str(payload.portal_url) if payload.portal_url else None,
                    contact=payload.contact,
                    document_acceptance_method=payload.document_acceptance_method,
                )
            )
            report.authorities_created += 1
            continue

        # Authorities are reference data, not versioned: correcting a ministry's
        # name is a fix, not a new fact about the world.
        changed = False
        for attribute, value in (
            ("name", payload.name),
            ("authority_type", payload.authority_type),
            ("portal_url", str(payload.portal_url) if payload.portal_url else None),
            ("contact", payload.contact),
            ("document_acceptance_method", payload.document_acceptance_method),
        ):
            if getattr(existing, attribute) != value:
                setattr(existing, attribute, value)
                changed = True
        if changed:
            report.authorities_updated += 1

    session.flush()
    return report


def _authority_ids(session: Session) -> dict[str, object]:
    return {a.slug: a.id for a in session.scalars(select(Authority)).all()}


def _build_version(
    payload: SchemeVersionIn,
    *,
    scheme: Scheme,
    version_number: int,
    authority_ids: dict[str, object],
) -> SchemeVersion:
    if payload.authority_slug and payload.authority_slug not in authority_ids:
        raise SeedDataError(
            f"{payload.slug}: unknown authority_slug {payload.authority_slug!r}; "
            "add it to authorities.json"
        )

    return SchemeVersion(
        scheme=scheme,
        version=version_number,
        is_current=True,
        name=payload.name,
        summary=payload.summary,
        scheme_type=payload.scheme_type,
        status=payload.status,
        administering_ministry=payload.administering_ministry,
        implementing_agency=payload.implementing_agency,
        authority_id=authority_ids.get(payload.authority_slug) if payload.authority_slug else None,
        target_segments=list(payload.target_segments),
        sectors=list(payload.sectors),
        states=list(payload.states),
        benefit_value_min=payload.benefit_value_min,
        benefit_value_max=payload.benefit_value_max,
        benefit_description=payload.benefit_description,
        application_url=str(payload.application_url) if payload.application_url else None,
        offline_process=payload.offline_process,
        application_difficulty=payload.application_difficulty,
        estimated_effort_hours=payload.estimated_effort_hours,
        drafting_lead_days=payload.drafting_lead_days,
        content_hash=content_hash(payload),
        effective_from=payload.effective_from,
        criteria=[
            EligibilityCriterion(
                criterion_type=criterion.criterion_type,
                description=criterion.description,
                machine_readable_rule=criterion.machine_readable_rule,
                display_order=criterion.display_order,
                source_url=str(criterion.source_url),
                source_quote=criterion.source_quote,
                last_verified_at=criterion.last_verified_at,
                verified_by_human=criterion.verified_by_human,
            )
            for criterion in payload.criteria
        ],
        document_requirements=[
            DocumentRequirement(
                document_name=document.document_name,
                document_type=document.document_type,
                issuing_authority_id=(
                    authority_ids.get(document.issuing_authority_slug)
                    if document.issuing_authority_slug
                    else None
                ),
                issuing_authority_name=document.issuing_authority_name,
                typical_processing_days=document.typical_processing_days,
                how_to_obtain=document.how_to_obtain,
                mandatory=document.mandatory,
                conditional_logic=document.conditional_logic,
                display_order=document.display_order,
                source_url=str(document.source_url),
                source_quote=document.source_quote,
                last_verified_at=document.last_verified_at,
                verified_by_human=document.verified_by_human,
            )
            for document in payload.document_requirements
        ],
        windows=[
            ApplicationWindow(
                open_date=window.open_date,
                close_date=window.close_date,
                recurrence=window.recurrence,
                notification_source=window.notification_source,
                notes=window.notes,
                source_url=str(window.source_url),
                source_quote=window.source_quote,
                last_verified_at=window.last_verified_at,
                verified_by_human=window.verified_by_human,
            )
            for window in payload.windows
        ],
        benefits=[
            Benefit(
                benefit_type=benefit.benefit_type,
                description=benefit.description,
                quantum_min=benefit.quantum_min,
                quantum_max=benefit.quantum_max,
                conditions_for_disbursement=benefit.conditions_for_disbursement,
                source_url=str(benefit.source_url),
                source_quote=benefit.source_quote,
                last_verified_at=benefit.last_verified_at,
                verified_by_human=benefit.verified_by_human,
            )
            for benefit in payload.benefits
        ],
    )


def load_schemes(
    session: Session,
    schemes: list[SchemeVersionIn],
    authorities: list[AuthorityIn],
) -> LoadReport:
    """Load or update the corpus, returning what changed."""
    report = _upsert_authorities(session, authorities)
    authority_ids = _authority_ids(session)

    for payload in schemes:
        incoming_hash = content_hash(payload)
        scheme = session.scalar(select(Scheme).where(Scheme.slug == payload.slug))

        if scheme is None:
            scheme = Scheme(slug=payload.slug)
            session.add(scheme)
            session.add(
                _build_version(
                    payload, scheme=scheme, version_number=1, authority_ids=authority_ids
                )
            )
            report.schemes_created += 1
            report.slugs_created.append(payload.slug)
            continue

        current = session.scalar(
            select(SchemeVersion)
            .where(SchemeVersion.scheme_id == scheme.id)
            .where(SchemeVersion.is_current.is_(True))
        )

        if current is not None and current.content_hash == incoming_hash:
            # Content is unchanged. Refresh provenance so the corpus reflects
            # that a human looked at it again today, but do not fabricate a
            # revision that changed nothing.
            _refresh_provenance(current, payload)
            report.unchanged += 1
            continue

        highest = session.scalar(
            select(SchemeVersion.version)
            .where(SchemeVersion.scheme_id == scheme.id)
            .order_by(SchemeVersion.version.desc())
            .limit(1)
        )
        if current is not None:
            current.is_current = False
            current.superseded_at = datetime.now(UTC)

        session.add(
            _build_version(
                payload,
                scheme=scheme,
                version_number=(highest or 0) + 1,
                authority_ids=authority_ids,
            )
        )
        report.versions_created += 1
        report.slugs_versioned.append(payload.slug)

    session.commit()
    return report


def _refresh_provenance(version: SchemeVersion, payload: SchemeVersionIn) -> None:
    """Update verification dates on an unchanged version.

    Matching is positional, which is safe precisely because the content hash
    already proved the criteria are identical.
    """
    for existing, incoming in zip(
        sorted(version.criteria, key=lambda c: c.display_order),
        sorted(payload.criteria, key=lambda c: c.display_order),
        strict=False,
    ):
        existing.last_verified_at = incoming.last_verified_at
        existing.verified_by_human = incoming.verified_by_human


def load_from_disk(session: Session) -> LoadReport:
    """Read the corpus from disk and load it."""
    return load_schemes(session, read_schemes(), read_authorities())
