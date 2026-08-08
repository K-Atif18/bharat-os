"""Combining deterministic checks and language-model judgements into one report.

A pure module. Aggregation is where this system is most tempted to lie, so the
rules are written down explicitly rather than emerging from whatever the arithmetic
happens to do.

Rule 1 — **a failed hard requirement is not a low score.** It is a separate
outcome, and no aggregate is produced. Averaging "you definitely do not meet the
turnover ceiling" with four soft positives to reach 71% would be actively
misleading.

Rule 2 — **hard and soft evidence are not interchangeable.** A confirmed hard
criterion is a fact. A soft judgement at 0.7 is an opinion. They are combined with
soft contributions weighted by both their confidence and a discount factor, so ten
hedged opinions cannot outweigh a handful of established facts.

Rule 3 — **unverifiable is not zero.** An unverifiable criterion lowers the
aggregate because less has been established, but it is reported separately with the
fields that would resolve it, so the user sees a task rather than a penalty.

Rule 4 — **anything needing human review is surfaced at the top level.** A report
containing a flagged judgement is itself flagged; the caveat cannot be lost by a
caller that only reads the number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from bharat_os.engine.results import HardRuleAssessment
from bharat_os.models.enums import SoftVerdict
from bharat_os.services.soft_criteria import SoftJudgement

#: How much a maximally confident soft judgement counts relative to a confirmed
#: hard criterion. Opinions are worth less than facts, and the number says by how
#: much rather than leaving it implicit.
SOFT_EVIDENCE_WEIGHT = 0.7

#: Aggregate confidence at or above which a report is described as strong. Not a
#: promise of approval, and the wording in the interface never implies one.
STRONG_MATCH_THRESHOLD = 0.75


class ReportOutcome(StrEnum):
    """The headline conclusion of an assessment."""

    #: A hard requirement is definitively unmet.
    RULED_OUT = "ruled_out"
    #: Everything checkable is satisfied and no judgement is outstanding.
    STRONG = "strong"
    #: Worth pursuing, with caveats.
    PROMISING = "promising"
    #: Too little established to say much.
    INSUFFICIENT_DATA = "insufficient_data"
    #: A judgement needs a human before this can be relied on.
    NEEDS_HUMAN_REVIEW = "needs_human_review"


@dataclass(frozen=True)
class EligibilityReport:
    """The full assessment of one scheme for one applicant."""

    outcome: ReportOutcome
    #: Proportion of the total evidence that has been established, in ``[0, 1]``.
    #: ``None`` when the applicant is ruled out, because no aggregate is honest
    #: in that case.
    confidence: float | None

    hard: HardRuleAssessment
    soft: tuple[SoftJudgement, ...] = ()

    #: Criteria a human should look at before the applicant relies on this.
    flagged_for_review: tuple[str, ...] = ()
    #: Profile fields that would resolve unverifiable criteria.
    missing_fields: tuple[str, ...] = ()
    #: Concrete evidence that would firm up the soft judgements.
    evidence_requested: tuple[str, ...] = field(default_factory=tuple)
    #: Why the applicant is ruled out, when they are.
    disqualifying_reasons: tuple[str, ...] = ()

    @property
    def requires_human_review(self) -> bool:
        return bool(self.flagged_for_review)

    @property
    def is_actionable(self) -> bool:
        """Whether it is reasonable to suggest the applicant pursue this."""
        return self.outcome is not ReportOutcome.RULED_OUT


def aggregate(
    hard: HardRuleAssessment,
    soft: list[SoftJudgement],
) -> EligibilityReport:
    """Produce a single report from deterministic and judgement-based results."""
    if hard.has_disqualifier:
        return EligibilityReport(
            outcome=ReportOutcome.RULED_OUT,
            # No aggregate. A number here would invite the reader to weigh it
            # against the disqualification, which is not a trade-off that exists.
            confidence=None,
            hard=hard,
            soft=tuple(soft),
            disqualifying_reasons=tuple(hard.results[key].reason for key in hard.unmet),
            missing_fields=hard.all_missing_fields,
        )

    # Established evidence over total possible evidence.
    hard_achieved = float(len(hard.met))
    hard_possible = float(hard.total)

    soft_achieved = 0.0
    soft_possible = 0.0
    for judgement in soft:
        soft_possible += SOFT_EVIDENCE_WEIGHT
        if judgement.verdict is SoftVerdict.LIKELY_MET and not judgement.requires_human_review:
            soft_achieved += SOFT_EVIDENCE_WEIGHT * judgement.confidence

    total_possible = hard_possible + soft_possible
    confidence = (hard_achieved + soft_achieved) / total_possible if total_possible else 0.0

    flagged = tuple(j.description for j in soft if j.requires_human_review)
    evidence = tuple(dict.fromkeys(item for j in soft for item in j.evidence_that_would_strengthen))

    if flagged:
        outcome = ReportOutcome.NEEDS_HUMAN_REVIEW
    elif total_possible == 0 or (hard.unverifiable and confidence < 0.5):
        # Either nothing was checkable at all, or too little was established for a
        # conclusion to be worth stating.
        outcome = ReportOutcome.INSUFFICIENT_DATA
    elif confidence >= STRONG_MATCH_THRESHOLD and not hard.unverifiable:
        outcome = ReportOutcome.STRONG
    else:
        outcome = ReportOutcome.PROMISING

    return EligibilityReport(
        outcome=outcome,
        confidence=confidence,
        hard=hard,
        soft=tuple(soft),
        flagged_for_review=flagged,
        missing_fields=hard.all_missing_fields,
        evidence_requested=evidence,
    )
