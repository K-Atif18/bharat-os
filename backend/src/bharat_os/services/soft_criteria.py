"""Judging criteria that require interpretation.

Some eligibility conditions cannot be decided in code. "Innovative
technology-based startup", "commercially viable product", "social impact focus" —
these are judgements, and pretending otherwise by encoding a keyword match would
be worse than admitting it.

So a language model is asked. Four constraints govern how:

1. **The verdict vocabulary is hedged.** ``likely_met``, not ``met``. The model is
   forming an opinion from a short profile, and the wording must not let that be
   mistaken for a finding.
2. **Low confidence degrades to human review**, rather than being reported as an
   answer with a small number attached.
3. **Every judgement is recorded** with its prompt, model and reasoning.
4. **Every judgement names what would settle it.** "We are 62% confident" is not
   actionable; "send us your product description and this becomes decidable" is.

The prompt is versioned so that a change in wording can be told apart from a
change in model behaviour when calibration shifts.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bharat_os.engine.profile import ApplicantProfile
from bharat_os.llm import LLMError, LLMRequest, LLMResponseError, get_provider
from bharat_os.llm.base import LLMProvider
from bharat_os.models.audit import AIJudgement
from bharat_os.models.enums import SoftVerdict
from bharat_os.models.scheme import EligibilityCriterion, SchemeVersion

logger = logging.getLogger(__name__)

#: Bump when the prompt wording changes, so old judgements remain attributable to
#: the prompt that produced them.
PROMPT_VERSION = "v1"

#: Below this, a judgement is reported as needing human review instead of being
#: presented as an answer. Chosen high deliberately: the cost of a confident wrong
#: answer here is a user wasting weeks on an application they cannot win.
HUMAN_REVIEW_THRESHOLD = 0.6

REQUIRED_KEYS = ("verdict", "confidence", "reasoning", "evidence_that_would_strengthen")

SYSTEM_PROMPT = """\
You assess whether an Indian business appears to satisfy a government scheme's \
eligibility criterion that cannot be decided mechanically.

Your judgement will be shown to the applicant as an opinion, not a determination. \
Act accordingly:

- Judge only from the profile given. Do not assume facts that are not stated.
- If the profile lacks what you would need, say so and return "uncertain". An \
honest "uncertain" is far more useful than a confident guess.
- Confidence is your probability that a scheme officer reviewing this application \
would consider the criterion satisfied. Reserve values above 0.8 for cases where \
the profile makes it plain.
- Never invent details about the business.

Reply with a single JSON object and nothing else:

{
  "verdict": "likely_met" | "likely_unmet" | "uncertain",
  "confidence": <number between 0 and 1>,
  "reasoning": "<two or three sentences, addressed to the applicant>",
  "evidence_that_would_strengthen": ["<specific document or fact>", ...]
}

"evidence_that_would_strengthen" must list concrete things the applicant could \
provide. Never leave it empty; if the criterion looks clearly satisfied, name what \
would put it beyond doubt for a reviewer.\
"""


@dataclass(frozen=True)
class SoftJudgement:
    """A model's opinion on one criterion, with everything needed to weigh it."""

    criterion_id: str
    description: str
    verdict: SoftVerdict
    confidence: float
    reasoning: str
    evidence_that_would_strengthen: tuple[str, ...]
    requires_human_review: bool
    provider: str
    model: str
    prompt_version: str
    cached: bool = False

    @property
    def is_positive(self) -> bool:
        """Whether this leans towards the criterion being satisfied.

        Only counts when confidence clears the review threshold: a ``likely_met``
        at 0.4 is not support for anything.
        """
        return self.verdict is SoftVerdict.LIKELY_MET and not self.requires_human_review


def profile_summary(profile: ApplicantProfile) -> str:
    """Render the profile for the prompt.

    Only fields the applicant supplied are included. Emitting "turnover: unknown"
    invites the model to speculate about the gap; omitting the line entirely leaves
    nothing to speculate from.
    """
    lines: list[str] = []
    if profile.state:
        lines.append(f"- State: {profile.state}")
    if profile.district:
        lines.append(f"- District: {profile.district}")
    if profile.sector:
        lines.append(f"- Sector: {profile.sector}")
    if profile.stage:
        lines.append(f"- Stage: {profile.stage}")
    if profile.employee_count is not None:
        lines.append(f"- Employees: {profile.employee_count}")
    if profile.annual_turnover_inr is not None:
        lines.append(f"- Annual turnover: Rs {profile.annual_turnover_inr:,}")
    if profile.incorporation_date:
        age = profile.entity_age_years
        lines.append(
            f"- Incorporated: {profile.incorporation_date.isoformat()}"
            + (f" (about {age:.1f} years ago)" if age is not None else "")
        )
    if profile.registrations:
        lines.append(f"- Registrations held: {', '.join(sorted(profile.registrations))}")
    else:
        lines.append("- Registrations held: none")
    if profile.is_woman_led is not None:
        lines.append(f"- Woman-led: {'yes' if profile.is_woman_led else 'no'}")
    if profile.social_category:
        lines.append(f"- Social category: {profile.social_category}")

    return "\n".join(lines) if lines else "- No details provided"


def build_prompt(
    criterion: EligibilityCriterion,
    version: SchemeVersion,
    profile: ApplicantProfile,
) -> str:
    return f"""\
Scheme: {version.name}
Administered by: {version.administering_ministry}

Criterion to assess:
"{criterion.description}"

{f'Wording from the official source: "{criterion.source_quote}"' if criterion.source_quote else ""}

Applicant profile:
{profile_summary(profile)}

Assess whether this applicant appears to satisfy the criterion."""


