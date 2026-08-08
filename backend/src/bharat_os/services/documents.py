"""Matching a user's document vault against a scheme's requirements.

Pure with respect to its inputs — no network, no LLM. The one thing it refuses to
do is guess: a vault document whose type does not match any requirement is left
alone rather than fuzzily matched to the nearest requirement, because a wrong
match here would tell someone they are ready to apply when a document is actually
missing or wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from bharat_os.models.document import UserDocument
from bharat_os.models.scheme import DocumentRequirement


class DocumentStatus(StrEnum):
    HAVE = "have"
    NEED = "need"
    EXPIRED = "expired"
    #: A conditional requirement whose condition does not apply to this profile.
    NOT_APPLICABLE = "not_applicable"
    OPTIONAL_MISSING = "optional_missing"


@dataclass(frozen=True)
class DocumentGap:
    """One required document, matched against the vault (or not)."""

    requirement_id: str
    document_name: str
    document_type: str
    mandatory: bool
    status: DocumentStatus
    issuing_authority: str | None
    typical_processing_days: int | None
    how_to_obtain: str | None
    #: Set only when status is EXPIRED.
    expired_on: date | None = None


def match_documents(
    requirements: list[DocumentRequirement],
    vault: list[UserDocument],
    *,
    profile_known_fields: frozenset[str] | None = None,
    profile_resolve=None,
) -> list[DocumentGap]:
    """Compute have/need/expired/not-applicable for every requirement.

    ``profile_resolve``, when given, is used to evaluate conditional requirements
    with the engine's own rule evaluator, so "only required if turnover exceeds
    X" is decided by the same logic an eligibility criterion would use.
    """
    from bharat_os.engine.evaluator import evaluate_rule
    from bharat_os.models.enums import EvaluationState

    by_type: dict[str, list[UserDocument]] = {}
    for document in vault:
        by_type.setdefault(document.document_type.value, []).append(document)

    gaps: list[DocumentGap] = []
    for requirement in sorted(requirements, key=lambda r: r.display_order):
        applicable = True
        if requirement.conditional_logic is not None and profile_resolve is not None:
            result = evaluate_rule(requirement.conditional_logic, profile_resolve)
            if result.state is EvaluationState.UNMET:
                applicable = False
            # CANNOT_VERIFY is treated as applicable: better to ask for a document
            # that turns out unnecessary than to hide one that is required.

        held = by_type.get(requirement.document_type, [])
        current = [d for d in held if not d.is_expired]
        expired = [d for d in held if d.is_expired]

        if not applicable:
            status = DocumentStatus.NOT_APPLICABLE
            expired_on = None
        elif current:
            status = DocumentStatus.HAVE
            expired_on = None
        elif expired:
            status = DocumentStatus.EXPIRED
            expired_on = max(d.expiry_date for d in expired if d.expiry_date)
        elif requirement.mandatory:
            status = DocumentStatus.NEED
            expired_on = None
        else:
            status = DocumentStatus.OPTIONAL_MISSING
            expired_on = None

        gaps.append(
            DocumentGap(
                requirement_id=str(requirement.id),
                document_name=requirement.document_name,
                document_type=requirement.document_type,
                mandatory=requirement.mandatory,
                status=status,
                issuing_authority=(
                    requirement.issuing_authority.name
                    if requirement.issuing_authority
                    else requirement.issuing_authority_name
                ),
                typical_processing_days=requirement.typical_processing_days,
                how_to_obtain=requirement.how_to_obtain,
                expired_on=expired_on,
            )
        )

    return gaps


def unrecognised_vault_documents(
    requirements: list[DocumentRequirement],
    vault: list[UserDocument],
) -> list[UserDocument]:
    """Vault documents that match no requirement on this scheme.

    Not an error — a document can legitimately be irrelevant to one scheme and
    required by another. Surfaced so the vault view can show "not needed here"
    rather than silently ignoring it.
    """
    required_types = {r.document_type for r in requirements}
    return [d for d in vault if d.document_type.value not in required_types]
