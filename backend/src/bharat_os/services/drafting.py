"""Generating an application draft.

Three kinds of field, always:

* **Profile fields** are copied verbatim. No model call, no room for drift.
* **Narrative fields** are written by the language model from the profile and an
  explicit instruction, and always carry the instruction alongside the text so
  the applicant can see what was asked, not just what was answered.
* **Human-required fields** are never populated. They carry a plain-language
  reason so the applicant understands why, rather than seeing a blank they
  might assume is a bug.

The one invariant that must never break, anywhere this module is touched: this
code produces a draft, and a draft is not a submission. There is no function
here, and there must never be one, that files anything with a government portal.
Every draft ends with at least one field the applicant must act on themselves —
enforced by :func:`generate_draft` refusing to skip the human-required fields a
scheme's field map defines.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from bharat_os.engine.profile import ApplicantProfile
from bharat_os.llm import LLMError, LLMRequest, get_provider
from bharat_os.llm.base import LLMProvider
from bharat_os.models.enums import DraftFieldSource
from bharat_os.models.scheme import SchemeVersion
from bharat_os.services.field_maps import FIELD_MAPS, DraftField

SYSTEM_PROMPT = """\
You write narrative sections of Indian government scheme applications from a \
business profile.

Rules:
- Use only facts present in the profile. Never invent turnover figures, \
customer names, product details or achievements the profile does not state.
- Where the profile does not contain enough to be specific, write in general \
but honest terms rather than fabricating specifics.
- Write for a scheme reviewer: plain, factual, no marketing language.
- Stay within the requested word limit.

Reply with a single JSON object: {"text": "<the narrative>"}\
"""


@dataclass(frozen=True)
class DraftFieldResult:
    key: str
    label: str
    source: DraftFieldSource
    value: str | None
    #: Present for narrative fields: what was asked, so it is auditable.
    instruction: str | None = None
    #: Present for human-required fields: why nothing was filled in.
    reason: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source.value
        return d


class NoFieldMapError(LookupError):
    """Raised when drafting is requested for a scheme with no field map.

    Deliberately loud. A silent empty draft would look like a bug rather than a
    scheme that is simply not yet supported for drafting.
    """


def _profile_value(
    profile: ApplicantProfile, entity_name: str | None, field_name: str
) -> str | None:
    # entity_name is deliberately not a field on ApplicantProfile: it is identity
    # data, not an eligibility fact, and the engine's profile is scoped to what
    # eligibility rules reason about. Drafting needs it too, so it is threaded
    # through separately rather than widening the engine's domain object.
    if field_name == "entity_name":
        return entity_name

    value = profile.resolve(field_name)
    from bharat_os.engine.profile import MISSING

    if value is MISSING:
        return None
    if isinstance(value, frozenset | set):
        return ", ".join(sorted(value)) if value else "none"
    return str(value)


def _generate_narrative(
    provider: LLMProvider,
    field: DraftField,
    version: SchemeVersion,
    profile: ApplicantProfile,
) -> str | None:
    from bharat_os.services.soft_criteria import profile_summary

    prompt = (
        f"Scheme: {version.name}\n"
        f"Field to write: {field.label}\n"
        f"Instruction: {field.narrative_instruction}\n"
        f"{f'Word limit: {field.max_words}' if field.max_words else ''}\n\n"
        f"Applicant profile:\n{profile_summary(profile)}"
    )
    request = LLMRequest(system=SYSTEM_PROMPT, prompt=prompt, required_keys=("text",))
    try:
        response = provider.complete(request)
        return str(response.data["text"]).strip()
    except (LLMError, KeyError):
        return None


def generate_draft(
    session_unused: Session | None,
    version: SchemeVersion,
    profile: ApplicantProfile,
    *,
    scheme_slug: str,
    entity_name: str | None = None,
    provider: LLMProvider | None = None,
) -> list[DraftFieldResult]:
    """Generate every field of a draft for one scheme.

    ``session_unused`` is accepted for a consistent call signature with the rest
    of the services layer; drafting itself needs no database access beyond what
    the caller already has loaded onto ``version``.

    ``entity_name`` is passed separately from ``profile`` because it is identity
    data, not an eligibility fact — the engine's :class:`ApplicantProfile` is
    deliberately scoped to fields eligibility rules reason about.
    """
    field_map = FIELD_MAPS.get(scheme_slug)
    if field_map is None:
        raise NoFieldMapError(
            f"No draft field map for {scheme_slug!r}. Drafting is currently supported "
            f"for: {sorted(FIELD_MAPS)}."
        )

    active_provider = provider or get_provider()
    results: list[DraftFieldResult] = []

    for field in field_map:
        if field.source is DraftFieldSource.PROFILE:
            value = (
                _profile_value(profile, entity_name, field.profile_field)
                if field.profile_field
                else None
            )
            results.append(DraftFieldResult(field.key, field.label, field.source, value))

        elif field.source is DraftFieldSource.GENERATED_NARRATIVE:
            text = _generate_narrative(active_provider, field, version, profile)
            results.append(
                DraftFieldResult(
                    field.key,
                    field.label,
                    field.source,
                    text,
                    instruction=field.narrative_instruction,
                )
            )

        else:  # HUMAN_REQUIRED
            results.append(
                DraftFieldResult(
                    field.key,
                    field.label,
                    field.source,
                    value=None,
                    reason=field.human_required_reason,
                )
            )

    # Enforced, not just conventional: a draft with zero human-required fields
    # would read as "ready to submit", which no field map in this system may say.
    if not any(r.source is DraftFieldSource.HUMAN_REQUIRED for r in results):
        raise AssertionError(
            f"Field map for {scheme_slug!r} defines no human-required field. "
            "Every draft must leave at least one field for the applicant to "
            "supply themselves — a fully auto-filled draft is not permitted."
        )

    return results


def supported_schemes() -> list[str]:
    """Schemes that currently have a draft field map."""
    return sorted(FIELD_MAPS)
