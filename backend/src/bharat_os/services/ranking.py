"""Ranking matched schemes.

A pure module: given already-computed assessments and scheme facts, it produces an
ordering. No database, no network, so the scoring can be reasoned about and tested
in isolation.

The score has three factors, following the design in the source analysis:
match confidence, benefit value, and the inverse of application difficulty.

Two decisions in here are worth stating plainly.

**Benefit is scaled logarithmically.** A ten crore credit guarantee is not five
hundred times more useful to an applicant than a twenty lakh grant, and linear
scaling would let one enormous scheme dominate every feed regardless of fit. Log
scaling keeps large benefits ahead of small ones without letting magnitude swamp
relevance.

**Definite disqualification is not a low score, it is a separate outcome.** A
scheme with an unmet hard requirement is not "a weak match" — the applicant cannot
have it. Those are partitioned out of the ranked feed rather than mixed in with a
small number attached, because a ranked list implies "try these" and it would be
dishonest to include something that cannot succeed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from bharat_os.engine.results import HardRuleAssessment
from bharat_os.models.enums import ApplicationDifficulty

#: How much each difficulty level discounts a scheme's score. A hard application
#: is still worth surfacing, just below an equally valuable easy one.
DIFFICULTY_WEIGHT: dict[ApplicationDifficulty, float] = {
    ApplicationDifficulty.LOW: 1.0,
    ApplicationDifficulty.MEDIUM: 0.7,
    ApplicationDifficulty.HIGH: 0.45,
}

#: Confidence assigned when a scheme has no machine-decidable criteria at all.
#: Neutral rather than optimistic: we genuinely do not know yet.
NO_HARD_CRITERIA_CONFIDENCE = 0.5

#: Reference point for log scaling, in rupees. Roughly the largest benefit in the
#: corpus, so the factor lands in a sensible range rather than being tuned to one
#: outlier scheme.
BENEFIT_REFERENCE_INR = 100_000_000


class MatchOutcome(StrEnum):
    """How a scheme relates to an applicant.

    Kept distinct from the score so the interface can say "you are ruled out
    because X" instead of showing a low percentage and leaving the user guessing.
    """

    #: Every hard criterion is met.
    ELIGIBLE = "eligible"
    #: Some criteria cannot be decided without more profile data.
    NEEDS_MORE_DATA = "needs_more_data"
    #: A hard requirement is definitively unmet.
    RULED_OUT = "ruled_out"
    #: The scheme has no machine-decidable criteria, so only judgement applies.
    JUDGEMENT_ONLY = "judgement_only"


@dataclass(frozen=True)
class RankingInput:
    """Everything the ranker needs about one scheme."""

    slug: str
    assessment: HardRuleAssessment
    difficulty: ApplicationDifficulty
    benefit_value_max: int | None
    #: Number of criteria requiring judgement, reported so the UI can be honest
    #: about how much of the assessment is not yet settled.
    soft_criteria_count: int = 0


@dataclass(frozen=True)
class RankedMatch:
    """A scored scheme, with the components that produced the score."""

    slug: str
    outcome: MatchOutcome
    #: Share of decidable hard criteria that are met, in ``[0, 1]``.
    confidence: float
    score: float
    confidence_factor: float
    benefit_factor: float
    difficulty_factor: float
    criteria_met: int
    criteria_unmet: int
    criteria_unverifiable: int
    soft_criteria_count: int
    missing_fields: tuple[str, ...]


def classify(assessment: HardRuleAssessment) -> MatchOutcome:
    if assessment.total == 0:
        return MatchOutcome.JUDGEMENT_ONLY
    if assessment.has_disqualifier:
        return MatchOutcome.RULED_OUT
    if assessment.unverifiable:
        return MatchOutcome.NEEDS_MORE_DATA
    return MatchOutcome.ELIGIBLE


def hard_rule_confidence(assessment: HardRuleAssessment) -> float:
    """Share of hard criteria confirmed met.

    Unverifiable criteria count against confidence without being treated as
    failures: the number honestly reflects how much has actually been established,
    and the accompanying ``missing_fields`` says how to raise it.
    """
    if assessment.total == 0:
        return NO_HARD_CRITERIA_CONFIDENCE
    return len(assessment.met) / assessment.total


def benefit_factor(benefit_value_max: int | None) -> float:
    """Log-scaled benefit magnitude in ``[0, 1]``.

    Schemes with no monetary value — registrations, certifications — get a modest
    non-zero factor rather than zero. DPIIT recognition pays nothing directly but
    unlocks much of the rest of the corpus, so ranking it last would be wrong.
    """
    if not benefit_value_max:
        return 0.25
    return min(1.0, math.log1p(benefit_value_max) / math.log1p(BENEFIT_REFERENCE_INR))


def difficulty_factor(difficulty: ApplicationDifficulty) -> float:
    return DIFFICULTY_WEIGHT[difficulty]


def score_one(item: RankingInput) -> RankedMatch:
    outcome = classify(item.assessment)
    confidence = hard_rule_confidence(item.assessment)
    benefit = benefit_factor(item.benefit_value_max)
    difficulty = difficulty_factor(item.difficulty)

    return RankedMatch(
        slug=item.slug,
        outcome=outcome,
        confidence=confidence,
        score=0.0 if outcome is MatchOutcome.RULED_OUT else confidence * benefit * difficulty,
        confidence_factor=confidence,
        benefit_factor=benefit,
        difficulty_factor=difficulty,
        criteria_met=len(item.assessment.met),
        criteria_unmet=len(item.assessment.unmet),
        criteria_unverifiable=len(item.assessment.unverifiable),
        soft_criteria_count=item.soft_criteria_count,
        missing_fields=item.assessment.all_missing_fields,
    )


def rank(items: list[RankingInput]) -> tuple[list[RankedMatch], list[RankedMatch]]:
    """Score and order schemes.

    Returns ``(matches, ruled_out)``. Ruled-out schemes are returned separately
    rather than appended, so a caller cannot accidentally present something the
    applicant cannot obtain as though it were a suggestion.

    Ties break on slug so the ordering is stable and the feed does not reshuffle
    between identical requests.
    """
    scored = [score_one(item) for item in items]
    matches = [m for m in scored if m.outcome is not MatchOutcome.RULED_OUT]
    ruled_out = [m for m in scored if m.outcome is MatchOutcome.RULED_OUT]

    matches.sort(key=lambda m: (-m.score, m.slug))
    ruled_out.sort(key=lambda m: m.slug)
    return matches, ruled_out