def cache_key(
    criterion: EligibilityCriterion,
    profile: ApplicantProfile,
    provider: LLMProvider,
    *,
    user_id: object | None = None,
) -> str:
    """Identity of a user's question, used to avoid asking it twice.

    Includes the user, model and prompt version. User scoping prevents one
    account from receiving an audit result that was created for another account
    with coincidentally identical profile facts. Service-level calls without an
    account retain a stable anonymous scope for deterministic tests and tooling.
    """
    material = "|".join(
        [
            str(user_id) if user_id is not None else "anonymous",
            str(criterion.id),
            PROMPT_VERSION,
            provider.name,
            provider.model,
            profile_summary(profile),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _coerce_confidence(raw: object) -> float:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise LLMResponseError(f"confidence was not a number: {raw!r}") from exc
    if not 0.0 <= value <= 1.0:
        raise LLMResponseError(f"confidence {value} is outside [0, 1]")
    return value


def _coerce_verdict(raw: object) -> SoftVerdict:
    try:
        return SoftVerdict(str(raw))
    except ValueError as exc:
        raise LLMResponseError(
            f"verdict {raw!r} is not one of {[v.value for v in SoftVerdict]}"
        ) from exc


def judge_criterion(
    db: Session,
    criterion: EligibilityCriterion,
    version: SchemeVersion,
    profile: ApplicantProfile,
    *,
    user_id: object | None = None,
    provider: LLMProvider | None = None,
) -> SoftJudgement:
    """Judge one soft criterion, using the cache and recording an audit row.

    A provider failure is not allowed to break the assessment. The deterministic
    part of the report is still valid and useful, so the soft criterion degrades to
    "needs human review" instead of taking the whole page down.
    """
    active = provider or get_provider()
    key = cache_key(criterion, profile, active, user_id=user_id)

    existing = db.scalar(select(AIJudgement).where(AIJudgement.cache_key == key))
    if existing is not None:
        return _to_judgement(existing, criterion, cached=True)

    request = LLMRequest(
        system=SYSTEM_PROMPT,
        prompt=build_prompt(criterion, version, profile),
        required_keys=REQUIRED_KEYS,
    )

    try:
        response = active.complete(request)
        verdict = _coerce_verdict(response.data["verdict"])
        confidence = _coerce_confidence(response.data["confidence"])
        reasoning = str(response.data["reasoning"]).strip()
        evidence = response.data["evidence_that_would_strengthen"]
        if not isinstance(evidence, list):
            evidence = [str(evidence)]
        evidence = [str(item) for item in evidence if str(item).strip()]
    except (LLMError, KeyError) as exc:
        # Log the failure, not the profile: the prompt contains personal data.
        logger.warning(
            "Soft criterion %s could not be judged (%s): %s",
            criterion.id,
            type(exc).__name__,
            exc,
        )
        return SoftJudgement(
            criterion_id=str(criterion.id),
            description=criterion.description,
            verdict=SoftVerdict.UNCERTAIN,
            confidence=0.0,
            reasoning=(
                "This criterion needs a human to assess. Our automated assessment "
                "was unavailable, so rather than guess we are flagging it for review."
            ),
            evidence_that_would_strengthen=(),
            requires_human_review=True,
            provider=active.name,
            model=active.model,
            prompt_version=PROMPT_VERSION,
        )

    requires_review = confidence < HUMAN_REVIEW_THRESHOLD

    record = AIJudgement(
        cache_key=key,
        criterion_id=criterion.id,
        user_id=user_id,
        verdict=verdict,
        confidence=confidence,
        reasoning=reasoning,
        evidence_that_would_strengthen=evidence,
        requires_human_review=requires_review,
        provider=response.provider,
        model=response.model,
        prompt_version=PROMPT_VERSION,
        prompt=response.prompt,
        raw_response=response.raw_text,
        prompt_tokens=response.usage.get("prompt_tokens"),
        completion_tokens=response.usage.get("completion_tokens"),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        # React Strict Mode, retries, or two workers can ask the same question
        # concurrently. The globally unique cache key makes one insert win; the
        # loser should reuse that committed answer rather than fail the request.
        db.rollback()
        winner = db.scalar(select(AIJudgement).where(AIJudgement.cache_key == key))
        if winner is None:
            raise
        return _to_judgement(winner, criterion, cached=True)

    return _to_judgement(record, criterion, cached=False)


def _to_judgement(
    record: AIJudgement, criterion: EligibilityCriterion, *, cached: bool
) -> SoftJudgement:
    return SoftJudgement(
        criterion_id=str(criterion.id),
        description=criterion.description,
        verdict=record.verdict,
        confidence=record.confidence,
        reasoning=record.reasoning,
        evidence_that_would_strengthen=tuple(record.evidence_that_would_strengthen or ()),
        requires_human_review=record.requires_human_review,
        provider=record.provider,
        model=record.model,
        prompt_version=record.prompt_version,
        cached=cached,
    )


def judge_all(
    db: Session,
    version: SchemeVersion,
    profile: ApplicantProfile,
    *,
    user_id: object | None = None,
    provider: LLMProvider | None = None,
) -> list[SoftJudgement]:
    """Judge every soft criterion on a scheme version."""
    from bharat_os.services.eligibility import soft_criteria

    return [
        judge_criterion(db, criterion, version, profile, user_id=user_id, provider=provider)
        for criterion in soft_criteria(version)
    ]
